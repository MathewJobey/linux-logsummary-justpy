import justpy as jp
import os
import sys
import asyncio

# Add code folder to path to avoid conflict with built-in 'code' module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'code'))

from cleaner import clean_log_file
from parser import (
    template_miner, preprocess_log, remove_trailing_timestamp,
    normalize_login_uid, normalize_ftpd_rhost, extract_named_parameters
)
import pandas as pd

# ==========================================
# BLACKLIST (for display)
# ==========================================
BLACKLIST = [
    "kernel", "rc", "irqbalance", "sysctl", "network", "random", "udev",
    "apmd", "smartd", "init",
    "bluetooth", "sdpd", "hcid", "cups", "gpm",
    "logrotate", "syslog", "klogd", "crond", "anacron", "atd", "readahead",
    "messagebus", "ntpd", "dd",
    "rpc.statd", "rpcidmapd", "portmap", "nfslock", "automount", "ifup",
    "netfs", "autofs",
    "privoxy", "squid", "sendmail", "spamassassin", "httpd", "xfs",
    "IIim", "htt", "htt_server", "canna", "named", "rsyncd", "mysqld", "FreeWnn"
]

# ==========================================
# GLOBAL STATE
# ==========================================
class AppState:
    uploaded_file_path = None
    cleaned_file_path = None

state = AppState()

# ==========================================
# STYLES
# ==========================================
card_style = """
    background-color: white;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    padding: 24px;
    margin-bottom: 20px;
"""

button_primary = """
    background-color: #2563eb;
    color: white;
    padding: 12px 24px;
    border-radius: 6px;
    border: none;
    cursor: pointer;
    font-weight: 500;
    width: 100%;
"""

button_secondary = """
    background-color: #f3f4f6;
    color: #374151;
    padding: 8px 16px;
    border-radius: 6px;
    border: 1px solid #d1d5db;
    cursor: pointer;
    font-weight: 500;
"""

input_style = """
    width: 100%;
    padding: 12px;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    font-size: 14px;
    box-sizing: border-box;
"""

# ==========================================
# COMPONENT BUILDERS
# ==========================================
def create_header(container):
    """Create the header with logo and title"""
    header = jp.Div(a=container, classes="text-center mb-8")
    
    # Linux penguin emoji as logo
    logo = jp.Div(a=header, classes="text-5xl mb-2")
    logo.inner_html = "🐧"
    
    title = jp.H1(a=header, text="Linux Log Analysis Pipeline",
                  classes="text-2xl font-bold text-blue-600")
    return header


def create_step_card(container, step_num, title, description):
    """Create a step card container"""
    card = jp.Div(a=container, style=card_style)
    
    # Step header
    header = jp.Div(a=card, classes="flex items-center gap-2 mb-2")
    step_badge = jp.Span(a=header, text="📄", classes="text-lg")
    step_title = jp.Span(a=header, text=f"Step {step_num}: {title}",
                         classes="font-semibold text-gray-800")
    
    # Description
    jp.P(a=card, text=description, classes="text-gray-500 text-sm mb-4")
    
    return card


def create_file_upload_area(card, on_file_change):
    """Create file upload/drag area"""
    upload_area = jp.Div(a=card, classes="mb-4")
    
    # Drag and drop text
    jp.P(a=upload_area, text="Drag and drop file here",
         classes="text-center text-gray-400 mb-3")
    
    # File input row
    file_row = jp.Div(a=upload_area, classes="flex items-center justify-center gap-3 mb-4")
    
    # File input button
    file_input = jp.Input(a=file_row, type="file", accept=".log,.txt",
                          classes="hidden", id="file-input")
    
    select_btn = jp.Button(a=file_row, text="📁 Select Log File",
                           style=button_secondary,
                           click=lambda self, msg: msg.page.run_javascript(
                               "document.getElementById('file-input').click()"))
    
    file_label = jp.Span(a=file_row, text="No file selected",
                         classes="text-gray-500 text-sm", name="file_label")
    
    file_input.on("change", on_file_change)
    file_input.file_label = file_label
    
    return upload_area, file_input, file_label


