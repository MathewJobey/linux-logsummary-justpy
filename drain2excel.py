import justpy as jp
import os
import re
import json
import pandas as pd
from drain3 import TemplateMiner
from drain3.template_miner_config import TemplateMinerConfig
from drain3.masking import MaskingInstruction

# ==========================================
# PART 1: LOGIC FROM DATA_CLEANER.PY
# ==========================================

BLACKLIST = [
    # 1. Hardware & Boot
    "kernel", "rc", "irqbalance", "sysctl", "network", "random", "udev", 
    "apmd", "smartd", "init",
    # 2. Peripherals
    "bluetooth", "sdpd", "hcid", "cups", "gpm",
    # 3. System Housekeeping
    "logrotate", "syslog", "klogd", "crond", "anacron", "atd", "readahead", 
    "messagebus", "ntpd", "dd",
    # 4. Network Plumbing
    "rpc.statd", "rpcidmapd", "portmap", "nfslock", "automount", "ifup", 
    "netfs", "autofs",
    # 5. PROXIES & SERVERS
    "privoxy", "squid", "sendmail", "spamassassin", "httpd", "xfs", 
    "IIim", "htt", "htt_server", "canna", "named", "rsyncd", "mysqld", "FreeWnn"
]

def run_cleaner_logic(input_filename):
    """Refactored logic from data_cleaner.py"""
    if not os.path.exists(input_filename):
        return None, f"Error: '{input_filename}' not found.", None

    base_name, extension = os.path.splitext(input_filename)
    output_filename = f"{base_name}_clean{extension}"
    trash_filename = f"{base_name}_trash{extension}"

    removed_count = 0
    kept_count = 0

    try:
        with open(input_filename, 'r') as infile, \
             open(output_filename, 'w') as outfile, \
             open(trash_filename, 'w') as trashfile:
            
            for line in infile:
                stripped_line = line.strip()
                if not stripped_line: continue

                tokens = stripped_line.split()

                # Safety check for short lines
                if len(tokens) < 5:
                    outfile.write(line)
                    kept_count += 1
                    continue

                process_token = tokens[4] 

                matched_keyword = None
                for bad_process in BLACKLIST:
                    if process_token.startswith(bad_process):
                        matched_keyword = bad_process
                        break
                
                if matched_keyword:
                    trashfile.write(f"[MATCHED: {matched_keyword}] {line}")
                    removed_count += 1
                else:
                    outfile.write(line)
                    kept_count += 1
        
        msg = (f"Cleaning Complete.\n"
               f"Kept: {kept_count} lines\n"
               f"Removed: {removed_count} lines\n"
               f"Clean file saved to: {output_filename}")
        return output_filename, msg, trash_filename

    except Exception as e:
        return None, f"Error during cleaning: {str(e)}", None


# ==========================================
# PART 2: LOGIC FROM DRAIN2EXCEL.PY
# ==========================================

def get_drain_config():
    """Recreates the specific configuration from drain2excel.py"""
    config = TemplateMinerConfig()
    config.profiling_enabled = False
    config.drain_depth = 7 
    config.drain_sim_th = 0.75 
    config.mask_prefix = "" 
    config.mask_suffix = ""

    config.masking_instructions = [
        MaskingInstruction(r"\(Address already in use \(errno = \d+\)\)", "(Address already in use (errno = <NUM>))"),
        MaskingInstruction(r"FAILED LOGIN\s+\d+", "FAILED LOGIN <NUM>"),
        MaskingInstruction(r"fd\s+\d+", "fd <NUM>"),
        MaskingInstruction(r"\b\d+\s+seconds", "<NUM> seconds"),
        MaskingInstruction(r"\b\d+\s*([<>=!]+)\s*\d+", r"<NUM> \1 <NUM>"),
        MaskingInstruction(r"bad username\s*\[.*?\]", "bad username [<USERNAME>]"),
        MaskingInstruction(r"password changed for\s+\S+", "password changed for <USERNAME>"),
        MaskingInstruction(r"FOR\s+.*?,", "FOR <USERNAME>,"),
        MaskingInstruction(r"\b(?:\w+)?\(uid=\d+\)", "(uid=<UID>)"),
        MaskingInstruction(r"([cC]onnect(?:ion)? from)\s+\S+", r"\1 <RHOST>"),
        MaskingInstruction(r"\b(startup|shutdown|opened|closed)\b(?!:)", "<STATE>"),
        MaskingInstruction(r"ANONYMOUS FTP LOGIN FROM .+", "ANONYMOUS FTP LOGIN FROM <RHOST>"),
        MaskingInstruction(r"\beuid=\d+", "euid=<EUID>"),
        MaskingInstruction(r"\btty=\S+", "tty=<TTY>"),
        MaskingInstruction(r"\w{3}\s+\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}\s+\d{4}", "<TIMESTAMP>"),
        MaskingInstruction(r"\[\d+\]", "[<PID>]"),
        MaskingInstruction(r"\b(\w+)\(uid=\d+\)", r"\1(uid=<UID>)"),
        MaskingInstruction(r"\buid=\d+", "uid=<UID>"),
        MaskingInstruction(r"user=\S+", "user=<USERNAME>"),
        MaskingInstruction(r"user\s+(?!does\b)\S+", "user <USERNAME>"),
        MaskingInstruction(r"(?<=\s)\((?!uid=|Address|errno|ftpd|.*?chars)[^)]*\)", "(<RHOST>)"),
        MaskingInstruction(r"rhost=\S+", "rhost=<RHOST>"),
        MaskingInstruction(r"((?<!\d)\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?!\d)(?::\d+)?)", "<RHOST>"),
    ]
    return config

