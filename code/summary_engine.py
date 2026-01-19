import pandas as pd
import json
import os
import re
from dateutil import parser

# --- IMPORTS FROM NEW MODULES ---
from graph_generator import create_all_charts
from static_summary import write_executive_summary
from ai_summarizer import generate_summary

# ==========================================
# PART 1: SENTENCE CONSTRUCTION
# ==========================================

def fill_meaning_from_json(row, meaning_map):
    # Ensure ID is string to match the map keys
    template_id = str(row.get('Template ID', ''))
    params_json = row.get('Parameters')
    meaning_template = meaning_map.get(template_id)
    
    if not meaning_template: return "Error: Template ID not found"
    if pd.isna(params_json) or str(params_json).strip() == '{}': return meaning_template

    try:
        params_dict = json.loads(str(params_json))
        final_sentence = meaning_template
        for key, value in params_dict.items():
            placeholder = f"<{key}>"
            final_sentence = final_sentence.replace(placeholder, str(value))
        return final_sentence
    except:
        return meaning_template
    
def step_1_merge_sentences(input_file):
    print(f"[MERGE] Merging parameters in: {os.path.basename(input_file)}")
    try:
        df_logs = pd.read_excel(input_file, sheet_name="Log Analysis")
        df_templates = pd.read_excel(input_file, sheet_name="Template Summary")
    except Exception as e:
        raise ValueError(f"Error reading Excel file: {e}")
    
    df_logs['Template ID'] = df_logs['Template ID'].astype(str)
    df_templates['Template ID'] = df_templates['Template ID'].astype(str)
    meaning_map = dict(zip(df_templates['Template ID'], df_templates['Event Meaning']))
    
    df_logs['Meaning Log'] = df_logs.apply(lambda row: fill_meaning_from_json(row, meaning_map), axis=1)
    
    # Reorder Columns
    cols = list(df_logs.columns)
    if 'Raw Log' in cols and 'Meaning Log' in cols:
        cols.pop(cols.index('Meaning Log'))
        target_index = cols.index('Raw Log') + 1
        cols.insert(target_index, 'Meaning Log')
        df_logs = df_logs[cols]

    # Save
    base_dir = os.path.dirname(input_file)
    base_name = os.path.basename(input_file)
    stem, _ext = os.path.splitext(base_name)
    new_name = f"{stem}_merged.xlsx"
    output_path = os.path.join(base_dir, new_name)
    
    print(f"[MERGE] Saving to: {os.path.basename(output_path)}")
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        df_logs.to_excel(writer, sheet_name='Log Analysis', index=False)
        df_templates.to_excel(writer, sheet_name='Template Summary', index=False)
        
    return output_path

# ==========================================
# PART 2: SORTING
# ==========================================

def get_time_from_json(params_str):
    try:
        if pd.isna(params_str): return pd.NaT
        params = json.loads(str(params_str))
        time_str = params.get('TIMESTAMP')
        if not time_str: return pd.NaT
        return parser.parse(time_str)
    except:
        return pd.NaT

def step_2_sort_logs(input_file):
    print(f"[SORT] Sorting logs: {os.path.basename(input_file)}")
    try:
        df_logs = pd.read_excel(input_file, sheet_name="Log Analysis")
        df_templates = pd.read_excel(input_file, sheet_name="Template Summary")
    except Exception as e:
        raise ValueError(f"Error reading Excel file: {e}")

    if 'Parameters' in df_logs.columns:
        df_logs['Temp_Timestamp'] = df_logs['Parameters'].apply(get_time_from_json)
        if df_logs['Temp_Timestamp'].notna().sum() > 0:
            df_logs = df_logs.sort_values(by='Temp_Timestamp', ascending=True)
        df_logs = df_logs.drop(columns=['Temp_Timestamp'])
    
    base_dir = os.path.dirname(input_file)
    base_name = os.path.basename(input_file)
    stem, _ext = os.path.splitext(base_name)
    new_name = f"{stem}_sorted.xlsx"
    output_path = os.path.join(base_dir, new_name)

    print(f"[SORT] Saving to: {os.path.basename(output_path)}")
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        df_logs.to_excel(writer, sheet_name='Log Analysis', index=False)
        df_templates.to_excel(writer, sheet_name='Template Summary', index=False)

    return output_path