def create_manual_path_input(card):
    """Create manual path input section"""
    jp.Div(a=card, classes="text-center text-gray-400 text-sm my-4").inner_html = "OR"
    
    path_input = jp.Input(a=card, type="text",
                          placeholder="Enter path manually (e.g., Logs/Linux_2k.log)",
                          style=input_style, classes="mb-4")
    return path_input


def create_blacklist_accordion(card):
    """Create expandable blacklist section"""
    accordion = jp.Div(a=card, classes="mt-4")
    
    # Toggle header
    toggle_row = jp.Div(a=accordion, classes="flex items-center gap-2 cursor-pointer py-2")
    arrow = jp.Span(a=toggle_row, text="▶", classes="text-xs text-gray-500", name="arrow")
    checkbox = jp.Input(a=toggle_row, type="checkbox", classes="mr-1")
    jp.Span(a=toggle_row, text="View blacklisted process keywords",
            classes="text-sm text-gray-600")
    
    # Content (hidden by default)
    content = jp.Div(a=accordion, classes="hidden mt-3 p-3 bg-gray-50 rounded-lg",
                     name="blacklist_content")
    
    # Display blacklist in columns
    grid = jp.Div(a=content, classes="grid grid-cols-4 gap-2 text-xs text-gray-600")
    for keyword in BLACKLIST:
        jp.Span(a=grid, text=keyword, classes="bg-gray-200 px-2 py-1 rounded")
    
    def toggle_blacklist(self, msg):
        if "hidden" in content.classes:
            content.classes = content.classes.replace("hidden", "")
            arrow.text = "▼"
        else:
            content.classes += " hidden"
            arrow.text = "▶"
    
    toggle_row.on("click", toggle_blacklist)
    
    return accordion


def create_status_area(container):
    """Create status message area"""
    status = jp.Div(a=container, classes="mt-4 p-4 rounded-lg hidden", name="status")
    return status


# ==========================================
# EVENT HANDLERS
# ==========================================
async def on_file_selected(self, msg):
    """Handle file selection"""
    if msg.file_info:
        file_info = msg.file_info[0]
        filename = file_info['name']
        self.file_label.text = filename
        
        # Save file content
        file_content = file_info['file_content']
        
        # Save to Logs folder
        logs_dir = "Logs"
        os.makedirs(logs_dir, exist_ok=True)
        
        save_path = os.path.join(logs_dir, filename)
        
        # Decode and save
        import base64
        content = base64.b64decode(file_content.split(',')[1]).decode('utf-8', errors='ignore')
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        state.uploaded_file_path = save_path
        await msg.page.update()


async def clean_log_clicked(self, msg):
    """Handle Clean Log File button click"""
    page = msg.page
    status = page.status_area
    path_input = page.path_input
    
    # Determine file path
    file_path = path_input.value.strip() if path_input.value.strip() else state.uploaded_file_path
    
    if not file_path:
        status.classes = "mt-4 p-4 rounded-lg bg-red-100 text-red-700"
        status.text = "⚠️ Please select a file or enter a path first."
        await page.update()
        return
    
    # Show processing status
    status.classes = "mt-4 p-4 rounded-lg bg-blue-100 text-blue-700"
    status.text = "🔄 Cleaning log file..."
    await page.update()
    
    # Run cleaner
    result = clean_log_file(file_path)
    
    if result is None:
        status.classes = "mt-4 p-4 rounded-lg bg-red-100 text-red-700"
        status.text = f"❌ Error: Could not find '{file_path}'"
    else:
        output_file, trash_file, kept, removed = result
        state.cleaned_file_path = output_file
        status.classes = "mt-4 p-4 rounded-lg bg-green-100 text-green-700"
        status.inner_html = f"""
            ✅ <strong>Cleaning Complete!</strong><br>
            • Kept: {kept} lines → <code>{output_file}</code><br>
            • Removed: {removed} lines → <code>{trash_file}</code>
        """
        
        # Enable Step 2 button
        page.parse_btn.set_class("opacity-100")
        page.parse_btn.disabled = False
    
    await page.update()


