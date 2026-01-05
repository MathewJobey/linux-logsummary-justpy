import justpy as jp
import os
import sys
import base64

# 1. SETUP: Connect to 'code' folder
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'code'))

# Import your tools
from cleaner import clean_log_file, BASE_BLACKLIST, find_new_processes
# We will import parser later when we get to Step 2, but for now we just need the placeholder
# from parser import parse_log_file 

# 2. STATE MANAGEMENT
class PipelineState:
    def __init__(self):
        self.cleaned_file_path = None

state = PipelineState()

# 3. HELPER: Collapsible List (Accordion)
def create_accordion(parent, title, items):
    """Creates a toggleable list to show default keywords."""
    wrapper = jp.Div(a=parent, classes="mt-2 mb-4 border rounded bg-white")
    
    # Header
    header = jp.Div(a=wrapper, classes="p-2 cursor-pointer bg-gray-50 hover:bg-gray-100 flex items-center justify-between")
    jp.Span(text=title, a=header, classes="text-sm font-semibold text-gray-700")
    icon = jp.Span(text="▼", a=header, classes="text-xs text-gray-400")
    
    # Content (Hidden Grid)
    content = jp.Div(a=wrapper, classes="hidden p-3 bg-white grid grid-cols-4 gap-2 text-xs text-gray-600 border-t")
    
    for item in items:
        jp.Span(text=item, a=content, classes="bg-gray-100 px-2 py-1 rounded text-center truncate")

    def toggle(self, msg):
        if "hidden" in content.classes:
            content.classes = content.classes.replace("hidden", "grid")
            icon.text = "▲"
        else:
            content.classes = content.classes.replace("grid", "hidden")
            icon.text = "▼"
            
    header.on('click', toggle)
    return wrapper