def remove_trailing_timestamp(text):
    trailing_regex = r"\s+at\s+\w{3}\s+\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}\s+\d{4}$"
    return re.sub(trailing_regex, "", text)

def normalize_login_uid(line):
    return re.sub(r"\b\w+\(uid=", "(uid=", line)

def normalize_ftpd_rhost(line):
    pattern = re.compile(r"(connection from)\s+(\d{1,3}(?:\.\d{1,3}){3})\s*\(([^)]*)\)")
    def replacer(match):
        prefix = match.group(1)
        outer_ip = match.group(2)
        inner = match.group(3).strip()
        if inner: return f"{prefix} {outer_ip} ({inner})"
        else: return f"{prefix} {outer_ip}"
    return pattern.sub(replacer, line)

def preprocess_log(log_line):
    log_line = remove_trailing_timestamp(log_line)
    log_line = normalize_ftpd_rhost(log_line)
    header_regex = r'^([A-Z][a-z]{2}\s+\d+\s\d{2}:\d{2}:\d{2})\s+(\S+)'
    log_line = re.sub(header_regex, '<TIMESTAMP> <HOSTNAME>', log_line)
    return log_line.strip()

def extract_named_parameters(clean_raw_line, template):
    params = {}
    regex_pattern = re.escape(template)
    regex_pattern = regex_pattern.replace(r"\ ", r"\s+?")
    regex_pattern = regex_pattern.replace(" ", r"\s+?")
    regex_pattern = regex_pattern.replace(r"\*", r"(.*?)")

    special_tags = {
        "<TIMESTAMP>": r"([A-Z][a-z]{2}\s+\d+\s\d{2}:\d{2}:\d{2})",
        "<HOSTNAME>": r"(\S+)"
    }
    for tag, pattern in special_tags.items():
        if tag in template:
            regex_pattern = regex_pattern.replace(re.escape(tag), pattern)

    remaining_tags = re.findall(r"<[A-Z]+>", template)
    for tag in set(remaining_tags):
        if tag not in special_tags:
            regex_pattern = regex_pattern.replace(re.escape(tag), r"(.*?)")

    regex_pattern = f"^{regex_pattern}$"

    try:
        match = re.match(regex_pattern, clean_raw_line)
        if not match: return json.dumps({})
        extracted_values = list(match.groups())
        ordered_tags = re.findall(r"<[A-Z]+>", template)
        
        if len(extracted_values) == len(ordered_tags):
             for tag, value in zip(ordered_tags, extracted_values):
                key = tag.strip("<>")
                if value is None: value = ""
                if key in params:
                    if value not in params[key]:
                        params[key] = f"{params[key]}, {value}"
                else:
                    params[key] = value
    except Exception:
        pass
    return json.dumps(params)