async def parse_log_clicked(self, msg):
    """Handle Parse Log File button click"""
    page = msg.page
    status = page.status_area_2
    path_input = page.path_input_2
    
    # Determine file path
    file_path = path_input.value.strip() if path_input.value.strip() else state.cleaned_file_path
    
    if not file_path:
        status.classes = "mt-4 p-4 rounded-lg bg-red-100 text-red-700"
        status.text = "⚠️ Please clean a log file first or enter a path."
        await page.update()
        return
    
    # Show processing status
    status.classes = "mt-4 p-4 rounded-lg bg-blue-100 text-blue-700"
    status.text = "🔄 Parsing log file with Drain3... This may take a moment."
    await page.update()
    
    # Run parser
    try:
        base_name, _ = os.path.splitext(file_path)
        output_excel = f"{base_name}_analysis.xlsx"
        
        rows = []
        with open(file_path, 'r') as f:
            for line in f:
                raw_line = line.strip()
                if not raw_line:
                    continue
                
                content = preprocess_log(raw_line)
                result = template_miner.add_log_message(content)
                
                template = result['template_mined']
                cluster_id = result['cluster_id']
                
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
            
            status.classes = "mt-4 p-4 rounded-lg bg-green-100 text-green-700"
            status.inner_html = f"""
                ✅ <strong>Parsing Complete!</strong><br>
                • Total Lines: {len(df_logs)}<br>
                • Unique Templates: {len(df_summary)}<br>
                • Output: <code>{output_excel}</code>
            """
        else:
            status.classes = "mt-4 p-4 rounded-lg bg-yellow-100 text-yellow-700"
            status.text = "⚠️ No logs found in the file."
            
    except FileNotFoundError:
        status.classes = "mt-4 p-4 rounded-lg bg-red-100 text-red-700"
        status.text = f"❌ Error: '{file_path}' not found."
    except Exception as e:
        status.classes = "mt-4 p-4 rounded-lg bg-red-100 text-red-700"
        status.text = f"❌ Error: {str(e)}"
    
    await page.update()


# ==========================================
# MAIN PAGE
# ==========================================
def log_analysis_page():
    wp = jp.WebPage()
    wp.title = "Linux Log Analysis Pipeline"
    
    # Main container
    container = jp.Div(a=wp, classes="min-h-screen bg-gray-100 py-8")
    inner = jp.Div(a=container, classes="max-w-2xl mx-auto px-4")
    
    # Header
    create_header(inner)
    
    # ==========================================
    # STEP 1: Clean Log File
    # ==========================================
    card1 = create_step_card(inner, 1, "Clean Log File",
                             "Remove noise from hardware, boot, peripheral, and housekeeping processes.")
    
    # File upload area
    upload_area, file_input, file_label = create_file_upload_area(card1, on_file_selected)
    
    # Manual path input
    path_input = create_manual_path_input(card1)
    wp.path_input = path_input
    
    # Clean button
    clean_btn = jp.Button(a=card1, text="🧹 Clean Log File",
                          style=button_primary, click=clean_log_clicked)
    
    # Blacklist accordion
    create_blacklist_accordion(card1)
    
    # Status area for Step 1
    status_area = jp.Div(a=card1, classes="mt-4 p-4 rounded-lg hidden", name="status")
    wp.status_area = status_area
    
    # ==========================================
    # STEP 2: Parse & Analyze
    # ==========================================
    card2 = create_step_card(inner, 2, "Parse & Analyze Logs",
                             "Extract log templates and parameters using Drain3 algorithm.")
    
    # Path input for Step 2
    path_input_2 = jp.Input(a=card2, type="text",
                            placeholder="Uses cleaned file, or enter custom path",
                            style=input_style, classes="mb-4")
    wp.path_input_2 = path_input_2
    
    # Parse button (initially slightly dimmed)
    parse_btn = jp.Button(a=card2, text="🔍 Parse & Export to Excel",
                          style=button_primary,
                          classes="opacity-70",
                          click=parse_log_clicked)
    wp.parse_btn = parse_btn
    
    # Status area for Step 2
    status_area_2 = jp.Div(a=card2, classes="mt-4 p-4 rounded-lg hidden")
    wp.status_area_2 = status_area_2
    
    # ==========================================
    # Footer
    # ==========================================
    footer = jp.Div(a=inner, classes="text-center text-gray-400 text-sm mt-8")
    footer.text = "Powered by Drain3 & JustPy"
    
    return wp


# ==========================================
# RUN SERVER
# ==========================================
if __name__ == "__main__":
    jp.justpy(log_analysis_page, port=8080)