# 4. MAIN APPLICATION
def app():
    wp = jp.WebPage(title="Linux Log Summarizer", classes="bg-gray-100 min-h-screen")
    layout = jp.Div(a=wp, classes="max-w-4xl mx-auto p-8 font-sans text-slate-800")
    
    # Title
    header = jp.Div(a=layout, classes="text-center mb-10")
    jp.Div(text="Linux Log Summarizer", a=header, classes="text-4xl font-bold tracking-tight text-gray-800 uppercase border-b-4 border-blue-500 pb-2")

    # =========================================================
    # STEP 1: CLEANING & BLACKLIST
    # =========================================================
    card1 = jp.Div(a=layout, classes="bg-white p-6 rounded-xl shadow-lg border border-gray-200 mb-8")
    
    # Header
    jp.Div(text="Step 1: Clean & Filter", a=card1, classes="text-xl font-bold mb-4 text-slate-800 border-b pb-2")

    # ---------------------------------------------------------
    # A. File Upload Section
    # ---------------------------------------------------------
    jp.Label(text="Select Log File:", a=card1, classes="block text-sm font-bold text-gray-700 mb-1")
    
    # 1. CREATE A FORM (Required for file transfer)
    upload_form = jp.Form(a=card1, classes="mb-6", enctype='multipart/form-data')
    # 2. Container inside the form
    upload_box = jp.Div(a=upload_form, classes="border-2 border-dashed border-gray-300 rounded-lg p-6 flex flex-col items-center justify-center bg-gray-50 hover:bg-gray-100 transition-colors mb-2")
    # 3. The File Input Component
    file_input = jp.Input(a=upload_box, type='file', name='target_file', classes="block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100")
    # 4. Submit Button
    upload_btn = jp.Button(text="⬆ Upload Selected File ", type='submit', a=upload_form,
                           classes="w-full bg-white text-blue-600 font-bold py-2 px-4 rounded border border-blue-200 hover:bg-blue-50 hover:border-blue-400 shadow-sm transition-all cursor-pointer text-sm")
    upload_status = jp.Div(text="Please select a file and click Upload.", a=card1, classes="text-xs text-gray-500 mb-4 italic mt-2")
    
    
    # ---------------------------------------------------------
    # B. Blacklist Controls
    # ---------------------------------------------------------
    jp.Label(text="Blacklisted Processes:", a=card1, classes="block text-sm font-bold text-gray-700 mt-4 mb-1")
    create_accordion(card1, f"Default ({len(BASE_BLACKLIST)})", BASE_BLACKLIST)

    # --- NEW FEATURE: SCANNER ---
    scan_area = jp.Div(a=card1, classes="bg-blue-50 p-4 rounded-lg border border-blue-100 mb-4")
    jp.Div(text="Not sure what to block? Scan the file for suggestions.", a=scan_area, classes="text-xs text-blue-800 mb-2")
    btn_scan = jp.Button(text="🔍 Scan for New Processes", a=scan_area, 
                         classes="bg-white border border-blue-300 text-blue-700 text-xs font-bold py-1 px-3 rounded hover:bg-blue-50")
    suggestions_box = jp.Div(a=scan_area, classes="mt-3 text-xs font-mono text-slate-600 grid grid-cols-3 gap-2 hidden")

    # D. Action Button
    btn_clean = jp.Button(text="Run Cleaner Tool", a=card1, 
                          classes="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded shadow transition-all")
    
    # Status Output
    status1 = jp.Div(text="", a=card1, classes="mt-4 text-sm font-mono whitespace-pre-wrap")

    # =========================================================
    # STEP 2: PARSE (Placeholder for now)
    # =========================================================
    card2 = jp.Div(a=layout, classes="bg-gray-50 p-6 rounded-xl shadow border border-gray-200 opacity-50 pointer-events-none")
    jp.Div(text="Step 2: Parse & Export", a=card2, classes="text-xl font-bold mb-2 text-slate-800")
    jp.Div(text="Waiting for Step 1 completion...", a=card2, classes="text-sm text-gray-500 italic")


    # =========================================================
    # LOGIC HANDLERS
    # =========================================================
    # 1. NEW: Handle File Upload
    async def handle_upload(self, msg):
        """Called when the FORM is submitted (contains file content)"""
        print("\n--- UPLOAD STARTED ---")
        
        # 1. Create Logs folder safely
        base_dir = os.path.dirname(os.path.abspath(__file__))
        logs_dir = os.path.join(base_dir, "Logs")
        if not os.path.exists(logs_dir):
            print(f"[INFO] Creating directory: {logs_dir}")
            os.makedirs(logs_dir)

        # 2. Find the file component in the form data
        file_component = None
        for c in msg.form_data:
            if c.type == 'file':
                file_component = c
                break
        
        # 3. Process the file
        if file_component and hasattr(file_component, 'files') and len(file_component.files) > 0:
            for i, v in enumerate(file_component.files):
                fname = v.name
                print(f"[INFO] Processing file: {fname}")
                
                if 'file_content' in v:
                    # DECODE BASE64 CONTENT
                    file_content = v.file_content
                    decoded_content = base64.b64decode(file_content)
                    
                    # COUNT LINES (Split by newlines to count)
                    line_count = len(decoded_content.splitlines())
                    
                    save_path = os.path.join(logs_dir, fname)
                    print(f"[INFO] Saving to: {save_path}")

                    with open(save_path, 'wb') as f:
                        f.write(decoded_content)
                    
                    print(f"[SUCCESS] Wrote {len(decoded_content)} bytes.")
                    print(f"[INFO] Total Log Lines: {line_count}")  # <--- NEW LINE HERE
                    print("----------------------\n")
                    
                    # SUCCESS UI UPDATES
                    state.uploaded_file = save_path
                    upload_status.text = f"✅ Saved: {fname} ({line_count} lines)"
                    upload_status.classes = "text-xs text-green-600 mb-4 font-bold"
                    
                    # Enable Cleaner
                    btn_clean.disabled = False
                    btn_clean.classes = "w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded shadow transition-all cursor-pointer"
                    
                    # Reset Step 2
                    card2.classes = "bg-gray-50 p-6 rounded-xl shadow border border-gray-200 opacity-50 pointer-events-none"
                    card2.delete_components()
                    jp.Div(text="Step 2: Parse & Export", a=card2, classes="text-xl font-bold mb-2 text-slate-800")
                    jp.Div(text="Waiting for Step 1 completion...", a=card2, classes="text-sm text-gray-500 italic")
                else:
                    print("[ERROR] Empty file content received.")
                    upload_status.text = "Error: Browser sent empty file."
        else:
            print("[WARNING] No file selected.")
            upload_status.text = "No file selected."
                               
    async def run_scan(self, msg):
        # Use the file we just uploaded
        if not hasattr(state, 'uploaded_file') or not state.uploaded_file:
            suggestions_box.text = "Please upload a file first."
            suggestions_box.classes = "text-red-500 block mt-2"
            return

        new_items = find_new_processes(state.uploaded_file)
        
        suggestions_box.delete_components()
        if new_items:
            suggestions_box.classes = "mt-3 text-xs font-mono text-slate-600 grid grid-cols-3 gap-2 block"
            for item in new_items:
                jp.Div(text=item, a=suggestions_box, 
                       classes="bg-white border px-2 py-1 rounded cursor-pointer hover:bg-blue-100 text-center truncate",
                       title=item)
        else:
            suggestions_box.text = "No new processes found."
            suggestions_box.classes = "text-green-600 block mt-2"

    async def run_cleaner(self, msg):
        status1.text = "Running..."
        status1.classes = "mt-4 text-sm font-mono text-blue-600"
        
        if not hasattr(state, 'uploaded_file') or not state.uploaded_file:
            return

        file_path = state.uploaded_file
        
        # --- FIX: Removed the line reading 'custom_input' ---
        # We just call the cleaner with the file path
        out, trash, kept, removed = clean_log_file(file_path) 
        
        state.cleaned_file_path = out
        
        status1.inner_html = f"""
        ✅ <b>Cleaning Complete</b>
        • Input: {os.path.basename(file_path)}
        • Kept: {kept} lines (Saved to: {out})
        • Removed: {removed} lines
        """
        status1.classes = "mt-4 text-sm font-mono text-green-700 bg-green-50 p-4 rounded border border-green-200"
        
        # Unlock Step 2
        card2.classes = "bg-white p-6 rounded-xl shadow border border-gray-200 opacity-100 transition-all duration-500"
        card2.delete_components()
        jp.Div(text="Step 2: Parse & Export", a=card2, classes="text-xl font-bold mb-4 text-slate-800 border-b pb-2")
        jp.Div(text=f"Ready to parse file: {out}", a=card2, classes="text-green-600 font-medium mb-4")
        jp.Button(text="Proceed to Drain Parsing", a=card2, classes="bg-green-600 text-white font-bold py-2 px-4 rounded")

    # Connect Events
    upload_form.on('submit', handle_upload)
    btn_scan.on('click', run_scan)
    btn_clean.on('click', run_cleaner)

    return wp

jp.justpy(app, port=8000)