def run_parser_logic(target_file):
    """Refactored logic from drain2excel.py"""
    if not os.path.exists(target_file):
        return None, f"Error: '{target_file}' not found."

    base_name, _ = os.path.splitext(target_file)
    output_excel = f"{base_name}_analysis.xlsx"
    
    template_miner = TemplateMiner(config=get_drain_config())
    rows = []

    try:
        with open(target_file, 'r') as f:
            for line in f:
                raw_line = line.strip()
                if not raw_line: continue
                
                # Preprocess & Mine
                content = preprocess_log(raw_line)
                result = template_miner.add_log_message(content)
                template = result['template_mined']
                cluster_id = result['cluster_id']
                
                # Extract Variables
                clean_raw_line = remove_trailing_timestamp(raw_line)
                clean_raw_line = normalize_login_uid(clean_raw_line)
                clean_raw_line = normalize_ftpd_rhost(clean_raw_line)
                
                params_json = extract_named_parameters(clean_raw_line, template)
                
                rows.append({
                    "Raw Log": raw_line,
                    "Drained Named Log": template,
                    "Template ID": cluster_id,
                    "Parameters": params_json
                })

        if rows:
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
            
            with pd.ExcelWriter(output_excel) as writer:
                df_logs.to_excel(writer, sheet_name='Log Analysis', index=False)
                df_summary.to_excel(writer, sheet_name='Template Summary', index=False)
            
            msg = (f"Analysis Complete!\n"
                   f"Total Lines: {len(df_logs)}\n"
                   f"Unique Clusters: {len(df_summary)}\n"
                   f"File saved: {output_excel}")
            return output_excel, msg
        else:
            return None, "Warning: No logs found in the file."
            
    except Exception as e:
        return None, f"Error during parsing: {str(e)}"

# ==========================================
# PART 3: JUSTPY UI
# ==========================================

async def analyze_app():
    wp = jp.QuasarPage()
    wp.title = "Log Analysis Tool"

    # --- Header ---
    div_main = jp.Div(classes="q-pa-md", a=wp)
    jp.Div(text="Surgical Log Cleaner & Parser", classes="text-h4 q-mb-md", a=div_main)

    # --- Step 1: Input ---
    jp.Div(text="Step 1: Select File", classes="text-h6", a=div_main)
    
    input_wrapper = jp.Div(classes="row q-gutter-md items-center", a=div_main)
    file_input = jp.Input(placeholder="Enter filename (e.g., Linux_2k.log)", 
                          value="Linux_2k.log", 
                          classes="q-pa-sm border rounded", 
                          style="width: 300px;", a=input_wrapper)
    
    # --- Console Output Area ---
    console_area = jp.Pre(classes="bg-grey-2 q-pa-md q-mt-md rounded-borders", 
                          style="min-height: 150px; overflow-x: auto;", a=div_main)
    console_area.text = "System Ready. Waiting for input..."

    # --- Step 2 & 3: Actions ---
    action_wrapper = jp.Div(classes="row q-gutter-md q-mt-md", a=div_main)
    
    # Store state for the parsed filename
    wp.cleaned_file_path = None

    # --- Event Handlers ---
    
    def on_clean_click(self, msg):
        input_file = file_input.value.strip()
        console_area.text = f"Running Cleaner on {input_file}...\n"
        
        cleaned_file, log_msg, trash_file = run_cleaner_logic(input_file)
        
        if cleaned_file:
            console_area.text += log_msg
            wp.cleaned_file_path = cleaned_file
            # Enable parse button
            btn_parse.disable = False
            btn_parse.set_class("bg-primary")
            btn_parse.set_class("text-white")
        else:
            console_area.text += log_msg
            
    def on_parse_click(self, msg):
        if not wp.cleaned_file_path:
            console_area.text += "\n\nError: No clean file found. Please run cleaning first."
            return

        console_area.text += f"\n\nRunning Drain3 Parser on {wp.cleaned_file_path}..."
        excel_file, log_msg = run_parser_logic(wp.cleaned_file_path)
        
        console_area.text += "\n" + "-"*30 + "\n"
        console_area.text += log_msg

    # --- Buttons ---
    btn_clean = jp.Button(text="Clean Logs", classes="q-btn bg-teal text-white", a=action_wrapper)
    btn_clean.on('click', on_clean_click)

    btn_parse = jp.Button(text="Analyze & Generate Excel", classes="q-btn bg-grey-4 text-grey-8", disable=True, a=action_wrapper)
    btn_parse.on('click', on_parse_click)

    return wp

# Run the app
jp.justpy(analyze_app)