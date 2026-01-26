import re
import json
import os
import pandas as pd
from drain3 import TemplateMiner
from drain3.template_miner_config import TemplateMinerConfig
from drain3.masking import MaskingInstruction

# ==========================================
# 1. SETUP + CONFIGURATION
# ==========================================
def get_miner_config():
    config = TemplateMinerConfig()
    config.profiling_enabled = False
    config.drain_depth = 7 
    config.drain_sim_th = 0.75 
    config.mask_prefix = "" 
    config.mask_suffix = ""

    config.masking_instructions = [
    # FIX: Added spaces around '=' to match the raw log format "errno = 98"
    MaskingInstruction(r"\(Address already in use \(errno = \d+\)\)", "(Address already in use (errno = <NUM>))"),
    MaskingInstruction(r"FAILED LOGIN\s+\d+", "FAILED LOGIN <NUM>"),
    MaskingInstruction(r"fd\s+\d+", "fd <NUM>"),
    MaskingInstruction(r"\b\d+\s+seconds", "<NUM> seconds"),
    MaskingInstruction(r"\b\d+\s*([<>=!]+)\s*\d+", r"<NUM> \1 <NUM>"),
    MaskingInstruction(r"bad username\s*\[.*?\]", "bad username [<USERNAME>]"),
    MaskingInstruction(r"password changed for\s+\S+", "password changed for <USERNAME>"),
    MaskingInstruction(r"FOR\s+.*?,", "FOR <USERNAME>,"),
    
    # FIX: Handle "session opened for user ... by ..."
    # This captures both "by root" and "by (uid=0)" as <USERNAME>
    # FIX: Matches "LOGIN(uid=0)" OR just "(uid=0)" and converts both to "(uid=<UID>)"
    MaskingInstruction(r"\b(?:\w+)?\(uid=\d+\)", "(uid=<UID>)"),

    MaskingInstruction(r"([cC]onnect(?:ion)? from)\s+\S+", r"\1 <RHOST>"),
    # FIX: Added 'opened' and 'closed' to the state list
    MaskingInstruction(r"\b(startup|shutdown|opened|closed)\b(?!:)", "<STATE>"),
    
    # FTP Rule
    MaskingInstruction(r"ANONYMOUS FTP LOGIN FROM .+", "ANONYMOUS FTP LOGIN FROM <RHOST>"),
    # Captures "euid=0"
    MaskingInstruction(r"\beuid=\d+", "euid=<EUID>"),
    # Captures "tty=NODEVssh" or "tty=pts/0"
    MaskingInstruction(r"\btty=\S+", "tty=<TTY>"),
    # ---------------------------------------------------

    # 2. GENERIC VARIABLES (Low Priority)
    MaskingInstruction(r"\w{3}\s+\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}\s+\d{4}", "<TIMESTAMP>"),
    MaskingInstruction(r"\[\d+\]", "[<PID>]"),
    
    # FIX: Capture the prefix word (e.g., LOGIN, sshd) and keep it in the template
    MaskingInstruction(r"\b(\w+)\(uid=\d+\)", r"\1(uid=<UID>)"),
    
    MaskingInstruction(r"\buid=\d+", "uid=<UID>"),
    MaskingInstruction(r"user=\S+", "user=<USERNAME>"),
   # FIX: Don't match "user does" (as in "user does not have access")
    MaskingInstruction(r"user\s+(?!does\b)\S+", "user <USERNAME>"),
    
    # FIX: Added 'chars' to exclusion list so "(36 chars)" is not masked as RHOST
    MaskingInstruction(r"(?<=\s)\((?!uid=|Address|errno|ftpd|.*?chars)[^)]*\)", "(<RHOST>)"),

    # FIX: Handle explicit rhost=... (matches "rhost=1.2.3.4" -> "rhost=<RHOST>")
    MaskingInstruction(r"rhost=\S+", "rhost=<RHOST>"),
    
    # FIX: Handle naked IPs (matches "1.2.3.4" -> "<RHOST>")
    MaskingInstruction(r"((?<!\d)\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?!\d)(?::\d+)?)", "<RHOST>"),
]
    return config

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================
def remove_trailing_timestamp(text):
    """
    Removes the redundant 'at Sat Jun 18...' timestamp from the end of the line.
    """
    # Regex for: " at Sat Jun 18 02:08:12 2005" (at the end of string)
    return re.sub(r"\s+at\s+\w{3}\s+\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}\s+\d{4}$", "", text)

def normalize_login_uid(line):
    """
    Standardizes 'LOGIN(uid=0)' to just '(uid=0)' so it matches the template consistently.
    """
    return re.sub(r"\b\w+\(uid=", "(uid=", line)

def preprocess_log(log_line):
    # 1. Remove the redundant trailing timestamp first
    log_line = remove_trailing_timestamp(log_line)
    log_line = normalize_ftpd_rhost(log_line)
    
    # 2. Standardize the Header
    header_regex = r'^([A-Z][a-z]{2}\s+\d+\s\d{2}:\d{2}:\d{2})\s+(\S+)'
    log_line = re.sub(header_regex, '<TIMESTAMP> <HOSTNAME>', log_line)
    return log_line.strip()

def normalize_ftpd_rhost(line):
    pattern = re.compile(r"(connection from)\s+(\d{1,3}(?:\.\d{1,3}){3})\s*\(([^)]*)\)")
    def replacer(match):
        prefix, outer_ip, inner = match.group(1), match.group(2), match.group(3).strip()
        return f"{prefix} {outer_ip} ({inner})" if inner else f"{prefix} {outer_ip}"
    return pattern.sub(replacer, line)

