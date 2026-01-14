import pandas as pd
import json
import os
import re
from dateutil import parser

# --- NEW IMPORTS ---
from graph_generator import create_all_charts
from static_summary import write_executive_summary

# ==========================================
# PART 1: SENTENCE CONSTRUCTION
# ==========================================

def fill_meaning_from_json(row, meaning_map):
    """
    1. Grabs the 'Event Meaning' using the Template ID.
    2. Parses the 'Parameters' JSON.
    3. Replaces <USER> with 'root' in the sentence.
    """
    # Ensure ID is string to match the map keys
    template_id = str(row.get('Template ID', ''))
    params_json = row.get('Parameters')
    
    # Get the abstract meaning sentence
    meaning_template = meaning_map.get(template_id)
    
    if not meaning_template:
        return "Error: Template ID not found"
    
    if pd.isna(params_json) or str(params_json).strip() == '{}':
        return meaning_template

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
    
    # Ensure Template IDs are consistent strings
    df_logs['Template ID'] = df_logs['Template ID'].astype(str)
    df_templates['Template ID'] = df_templates['Template ID'].astype(str)

    # Map Templates {ID: Meaning}
    meaning_map = dict(zip(df_templates['Template ID'], df_templates['Event Meaning']))
    
    # Generate Specific Meanings
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
# PART 3: REPORT & GRAPHS
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
        if any(x in text for x in ['warning', 'warn', 'error', 'refused']): return 'WARNING'
        return 'INFO'
    df_logs['Severity'] = df_logs.apply(classify_severity, axis=1)

    def classify_security(row):
        text = str(row['Raw Log']).lower()
        if 'illegal' in text: return 'Illegal Access'
        if 'authentication failure' in text: return 'Auth Failure'
        if 'root' in text and 'session' in text: return 'Root Activity'
        if 'session opened' in text or 'accepted' in text: return 'Successful Login'
        return 'Normal'
    df_logs['Security_Tag'] = df_logs.apply(classify_security, axis=1)

    # 3. Calculate Time Metrics
    min_time = df_logs['datetime'].min()
    max_time = df_logs['datetime'].max()
    duration = max_time - min_time
    total_hours = duration.total_seconds() / 3600

    if total_hours < 4:
        resample_rule = '1T'; date_format = '%H:%M'; xlabel_text = "Time (HH:MM)"; time_unit = "Minute"
    elif total_hours < 48:
        resample_rule = '1H'; date_format = '%d %b %H:00'; xlabel_text = "Time (Day Hour)"; time_unit = "Hour"
    else:
        resample_rule = '1D'; date_format = '%b %d'; xlabel_text = "Date"; time_unit = "Day"

    # 4. Generate Charts (Using graph_generator)
    peak_str, peak_vol = create_all_charts(df_logs, base_dir, resample_rule, time_unit, date_format, xlabel_text)

    # 5. Generate Report (Using static_summary)
    write_executive_summary(df_logs, report_path, min_time, max_time, peak_str, peak_vol, total_hours, generic_meaning_map)
    
    return report_path