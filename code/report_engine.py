import pandas as pd
import json
import os
import re
from dateutil import parser

# --- IMPORTS FROM NEW MODULES ---
from graph_generator import create_all_charts
from static_report import write_executive_report
from fail2ban_logic import scan_threats

# ==========================================
# PART 1: SENTENCE CONSTRUCTION
# ==========================================

def fill_meaning_from_json(row, meaning_map):
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
    print(f"[SORT] Processing Excel: {os.path.basename(input_file)}")
    
    # 1. Load the Excel Data
    try:
        df_logs = pd.read_excel(input_file, sheet_name="Log Analysis")
        df_templates = pd.read_excel(input_file, sheet_name="Template Summary")
    except Exception as e:
        raise ValueError(f"Error reading Excel file: {e}")

    # 2. Sort using the Embedded Index (Source of Truth)
    if 'Parameters' in df_logs.columns:
        print("[SORT] Sorting based on embedded '_Original_Line_Index'...")

        def get_index_from_json(params_str):
            try:
                if pd.isna(params_str): return 999999999
                # Parse JSON
                params = json.loads(str(params_str))
                # Extract the index we saved in parser.py (default to high number if missing)
                return int(params.get('_Original_Line_Index', 999999999))
            except:
                return 999999999

        # Create temporary sorting column
        df_logs['_Sort_Index'] = df_logs['Parameters'].apply(get_index_from_json)
        
        # Verify if we actually found indices
        valid_count = (df_logs['_Sort_Index'] != 999999999).sum()
        print(f"[SORT] Found valid indices for {valid_count}/{len(df_logs)} rows.")

        # Perform the Sort
        df_logs = df_logs.sort_values(by='_Sort_Index', ascending=True)
        
        # Clean up
        df_logs = df_logs.drop(columns=['_Sort_Index'])
        
    else:
        print("[WARN] 'Parameters' column missing. Cannot perform strict sorting.")

    # 3. Save Sorted File
    base_dir = os.path.dirname(input_file)
    filename = os.path.basename(input_file)
    stem, _ext = os.path.splitext(filename)
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
    report_path = os.path.join(base_dir, "Log_Analysis_Report.md")
    
    # 1. Load Data
    try:
        df_logs = pd.read_excel(file_path, sheet_name='Log Analysis')
        try:
            df_templates = pd.read_excel(file_path, sheet_name='Template Summary')
            if not df_templates.empty:
                df_templates['Template ID'] = df_templates['Template ID'].astype(str)
                generic_meaning_map = dict(zip(df_templates['Template ID'], df_templates['Event Meaning']))
            else:
                generic_meaning_map = {}
        except:
            df_templates = pd.DataFrame()
            generic_meaning_map = {}
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