def extract_named_parameters(clean_raw_line, template, line_index):
    """
    Extracts values using the Cleaned Raw Line (no trailing timestamp).
    """
    params = {}
    
    # --- PART A: Existing Template Matching Logic ---
    regex_pattern = re.escape(template)

    # Allow flexible whitespace
    regex_pattern = regex_pattern.replace(r"\ ", r"\s+?").replace(" ", r"\s+?")
    
    # Handle Drain Wildcards
    regex_pattern = regex_pattern.replace(r"\*", r"(.*?)")

    # Special tags mapping
    special_tags = {
        "<TIMESTAMP>": r"([A-Z][a-z]{2}\s+\d+\s\d{2}:\d{2}:\d{2})",
        "<HOSTNAME>": r"(\S+)"
    }

    # Replace special tags first
    for tag, pattern in special_tags.items():
        if tag in template:
            regex_pattern = regex_pattern.replace(re.escape(tag), pattern)

    # Replace remaining generic tags
    remaining_tags = re.findall(r"<[A-Z]+>", template)
    for tag in set(remaining_tags):
        if tag not in special_tags:
            regex_pattern = regex_pattern.replace(re.escape(tag), r"(.*?)")

    regex_pattern = f"^{regex_pattern}$"

    try:
        match = re.match(regex_pattern, clean_raw_line)
        if match:
            extracted_values = list(match.groups())
            ordered_tags = re.findall(r"<[A-Z]+>", template)
            
            if len(extracted_values) == len(ordered_tags):
                 for tag, value in zip(ordered_tags, extracted_values):
                    key = tag.strip("<>")
                    if value is None: value = ""
                    
                    if key in params:
                        params[key] = f"{params[key]}, {value}"
                    else:
                        params[key] = value
    except Exception:
        pass

    # --- PART B: FIX - Force Header Extraction ---
    # We manually extract the TIMESTAMP and HOSTNAME from the raw line 
    # to ensure they are always captured correctly, regardless of template matching.
    
    # This Regex matches: ^(Jun 18 20:20:20) (combo) ...
    header_match = re.search(r'^([A-Z][a-z]{2}\s+\d+\s\d{2}:\d{2}:\d{2})\s+(\S+)', clean_raw_line)
    
    if header_match:
        # Overwrite/Set these keys with the authoritative raw values
        params['TIMESTAMP'] = header_match.group(1)
        params['HOSTNAME'] = header_match.group(2)
    
    params['_Original_Line_Index'] = line_index

    return json.dumps(params)

# ==========================================
# 3. MAIN PARSING FUNCTION
# ==========================================
def parse_log_file(target_file):
    """
    Parses the given log file using Drain3 and exports to Excel.
    Returns: (output_excel_path, total_lines, unique_clusters)
    """
    if not os.path.exists(target_file):
        raise FileNotFoundError(f"File not found: {target_file}")

    # Initialize a FRESH miner for every run
    config = get_miner_config()
    template_miner = TemplateMiner(config=config)
    base_name, _ = os.path.splitext(target_file)
    output_excel = f"{base_name}_analysis.xlsx"
    rows = []

    # --- UPDATED TERMINAL OUTPUT START ---
    print("\n------ [PARSING INITIATED] ------")
    print(f"Input File:       {os.path.basename(target_file)}")

    with open(target_file, 'r', encoding='utf-8', errors='ignore') as f:
        for idx, line in enumerate(f): 
            raw_line = line.strip()
            if not raw_line: continue
            
            # 1. Preprocess & Mine
            content = preprocess_log(raw_line)
            result = template_miner.add_log_message(content)
            
            template = result['template_mined']
            cluster_id = result['cluster_id']
            
            # 2. Extract Variables
            clean_raw_line = remove_trailing_timestamp(raw_line)
            clean_raw_line = normalize_login_uid(clean_raw_line)
            clean_raw_line = normalize_ftpd_rhost(clean_raw_line)
            
            params_json = extract_named_parameters(clean_raw_line, template, idx)
            
            rows.append({
                "Raw Log": raw_line,
                "Drained Named Log": template,
                "Template ID": cluster_id,
                "Parameters": params_json
            })

    if not rows:
        return None, 0, 0
    # --- UPDATED TERMINAL OUTPUT END ---
    unique_clusters = len(template_miner.drain.clusters)
    print(f"Unique Templates: {unique_clusters}")
    print("---------------------------------")
    print(f"File Saved To:    {os.path.abspath(output_excel)}\n")
        
        # Create DataFrames
    df_logs = pd.DataFrame(rows)
    df_logs = df_logs.sort_values(by="Template ID")
    df_logs = df_logs[["Raw Log", "Drained Named Log", "Template ID", "Parameters"]]
    
    clusters = []
    for cluster in template_miner.drain.clusters:
        clusters.append({
            "Template ID": cluster.cluster_id,
            "Template Pattern": cluster.get_template(),
            "Occurrences": cluster.size
        })
    df_summary = pd.DataFrame(clusters)
    df_summary = df_summary.sort_values(by="Occurrences", ascending=False)
    
    # Write to Excel
    with pd.ExcelWriter(output_excel) as writer:
        df_logs.to_excel(writer, sheet_name='Log Analysis', index=False)
        df_summary.to_excel(writer, sheet_name='Template Summary', index=False)
    
    return output_excel, len(df_logs), len(df_summary)
        