# ==========================================
# PART 3: REPORT & ANALYTICS
# ==========================================

def step_3_generate_report(file_path):
    print(f"[REPORT] Generating analytics for: {os.path.basename(file_path)}")
    
    base_dir = os.path.dirname(file_path)
    report_path = os.path.join(base_dir, "Executive_Summary.txt")
    
    # 1. Load Data
    try:
        df_logs = pd.read_excel(file_path, sheet_name='Log Analysis')
        try:
            df_templates = pd.read_excel(file_path, sheet_name='Template Summary')
            if not df_templates.empty:
                df_templates['Template ID'] = df_templates['Template ID'].astype(str)
                # Create maps for Meaning AND Pattern
                generic_meaning_map = dict(zip(df_templates['Template ID'], df_templates['Event Meaning']))
                pattern_map = dict(zip(df_templates['Template ID'], df_templates['Template Pattern']))
            else:
                generic_meaning_map = {}
                pattern_map = {}
        except:
            df_templates = pd.DataFrame()
            generic_meaning_map = {}
            pattern_map = {}
    except Exception as e:
        raise ValueError(f"Error reading Excel: {e}")

    # 2. Process Data
    df_logs.columns = [c.strip() for c in df_logs.columns]
    df_logs['params'] = df_logs['Parameters'].apply(lambda x: json.loads(x) if isinstance(x, str) else {})
    df_logs['USERNAME'] = df_logs['params'].apply(lambda x: x.get('USERNAME', 'N/A'))
    df_logs['RHOST'] = df_logs['params'].apply(lambda x: x.get('RHOST', 'N/A'))
    
    def extract_service(raw):
        try:
            parts = str(raw).split()
            if len(parts) > 4: return re.split(r'\[|:', parts[4])[0]
        except: pass
        return "Unknown"
    df_logs['Service'] = df_logs['Raw Log'].apply(extract_service)

    def parse_time(row):
        ts = row['params'].get('TIMESTAMP', '')
        if not ts: 
            parts = str(row['Raw Log']).split()
            if len(parts) >= 3: ts = " ".join(parts[:3])
        try:
            return pd.to_datetime(f"2024 {ts}", format="%Y %b %d %H:%M:%S")
        except:
            return pd.to_datetime(ts, errors='coerce')
    
    df_logs['datetime'] = df_logs.apply(parse_time, axis=1)
    df_logs = df_logs.dropna(subset=['datetime'])
    
    if len(df_logs) == 0:
        return "No valid timestamps found."

    df_logs['Template ID'] = df_logs['Template ID'].astype(str)

    def classify_severity(row):
        text = (str(row['Raw Log']) + " " + str(row['Meaning Log'])).lower()
        if any(x in text for x in ['critical', 'fatal', 'panic', 'emergency', 'alert', 'died']): return 'CRITICAL'
        if any(x in text for x in ['warning', 'warn', 'error', 'refused', 'failed']): return 'WARNING'
        return 'INFO'
    df_logs['Severity'] = df_logs.apply(classify_severity, axis=1)

    def classify_security(row):
        text = (str(row['Raw Log']) + " " + str(row['Meaning Log'])).lower()
        tags = []
        if 'illegal' in text or 'invalid user' in text: tags.append('Illegal Access')
        if 'authentication failure' in text or 'failed password' in text or "couldn't authenticate" in text: tags.append('Auth Failure')
        if 'sudo' in text or 'su(' in text or 'uid=0' in text or 'id=0' in text or 'user=root' in text: tags.append('Privilege Activity')
        if 'session opened' in text or 'accepted' in text: tags.append('Successful Login')
        if not tags: return 'Normal'
        return "; ".join(tags)
            
    df_logs['Security_Tag'] = df_logs.apply(classify_security, axis=1)

    # 3. Calculate Time Metrics
    min_time = df_logs['datetime'].min()
    max_time = df_logs['datetime'].max()
    duration = max_time - min_time
    total_hours = duration.total_seconds() / 3600

    # --- ADVANCED STATS CALCULATION FOR AI ---
    
    # A. Counts
    crit_count = len(df_logs[df_logs['Severity'] == 'CRITICAL'])
    warn_count = len(df_logs[df_logs['Severity'] == 'WARNING'])
    
    # B. Detailed Security Context
    priv_logs = df_logs[df_logs['Security_Tag'].str.contains('Privilege', na=False)]
    priv_count = len(priv_logs)
    unique_priv_users = priv_logs['USERNAME'].unique().tolist()
    unique_priv_users = [u for u in unique_priv_users if u != 'N/A']
    
    auth_fail_count = len(df_logs[df_logs['Security_Tag'].str.contains('Auth Failure', na=False)])
    
    # C. Login/Logout Analysis (Chronological Match) [UPDATED]
    login_mask = df_logs['Security_Tag'].str.contains('Successful Login', na=False)
    logout_mask = df_logs['Meaning Log'].str.lower().str.contains('session closed', na=False)
    
    # Filter only relevant events and sort by time
    session_events = df_logs.loc[login_mask | logout_mask].copy()
    
    # Tag event type for logic
    def get_event_type(row):
        if 'Successful Login' in row['Security_Tag']: return 'Login'
        return 'Logout'
    session_events['Event_Type'] = session_events.apply(get_event_type, axis=1)
    
    # Strict Sort by User then Time (Critical for the loop)
    session_events = session_events.sort_values(by=['USERNAME', 'datetime'])
    
    session_report_list = []
    
    # Group by user and iterate through their timeline
    for user, user_df in session_events.groupby('USERNAME'):
        if user == 'N/A': continue
        
        last_login_time = None
        
        for _, row in user_df.iterrows():
            if row['Event_Type'] == 'Login':
                # If we were already logged in, record the previous one as "Active/No Logout"
                if last_login_time is not None:
                    session_report_list.append(f"{user}: Logged in at {last_login_time} (Active/No Logout recorded)")
                # Start new session timer
                last_login_time = row['datetime']
                
            elif row['Event_Type'] == 'Logout':
                if last_login_time is not None:
                    # Match found! Calculate duration
                    duration = row['datetime'] - last_login_time
                    s = int(duration.total_seconds())
                    h, rem = divmod(s, 3600)
                    m, s = divmod(rem, 60)
                    dur_str = f"{h}h {m}m" if h > 0 else f"{m}m {s}s"
                    
                    session_report_list.append(f"{user}: {dur_str} ({last_login_time.strftime('%H:%M')} - {row['datetime'].strftime('%H:%M')})")
                    last_login_time = None
                # Else: Logout without login (orphan) -> Ignore
        
        # Check for any dangling login at the end of the loop
        if last_login_time is not None:
            session_report_list.append(f"{user}: Logged in at {last_login_time} (Active/No Logout)")

    # Summarize list for AI (Prevent Token Overflow)
    if session_report_list:
        # Take top 25 recent sessions to keep it concise for the AI
        session_str = "\n".join(session_report_list[:25])
        if len(session_report_list) > 25:
            session_str += f"\n... (and {len(session_report_list)-25} more sessions)"
    else:
        session_str = "No complete login sessions found."

    # Stats for counts
    success_count = len(df_logs[login_mask])
    logout_count = len(df_logs[logout_mask])
    
    # D. Top Actors
    top_services = df_logs['Service'].value_counts().head(3).index.tolist()
    top_users = df_logs[df_logs['USERNAME'] != 'N/A']['USERNAME'].value_counts().head(3).index.tolist()
    top_ips = df_logs[df_logs['RHOST'] != 'N/A']['RHOST'].value_counts().head(3).index.tolist()
    unique_ips_count = df_logs[df_logs['RHOST'] != 'N/A']['RHOST'].nunique()

    # E. Risk Highlights (With Template & Meaning)
    risk_df = df_logs[df_logs['Severity'].isin(['CRITICAL', 'WARNING'])]
    top_risk_templates = risk_df['Template ID'].value_counts().head(3)
    
    risk_details = []
    for tid, count in top_risk_templates.items():
        pattern = pattern_map.get(str(tid), "Unknown Pattern")
        meaning = generic_meaning_map.get(str(tid), "Unknown Meaning")
        risk_details.append(f"- [Template {tid} | Count: {count}] {meaning} (Pattern: {pattern})")
    
    risk_str = "\n".join(risk_details) if risk_details else "None detected."

    # F. Rarest Anomalies (With Pattern & Meaning)
    template_counts = df_logs['Template ID'].value_counts()
    min_occurrence = template_counts.min() if not template_counts.empty else 0
    rare_tids = template_counts[template_counts == min_occurrence].index.tolist()[:3] 
    
    rare_details = []
    for tid in rare_tids:
        meaning = generic_meaning_map.get(str(tid), "Unknown Meaning")
        pattern = pattern_map.get(str(tid), "Unknown Pattern")
        rare_details.append(f"- [T{tid}] {meaning} (Pattern: {pattern})")
    
    rare_str = "; ".join(rare_details) if rare_details else "None."

    # --- CONSTRUCT RICH TEXT FOR BART ---
    bart_input_text = (
        f"Executive Log Summary. "
        f"Time Range: {min_time} to {max_time} ({total_hours:.1f} hours). "
        f"Traffic: {len(df_logs)} events from {unique_ips_count} unique IPs. "
        f"Health Status: {crit_count} Critical, {warn_count} Warnings. "
        f"\n\nTOP RISK HIGHLIGHTS:\n{risk_str}\n\n"
        f"ACCESS CONTROL METRICS:\n"
        f"- Authentication Failures: {auth_fail_count}\n"
        f"- Privilege Escalation: {priv_count} events. Users involved: {', '.join(unique_priv_users)}.\n"
        f"- Login/Logout Activity:\n{session_str}\n\n"
        f"TOP VECTORS:\n"
        f"- Services: {', '.join(top_services)}\n"
        f"- Users: {', '.join(top_users)}\n"
        f"- Remote IPs: {', '.join(top_ips)}\n\n"
        f"ANOMALIES:\n"
        f"Detected {len(template_counts[template_counts == min_occurrence])} rare patterns appearing {min_occurrence} time(s). Examples: {rare_str}"
    )

    # 4. Generate AI Summary
    ai_summary = generate_summary(bart_input_text)

    # 5. Graph Settings
    if total_hours < 4:
        resample_rule = '1T'; date_format = '%H:%M'; xlabel_text = "Time (HH:MM)"; time_unit = "Minute"
    elif total_hours < 48:
        resample_rule = '1H'; date_format = '%d %b %H:00'; xlabel_text = "Time (Day Hour)"; time_unit = "Hour"
    else:
        resample_rule = '1D'; date_format = '%b %d'; xlabel_text = "Date"; time_unit = "Day"

    # 6. Generate Charts
    peak_str, peak_vol = create_all_charts(df_logs, base_dir, resample_rule, time_unit, date_format, xlabel_text)

    # 7. Generate Report
    write_executive_summary(df_logs, report_path, min_time, max_time, peak_str, peak_vol, total_hours, generic_meaning_map, ai_summary)
    
    return report_path