# --- YEAR SCANNING LOGIC ---
    import datetime
 # 1. Detect Anchor Year
    anchor_year = datetime.datetime.now().year
    found_year = False
    
    # CHANGE: Instead of a subset, we iterate through the ENTIRE dataframe.
    # We use df_logs.iterrows() directly.
    for index, row in df_logs.iterrows():
        
        # Priority A: Check JSON Timestamp
        ts_json = str(row['params'].get('TIMESTAMP', ''))
        match_json = re.search(r'(20\d{2})', ts_json)
        
        if match_json:
            anchor_year = int(match_json.group(1))
            found_year = True
            break  # STOP scanning once we find it!
        
        # Priority B: Check END of Raw Log
        raw_str = str(row['Raw Log']).strip()
        match_end = re.search(r'(20\d{2})\s*$', raw_str)
        
        if match_end:
            anchor_year = int(match_end.group(1))
            found_year = True
            break  # STOP scanning once we find it!
            
    print(f"[TIME] Year detected: {anchor_year} (Source: {'Logs' if found_year else 'System Date'})")

   # 2. Parse Dates (Robust Method)
    def parse_time(row):
        ts = row['params'].get('TIMESTAMP', '')
        
        # Fallback: Scrape Raw Log if JSON is empty
        if not ts: 
            parts = str(row['Raw Log']).split()
            # Standard syslog often puts date at START (Jul 15 ...)
            if len(parts) >= 3: ts = " ".join(parts[:3])
            
        try:
            ts_str = str(ts).strip()
            
            # PREPEND YEAR FIX:
            # If timestamp doesn't start with 20xx, prepend the anchor year.
            if not re.match(r'^20\d{2}', ts_str):
                ts_str = f"{anchor_year} {ts_str}"
            
            return pd.to_datetime(ts_str)
        except:
            return pd.NaT

    df_logs['datetime'] = df_logs.apply(parse_time, axis=1)
    
    # 3. Handle Year Rollover (Dec 31 -> Jan 01)
    mask_valid = df_logs['datetime'].notna()
    if mask_valid.sum() > 0:
        months = df_logs.loc[mask_valid, 'datetime'].dt.month.tolist()
        
        rollover_index = -1
        # Scan for the "12 -> 1" drop
        for i in range(len(months) - 1):
            if months[i] == 12 and months[i+1] == 1:
                rollover_index = i + 1
                break
        
        # Apply +1 Year to everything after the rollover
        if rollover_index != -1:
            print("[TIME] Detected Year Rollover (Dec -> Jan). Adjusting subsequent logs.")
            valid_indices = df_logs[mask_valid].index
            indices_to_update = valid_indices[rollover_index:]
            
            df_logs.loc[indices_to_update, 'datetime'] = df_logs.loc[indices_to_update, 'datetime'].apply(
                lambda dt: dt.replace(year=dt.year + 1)
            )

    # Filter out invalid dates
    df_logs = df_logs.dropna(subset=['datetime'])
    
    def classify_severity(row):
        text = (str(row['Raw Log']) + " " + str(row['Meaning Log'])).lower()
        if 'peer died' in text: return 'INFO' # to remove peer died case of telnetd[16732]: ttloop:  peer died: Invalid or incomplete multibyte or wide character
        if any(x in text for x in ['critical', 'fatal', 'panic', 'emergency', 'alert', 'died']): return 'CRITICAL'
        if any(x in text for x in ['warning', 'warn', 'error', 'refused', 'failed']): return 'WARNING'
        return 'INFO'
    df_logs['Severity'] = df_logs.apply(classify_severity, axis=1)

    def classify_security(row):
        text = (str(row['Raw Log']) + " " + str(row['Meaning Log'])).lower()
        svc = str(row['Service']).lower()
        tags = []
        if 'illegal' in text or 'invalid user' in text: tags.append('Illegal Access')
        if 'authentication failure' in text or 'failed password' in text or "couldn't authenticate" in text: tags.append('Auth Failure')
        if 'sudo' in svc or 'su' in svc or 'uid=0' in text or 'id=0' in text or 'user=root' in text: tags.append('Privilege Activity')
        if 'session opened' in text or 'accepted' in text: tags.append('Successful Login')
        if 'session closed' in text or 'logged out' in text: tags.append('Session Logout')
        if not tags: return 'Normal'
        return "; ".join(tags)
            
    df_logs['Security_Tag'] = df_logs.apply(classify_security, axis=1)

    # 3. Calculate Time Metrics
    min_time = df_logs['datetime'].min()
    max_time = df_logs['datetime'].max()
    duration = max_time - min_time
    total_hours = duration.total_seconds() / 3600

    # 4. Graph Settings
    if total_hours < 4:
        resample_rule = '1T'; date_format = '%H:%M'; xlabel_text = "Time (HH:MM)"; time_unit = "Minute"
    elif total_hours < 48:
        resample_rule = '1H'; date_format = '%d %b %H:00'; xlabel_text = "Time (Day Hour)"; time_unit = "Hour"
    else:
        resample_rule = '1D'; date_format = '%b %d'; xlabel_text = "Date"; time_unit = "Day"

    # 5. Generate Charts
    peak_str, peak_vol = create_all_charts(df_logs, base_dir, resample_rule, time_unit, date_format, xlabel_text)

    # 6. Threat Scanning (Fail2Ban)
    try:
        threat_df = scan_threats(df_logs, findtime='10min', maxretry=5)
    except Exception as e:
        print(f"[WARN] Threat scanning failed: {e}")
        threat_df = None

    # 7. Generate Main Report (Static)
    write_executive_report(df_logs, report_path, min_time, max_time, peak_str, peak_vol, total_hours, generic_meaning_map, threat_df=threat_df)

    return report_path