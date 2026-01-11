import pandas as pd
import json
import os
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from dateutil import parser
import re
import textwrap

# ==========================================
# PART 1: SENTENCE CONSTRUCTION
# ==========================================

def fill_meaning_from_json(row, meaning_map):
    """
    1. Grabs the 'Event Meaning' using the Template ID.
    2. Parses the 'Parameters' JSON (e.g., {"USER": "root"}).
    3. Replaces <USER> with 'root' in the sentence.
    """
    template_id = row.get('Template ID')
    params_json = row.get('Parameters')
    
    # Get the abstract meaning sentence (e.g. "User <USER> failed login")
    meaning_template = meaning_map.get(template_id)
    
    if not meaning_template:
        return "Error: Template ID not found"
    
    # If no parameters, return the template as is
    if pd.isna(params_json) or str(params_json).strip() == '{}':
        return meaning_template

    try:
        # Parse JSON and replace placeholders
        params_dict = json.loads(str(params_json))
        final_sentence = meaning_template
        
        for key, value in params_dict.items():
            placeholder = f"<{key}>"
            # Replace <KEY> with value (convert value to string just in case)
            final_sentence = final_sentence.replace(placeholder, str(value))
            
        return final_sentence

    except:
        # If JSON fails, return the template with placeholders intact
        return meaning_template
    
def step_1_merge_sentences(input_file):
    """
    Reads the input Excel (with generic meanings), fills in specific parameters,
    and saves a new Excel file with a 'Meaning Log' column.
    """
    print(f"[Summary Step 1] Merging parameters in: {os.path.basename(input_file)}")
    
    # 1. Load Data
    try:
        df_logs = pd.read_excel(input_file, sheet_name="Log Analysis")
        df_templates = pd.read_excel(input_file, sheet_name="Template Summary")
    except Exception as e:
        raise ValueError(f"Error reading Excel file: {e}")
    
    # 2. Map Templates {ID: Meaning}
    meaning_map = dict(zip(df_templates['Template ID'], df_templates['Event Meaning']))
    
    # 3. Generate Specific Meanings
    # We apply the helper function row by row
    df_logs['Meaning Log'] = df_logs.apply(lambda row: fill_meaning_from_json(row, meaning_map), axis=1)
    
    # 4. Reorder Columns (Put 'Meaning Log' next to 'Raw Log' for better visibility)
    cols = list(df_logs.columns)
    if 'Raw Log' in cols and 'Meaning Log' in cols:
        # Remove 'Meaning Log' from current position
        cols.pop(cols.index('Meaning Log'))
        # Insert it right after 'Raw Log'
        target_index = cols.index('Raw Log') + 1
        cols.insert(target_index, 'Meaning Log')
        df_logs = df_logs[cols]

    # 5. Save Output
    base_dir = os.path.dirname(input_file)
    base_name = os.path.basename(input_file)
    
    # Output filename: <inputfilename>_merged.xlsx
    # Example: myfile.xlsx -> myfile_merged.xlsx
    stem, _ext = os.path.splitext(base_name)
    new_name = f"{stem}_merged.xlsx"
        
    output_path = os.path.join(base_dir, new_name)
    
    print(f"[Summary Step 1] Saving to: {os.path.basename(output_path)}")
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        df_logs.to_excel(writer, sheet_name='Log Analysis', index=False)
        df_templates.to_excel(writer, sheet_name='Template Summary', index=False)
        
    return output_path