import justpy as jp
import os
import sys
import base64
import pandas as pd
import asyncio
import time

# 1. SETUP: Connect to 'code' folder
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'code'))

# Import your tools
from cleaner import clean_log_file, BASE_BLACKLIST, find_new_processes
from parser import parse_log_file 
#from meaning_generator import generate_meanings_for_file
from llama_meaning_generator import generate_meanings_for_file
from report_engine import step_1_merge_sentences, step_2_sort_logs, step_3_generate_report
from image_handler import get_b64_image, setup_lightbox
from markdown_handler import render_markdown_report, render_markdown_text
from ai_assistant import generate_summary, chat_with_log

# 2. STATE MANAGEMENT
class PipelineState:
    def __init__(self):
        self.cleaned_file_path = None
        self.uploaded_file = None
        self.meaning_file_path = None
        self.custom_blacklist = set()
        self.active_blacklist=[]
        self.chat_history = []

state = PipelineState()

# 3. HELPER: Collapsible List (Accordion)
def create_active_accordion(parent, title, items):
    """Creates a toggleable list to show default keywords."""
    wrapper = jp.Div(a=parent, classes="mt-2 mb-4 border rounded bg-white")
    
    # Header
    header = jp.Div(a=wrapper, classes="p-2 cursor-pointer bg-gray-50 hover:bg-gray-100 flex items-center justify-between")
    header_title = jp.Span(text=f"{title} ({len(items)})", a=header, classes="text-sm font-semibold text-gray-700")
    icon = jp.Span(text="▼", a=header, classes="text-xs text-gray-400")
    
    # Content (Hidden Grid)
    content = jp.Div(a=wrapper, classes="hidden p-3 bg-white grid grid-cols-4 gap-2 text-xs text-gray-600 border-t")
    wrapper.content_box = content
    wrapper.header_title = header_title
    wrapper.title = title
    
    def fill_items(item_list):
        content.delete_components()
        for item in item_list:
            jp.Span(text=item, a=content, classes="bg-gray-100 px-2 py-1 rounded text-center truncate")

    fill_items(items)
    
    def toggle(self, msg):
        if "hidden" in content.classes:
            content.classes = content.classes.replace("hidden", "grid")
            icon.text = "▲"
        else:
            content.classes = content.classes.replace("grid", "hidden")
            icon.text = "▼"
            
    header.on('click', toggle)
    # Store the fill function on the wrapper so we can call it later
    wrapper.refresh_list = fill_items 
    return wrapper

# 4. MAIN APPLICATION
def app():
    
    wp = jp.WebPage(title="Linux Log Summarizer", classes="bg-gray-100 min-h-screen")
    # Initialize the lightbox components
    lightbox, lightbox_img = setup_lightbox(wp)
    layout = jp.Div(a=wp, classes="max-w-4xl mx-auto p-8 font-sans text-slate-800")
    
    # --- CRITICAL FIX: State is now created NEW every time page loads ---
    wp.state = PipelineState()
    wp.state.active_blacklist = list(BASE_BLACKLIST)
    # Title
    header = jp.Div(a=layout, classes="text-center mb-10")
    jp.Div(text="Linux Log Summarizer", a=header, classes="text-4xl font-bold tracking-tight text-gray-800 uppercase border-b-4 border-blue-500 pb-2")

    # =========================================================
    # STEP 1: CLEANING & BLACKLIST
    # =========================================================
    card1 = jp.Div(a=layout, classes="bg-white p-6 rounded-xl shadow border border-gray-200 mb-8")
    
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
    upload_btn = jp.Button(text="⬆ Upload Selected File ", type='submit', a=upload_form, classes="w-full bg-white text-blue-600 font-bold py-2 px-4 rounded border border-blue-200 hover:bg-blue-50 hover:border-blue-400 shadow-sm transition-all cursor-pointer text-sm")
    # 5. Status Output
    upload_status = jp.Div(text="Please select a file and click Upload.", a=card1, classes="text-xs text-gray-500 mb-4 italic mt-2")
    
    # ---------------------------------------------------------
    # B. Blacklist Controls
    # ---------------------------------------------------------
    jp.Label(text="Blacklisted Processes:", a=card1, classes="block text-sm font-bold text-gray-700 mt-4 mb-1")
    # Pass the LOCAL list (wp.state.active_blacklist), not the global one
    blacklist_accordion = create_active_accordion(card1, "Current Blacklist", wp.state.active_blacklist)

    # --- NEW FEATURE: SCANNER ---
    jp.Label(text="Add To Blacklist:", a=card1, classes="block text-sm font-bold text-gray-700 mt-4 mb-1")
    scan_area = jp.Div(a=card1, classes="bg-blue-50 p-4 rounded-lg border border-blue-100 mb-4")
    btn_scan = jp.Button(text="🔍 Scan for New Processes", a=scan_area, 
                         classes="bg-white border border-blue-300 text-blue-700 text-xs font-bold py-1 px-3 rounded hover:bg-blue-50")
    suggestions_box = jp.Div(a=scan_area, classes="mt-3 text-xs font-mono text-slate-600 grid grid-cols-3 gap-2 hidden")
    
    btn_add_blacklist = jp.Button(text="+ Add To Blacklist", a=scan_area, classes="hidden mt-2 w-full bg-blue-600 text-white font-bold py-2 px-4 rounded text-xs hover:bg-blue-700 transition-all border border-blue-700")

    # D. Action Button
    btn_clean = jp.Button(text="CLEAN", a=card1, disabled=True, title="no file uploaded yet!", classes="w-full bg-gray-400 text-white font-sans font-bold italic py-3 px-6 rounded shadow transition-all cursor-not-allowed")
    
    # Status Output
    status1 = jp.Div(text="", a=card1, classes="mt-4 text-sm font-mono whitespace-pre-wrap")

    # =========================================================
    # STEP 2: PARSE (Placeholder for now)
    # =========================================================
    card2 = jp.Div(a=layout, classes="bg-gray-50 p-6 rounded-xl shadow border border-gray-200 opacity-50 pointer-events-none")
    jp.Div(text="Step 2: Parsing", a=card2, classes="text-xl font-bold italic mb-2 text-slate-800")
    jp.Div(text="Waiting for Step 1 completion...", a=card2, classes="text-sm text-gray-500 italic")
    # =========================================================
    # STEP 3: MEANING GENERATION (New Placeholder)
    # =========================================================
    card3 = jp.Div(a=layout, classes="bg-gray-50 p-6 rounded-xl shadow border border-gray-200 opacity-50 pointer-events-none mt-8")
    jp.Div(text="Step 3: Template Meaning Generation", a=card3, classes="text-xl font-bold italic mb-2 text-slate-800")
    jp.Div(text="Waiting for Step 2 completion...", a=card3, classes="text-sm text-gray-500 italic")

    # =========================================================
    # STEP 4: Analytics & Report (New)
    # =========================================================
    card4 = jp.Div(a=layout, classes="bg-gray-50 p-6 rounded-xl shadow border border-gray-200 opacity-50 pointer-events-none mt-8")
    jp.Div(text="Step 4: Analytics & Report", a=card4, classes="text-xl font-bold italic mb-2 text-slate-800")
    jp.Div(text="Waiting for Step 3 completion...", a=card4, classes="text-sm text-gray-500 italic")
   # =========================================================
    # STEP 5: AI Insights & Chat
    # =========================================================
    card5 = jp.Div(a=layout, classes="bg-gray-50 p-6 rounded-xl shadow border border-gray-200 opacity-50 pointer-events-none mt-8")
    
    # 1. Permanent Header
    c5_header = jp.Div(text="Step 5: AI Assistant & Insights", a=card5, classes="text-xl font-bold italic mb-2 text-slate-800")
    
    # 2. WAITING STATE (Visible Initially)
    c5_waiting = jp.Div(text="Waiting for Step 4 completion...", a=card5, classes="text-sm text-gray-500 italic mb-4")
    
    # 3. CONTENT STATE (Hidden Initially)
    # We put all controls inside this wrapper so we can show/hide them easily
    c5_content = jp.Div(a=card5, classes="hidden")
    
    # --- Controls inside Content ---
    jp.Div(text="Select Summary Style:", a=c5_content, classes="text-sm font-bold text-gray-700 mt-4 mb-1")
    
    # --- Style Toggle Buttons (Updated to Blue Scheme) ---
    style_box = jp.Div(a=c5_content, classes="flex gap-4 mb-4")
    
    # Active state matches the Blacklist selected items (Blue-100 background, Blue-500 border)
    btn_style_struct = jp.Div(text="Structured", a=style_box, 
                              classes="cursor-pointer px-4 py-2 rounded border border-blue-500 bg-blue-100 text-blue-700 font-bold text-sm shadow-sm transition-all")
    
    btn_style_narrative = jp.Div(text="Narrative", a=style_box, 
                                 classes="cursor-pointer px-4 py-2 rounded border border-gray-300 bg-white text-gray-600 text-sm shadow-sm transition-all hover:bg-gray-50")

    # --- Summarize Button (Updated to bg-blue-600) ---
    btn_ai_gen = jp.Button(text="SUMMARIZE", a=c5_content, 
                           classes="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded shadow transition-all cursor-pointer")
    
    ai_output_wrap = jp.Div(a=c5_content, classes="hidden mt-6 border-t pt-6")
    jp.Div(text="🤖 AI Analysis Result:", a=ai_output_wrap, classes="text-sm font-bold text-gray-700 mt-4 mb-1")
    # Changed to white background, slate text, and removed 'whitespace-pre-wrap'
    ai_result_box = jp.Div(a=ai_output_wrap, classes="bg-white text-slate-800 border border-gray-300 p-6 rounded-lg text-sm leading-relaxed shadow-inner max-h-96 overflow-y-auto")

    chat_wrap = jp.Div(a=c5_content, classes="hidden mt-8 border-t pt-6")
    jp.Div(text="💬 Chat with this Report:", a=chat_wrap, classes="text-sm font-bold text-gray-700 mt-4 mb-1")
    
    chat_window = jp.Div(a=chat_wrap, classes="bg-white border border-gray-300 h-64 rounded-lg p-4 mb-4 overflow-y-auto flex flex-col gap-3 shadow-inner")
    
    # --- [NEW INPUT BOX CODE] ---
    # 1. Container: Changed from jp.Div to jp.Form to handle Enter key correctly
    input_box = jp.Form(a=chat_wrap, classes="flex flex-row gap-2 mt-4 w-full")
    
    # 2. Input: (Same styles, just attached to the Form now)
    chat_input = jp.Input(a=input_box, placeholder="Ask a question about the logs...", type="text",
                          classes="flex-grow border border-gray-300 rounded px-4 py-2 text-sm focus:outline-none focus:border-indigo-500 shadow-sm bg-white")
    
    # 3. Button: Changed type to 'submit' so it triggers the form
    btn_send = jp.Button(text="SEND", a=input_box, type="submit",
                         classes="bg-blue-600 text-white font-bold px-6 py-2 rounded hover:bg-blue-700 transition-all shadow-sm cursor-pointer border border-blue-700")
    # ----------------------------
     
    # ---------------------------------------------------------
    # UI EVENT HANDLERS (For the Style Buttons)
    # ---------------------------------------------------------
    def set_style_structured(self, msg):
        msg.page.state.ai_style = "structured"
        # Structured = Active Blue | Narrative = Inactive Gray
        btn_style_struct.classes = "cursor-pointer px-4 py-2 rounded border border-blue-500 bg-blue-100 text-blue-700 font-bold text-sm shadow-sm transition-all"
        btn_style_narrative.classes = "cursor-pointer px-4 py-2 rounded border border-gray-300 bg-white text-gray-600 text-sm shadow-sm transition-all hover:bg-gray-50"
    
    def set_style_narrative(self, msg):
        msg.page.state.ai_style = "narrative"
        # Narrative = Active Blue | Structured = Inactive Gray
        btn_style_narrative.classes = "cursor-pointer px-4 py-2 rounded border border-blue-500 bg-blue-100 text-blue-700 font-bold text-sm shadow-sm transition-all"
        btn_style_struct.classes = "cursor-pointer px-4 py-2 rounded border border-gray-300 bg-white text-gray-600 text-sm shadow-sm transition-all hover:bg-gray-50"
        
    # Default the style
    wp.state.ai_style = "structured"
    btn_style_struct.on('click', set_style_structured)
    btn_style_narrative.on('click', set_style_narrative)

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
                    msg.page.state.uploaded_file = save_path
                    upload_status.inner_html = f"✅ <i>Saved: {fname} ({line_count} lines)</i>"
                    upload_status.classes = "text-xs text-green-600 mt-2 mb-4"
                    
                    # Enable Cleaner
                    btn_clean.disabled = False
                    btn_clean.title = "Click to start cleaning"
                    btn_clean.classes = "w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded shadow transition-all cursor-pointer"
                    
                    # Reset Step 2
                    card2.classes = "bg-gray-50 p-6 rounded-xl shadow border border-gray-200 opacity-50 pointer-events-none"
                    card2.delete_components()
                    jp.Div(text="Step 2: Parsing", a=card2, classes="text-xl font-bold italic mb-2 text-slate-800")
                    jp.Div(text="Waiting for Step 1 completion...", a=card2, classes="text-sm text-gray-500 italic")
                    # --- RESET STEP 3 ---
                    card3.classes = "bg-gray-50 p-6 rounded-xl shadow border border-gray-200 opacity-50 pointer-events-none mt-8"
                    card3.delete_components()
                    jp.Div(text="Step 3: Template Meaning Generation", a=card3, classes="text-xl font-bold italic mb-2 text-slate-800")
                    jp.Div(text="Waiting for Step 2 completion...", a=card3, classes="text-sm text-gray-500 italic")
                    
                    # --- [ADD THIS BLOCK] RESET STEP 4 ---
                    card4.classes = "bg-gray-50 p-6 rounded-xl shadow border border-gray-200 opacity-50 pointer-events-none mt-8"
                    card4.delete_components()
                    jp.Div(text="Step 4: Analytics & Report", a=card4, classes="text-xl font-bold italic mb-2 text-slate-800")
                    jp.Div(text="Waiting for Step 3 completion...", a=card4, classes="text-sm text-gray-500 italic")
                    
                    # --- [ADD THIS BLOCK] RESET STEP 5 ---
                    card5.classes = "bg-gray-50 p-6 rounded-xl shadow border border-gray-200 opacity-50 pointer-events-none mt-8"
                    c5_header.classes = "text-xl font-bold italic mb-2 text-slate-800" # Restore 'italic' style
                    c5_waiting.classes = "text-sm text-gray-500 italic mb-4" # Show waiting text
                    c5_content.classes = "hidden" # Hide content area
                    
                    # Clear internal AI state
                    ai_output_wrap.classes = "hidden mt-6 border-t pt-6"
                    chat_wrap.classes = "hidden mt-8 border-t pt-6"
                    chat_window.delete_components()
                    msg.page.state.chat_history = []
                    
                else:
                    print("[ERROR] Empty file content received.")
                    upload_status.text = "Error: Browser sent empty file."
        else:
            print("[WARNING] No file selected.")
            upload_status.text = "No file selected."
                               
    async def run_scan(self, msg):
        # 1. Check file
        if not msg.page.state.uploaded_file:
            suggestions_box.delete_components()
            suggestions_box.text = "Please upload a file first!"
            suggestions_box.classes = "italic text-red-600 text-xs mt-3 block"
            return

        # 2. Run Scan
        new_items = find_new_processes(msg.page.state.uploaded_file)
        
        # 3. Reset UI
        suggestions_box.delete_components()
        suggestions_box.inner_html = ""
        suggestions_box.text = ""
        msg.page.state.custom_blacklist.clear() # Clear old selections
        
        # Reset the "Add" button to original state
        btn_add_blacklist.text = "Add To Blacklist"
        btn_add_blacklist.classes = "hidden mt-3 w-full bg-blue-600 text-white font-bold py-2 px-4 rounded shadow-sm text-xs hover:bg-blue-700 transition-all border border-blue-700"
        btn_add_blacklist.disabled = False

        if new_items:
            # Show grid
            suggestions_box.classes = "mt-3 text-xs font-mono text-slate-600 grid grid-cols-3 gap-2 block"
            btn_add_blacklist.classes = btn_add_blacklist.classes.replace("hidden", "block") # Show button
            
            for item in new_items:
                # Create interactive div
                d = jp.Div(text=item, a=suggestions_box, 
                       classes="bg-white border border-gray-300 px-2 py-1 rounded cursor-pointer hover:bg-blue-50 text-center truncate transition-colors",
                       title="Click to select")
                d.on('click', toggle_blacklist_item) # <--- Connect the toggle event
        else:
            suggestions_box.text = "No new processes found."
            suggestions_box.classes = "text-blue-600 block mt-3"
            btn_add_blacklist.classes = btn_add_blacklist.classes.replace("block", "hidden")

    # Logic: Toggle item selection (White <-> Green)
    def toggle_blacklist_item(self, msg):
        process_name = self.text
        
        # Check if already selected
        if process_name in msg.page.state.custom_blacklist:
            # REMOVE IT
            msg.page.state.custom_blacklist.remove(process_name)
            self.classes = "bg-white border border-gray-300 px-2 py-1 rounded cursor-pointer hover:bg-blue-50 text-center truncate transition-colors"
        else:
            # ADD IT
            msg.page.state.custom_blacklist.add(process_name)
            self.classes = "bg-blue-100 border border-blue-500 text-blue-800 font-bold px-2 py-1 rounded cursor-pointer hover:bg-blue-200 text-center truncate transition-colors shadow-inner"

    # 2. ADD TO BLACKLIST (Updates Header Count + Security Logging)
    async def add_to_blacklist(self, msg):
        selected_items = msg.page.state.custom_blacklist
        if not selected_items: return

        print("\n--- BLACKLIST UPDATE INITIATED ---")

        count_added = 0
        for item in selected_items:
            if item not in msg.page.state.active_blacklist:
                msg.page.state.active_blacklist.append(item)
                count_added += 1
                # PRINT 1: Log specific item added
                print(f"[AUDIT] + Added process: '{item}'")
        
        # PRINT 2: Log the full updated list for verification
        print(f"[AUDIT] Total Count: {len(msg.page.state.active_blacklist)}")
        print(f"[AUDIT] Current Active Blacklist: {sorted(msg.page.state.active_blacklist)}")
        print("-------------------------------------------------\n")

        # REFRESH LIST & HEADER
        blacklist_accordion.refresh_list(msg.page.state.active_blacklist)
        blacklist_accordion.header_title.text = f"{blacklist_accordion.title} ({len(msg.page.state.active_blacklist)})"
        
        # Reset UI
        suggestions_box.delete_components()
        suggestions_box.inner_html = f"<i>{count_added} items added to blacklist!</i>"
        suggestions_box.classes = "text-green-600 font-bold text-xs mt-3 block p-2 bg-green-50 border border-green-200 rounded"
        
        btn_add_blacklist.classes = btn_add_blacklist.classes.replace("block", "hidden")
        msg.page.state.custom_blacklist.clear()
        
    async def run_cleaner(self, msg):
        # --- UI UPDATE: SPINNER ---
        self.disabled = True
        self.text = "" 
        self.inner_html = """
        <div class="flex items-center justify-center">
            <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            CLEANING...
        </div>
        """
        self.classes = "w-full bg-gray-400 text-white font-sans font-bold italic py-3 px-6 rounded shadow transition-all cursor-not-allowed"
        
        status1.text = "" # Clear old status
        await msg.page.update()
        await asyncio.sleep(0.1) # Allow UI render
        
        # Check page state
        if not msg.page.state.uploaded_file:
            # Revert UI if error
            self.inner_html = ""
            self.text = "CLEAN"
            self.disabled = False
            self.classes = "w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded shadow transition-all cursor-pointer"
            return

        file_path = msg.page.state.uploaded_file
        
        # Run the cleaner with the active blacklist
        out, trash, kept, removed = clean_log_file(
            file_path, 
            extra_blacklist=msg.page.state.active_blacklist
        ) 
        
        msg.page.state.cleaned_file_path = out
        
        # --- 1. NEW: PRINT TO TERMINAL ---
        print("\n--- [CLEANER REPORT] ---")
        print(f"Input File:    {os.path.basename(file_path)}")
        print(f"Kept Lines:    {kept}")
        print(f"Removed Lines: {removed}")
        print("------------------------")
        # Full path printed outside the separator
        print(f"File Saved to: {os.path.abspath(out)}\n")
        
        # --- 2. NEW: FORMATTED UI MESSAGE ---
        # We use <br> for newlines and a nested <div> for indentation
        status1.inner_html = f"""
        <div class="font-bold text-lg mb-2">✅ Cleaning Complete</div>
        <div class="ml-4">
            • <b>Input:</b> {os.path.basename(file_path)}<br>
            • <b>Kept:</b> {kept} lines <br>
            • <b>Removed:</b> {removed} lines
        </div>
        """
        status1.classes = "mt-4 text-sm font-mono text-green-800 bg-green-50 p-4 rounded border border-green-200 shadow-sm"
        # --- NEW: Output File (Blue Italic outside box) ---
        if not hasattr(card1, "output_label"):
            card1.output_label = jp.Div(
            a=card1,
            classes="text-xs text-blue-600 italic mt-2 mb-4"
            )
        card1.output_label.text = f"(Output File: {os.path.basename(out)})"
            
        # Unlock Step 2
        card2.classes = "bg-white p-6 rounded-xl shadow border border-gray-200 opacity-100 transition-all duration-500"
        card2.delete_components()
        jp.Div(text="Step 2: Parsing", a=card2, classes="text-xl font-bold mb-4 text-slate-800 border-b pb-2")
        jp.Div(text=f"Ready to parse file: {out}", a=card2, classes="text-green-600 font-medium mb-4")
        
        # --- ADD THIS: RESET STEP 3 (Re-lock it if we re-cleaned) ---
        card3.classes = "bg-gray-50 p-6 rounded-xl shadow border border-gray-200 opacity-50 pointer-events-none mt-8"
        card3.delete_components()
        jp.Div(text="Step 3: Template Meaning Generation", a=card3, classes="text-xl font-bold italic mb-2 text-slate-800")
        jp.Div(text="Waiting for Step 2 completion...", a=card3, classes="text-sm text-gray-500 italic")
        # --- RESET STEP 4 ---
        card4.classes = "bg-gray-50 p-6 rounded-xl shadow border border-gray-200 opacity-50 pointer-events-none mt-8"
        card4.delete_components()
        jp.Div(text="Step 4: Analytics & Report", a=card4, classes="text-xl font-bold italic mb-2 text-slate-800")
        jp.Div(text="Waiting for Step 3 completion...", a=card4, classes="text-sm text-gray-500 italic")
        # --- RESET STEP 5 ---
        card5.classes = "bg-gray-50 p-6 rounded-xl shadow border border-gray-200 opacity-50 pointer-events-none mt-8"
        c5_header.classes = "text-xl font-bold italic mb-2 text-slate-800" # Restore 'italic'
        c5_waiting.classes = "text-sm text-gray-500 italic mb-4"
        c5_content.classes = "hidden"
        
        # Clear internal AI state
        ai_output_wrap.classes = "hidden mt-6 border-t pt-6"
        chat_wrap.classes = "hidden mt-8 border-t pt-6"
        chat_window.delete_components()
        msg.page.state.chat_history = []
        
        # --- CONNECT THE PARSER BUTTON ---
        btn_parse = jp.Button(text="PARSE", a=card2, 
                              classes="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded shadow transition-all cursor-pointer")
        btn_parse.on('click', run_parser) # <--- THIS IS THE KEY LINK
        
        # --- RESTORE CLEAN BUTTON STATE ---
        self.inner_html = ""
        self.text = "CLEAN"
        self.disabled = False
        self.classes = "w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded shadow transition-all cursor-pointer"
        
    # Connect Events
    upload_form.on('submit', handle_upload)
    btn_scan.on('click', run_scan)
    btn_clean.on('click', run_cleaner)
    btn_add_blacklist.on('click', add_to_blacklist)
    
    # ------------------------------------------------------------------
    # 3. RUN PARSER LOGIC
    # ------------------------------------------------------------------
    async def run_parser(self, msg):
        # --- UI UPDATE: SPINNER ---
        self.disabled = True
        self.text = ""
        self.inner_html = """
        <div class="flex items-center justify-center">
            <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            PARSING...
        </div>
        """
        self.classes = "w-full bg-gray-400 text-white font-sans font-bold italic py-3 px-6 rounded shadow transition-all cursor-not-allowed"
        
        await msg.page.update()
        await asyncio.sleep(0.1) # Allow UI render
        
        # Get the cleaned file path from state
        cleaned_file = msg.page.state.cleaned_file_path
        if not cleaned_file or not os.path.exists(cleaned_file):
            print("[ERROR] Cleaned file not found.")
            return
        
        try:
            # 2. RUN THE PARSER
            excel_path, total_lines, clusters = parse_log_file(cleaned_file)
            # 3. SHOW RESULTS
            card2.delete_components()
            jp.Div(text="Step 2: Parsing", a=card2, classes="text-xl font-bold mb-4 text-slate-800 border-b pb-2")
            
            # --- NEW: Formatted Status Box (Matches Cleaner Style) ---
            parse_status = jp.Div(a=card2, classes="mt-4 text-sm font-mono text-green-800 bg-green-50 p-4 rounded border border-green-200 shadow-sm mb-2")
            parse_status.inner_html = f"""
            <div class="font-bold text-lg mb-2">✅ Parsing Complete</div>
            <div class="ml-4">
                • <b>Input:</b> {os.path.basename(cleaned_file)}<br>
                • <b>Unique templates:</b> {clusters}
            </div>
            """
            
            # ---Output File (Blue Italic outside box) ---
            jp.Div(text=f"(Output File: {os.path.basename(excel_path)})", a=card2, classes="text-xs text-blue-600 italic mb-4")
            # ========================================================
            # NEW: COLLAPSIBLE TEMPLATE SUMMARY (SHEET 2 DISPLAY)
            # ========================================================
            # 1. Read Sheet 2 from the Excel file we just created
            df = pd.read_excel(excel_path, sheet_name='Template Summary')
            # 2. Wrapper Container
            summary_wrap = jp.Div(a=card2, classes="border rounded shadow-sm bg-white mt-4 overflow-hidden")
            # 3. Header (Click to Toggle)
            summary_header = jp.Div(a=summary_wrap, classes="p-3 bg-gray-50 cursor-pointer flex justify-between items-center hover:bg-gray-100 transition select-none")
            jp.Span(text=f"📋 View Templates Found ({len(df)})", a=summary_header, classes="font-bold text-slate-700 text-sm")
            toggle_icon = jp.Span(text="▼", a=summary_header, classes="text-xs text-gray-500")
            # 4. Content (Hidden Table)
            # max-h-96 gives it a scrollbar if the list is huge
            summary_content = jp.Div(a=summary_wrap, classes="hidden overflow-y-auto max-h-96 border-t")
            # 5. Build the Table
            table = jp.Table(a=summary_content, classes="w-full text-left text-xs text-gray-600")
            
            # Table Header
            thead = jp.Thead(a=table, classes="bg-gray-100 text-gray-700 uppercase font-bold sticky top-0")
            tr_head = jp.Tr(a=thead)
            jp.Th(text="ID", a=tr_head, classes="px-4 py-2 w-16 bg-gray-100")
            jp.Th(text="Count", a=tr_head, classes="px-4 py-2 w-24 text-center bg-gray-100")
            jp.Th(text="Template Pattern", a=tr_head, classes="px-4 py-2 bg-gray-100")
            
            # Table Body
            tbody = jp.Tbody(a=table, classes="divide-y divide-gray-100")
            
            for index, row in df.iterrows():
                tr = jp.Tr(a=tbody, classes="hover:bg-blue-50 transition-colors")
                # ID Column
                jp.Td(text=row['Template ID'], a=tr, classes="px-4 py-2 font-mono text-blue-600 align-top")
                # Count Column
                jp.Td(text=row['Occurrences'], a=tr, classes="px-4 py-2 text-center font-bold text-slate-700 align-top")
                # Template Column (break-all ensures long regex doesn't break layout)
                jp.Td(text=row['Template Pattern'], a=tr, classes="px-4 py-2 font-mono break-all align-top")

            # 6. Toggle Logic
            def toggle_summary(self, msg):
                if "hidden" in summary_content.classes:
                    summary_content.classes = summary_content.classes.replace("hidden", "")
                    toggle_icon.text = "▲"
                else:
                    summary_content.classes = f"{summary_content.classes} hidden"
                    toggle_icon.text = "▼"
            
            summary_header.on('click', toggle_summary)
            # ========================================================
            # UNLOCK STEP 3
            # ========================================================
            card3.classes = "bg-white p-6 rounded-xl shadow border border-gray-200 opacity-100 transition-all duration-500 mt-8"
            card3.delete_components()
            jp.Div(text="Step 3: Template Meaning Generation", a=card3, classes="text-xl font-bold mb-4 text-slate-800 border-b pb-2")
            
            jp.Div(text=f"Ready to generate meanings for {len(df)} templates.", a=card3, classes="text-green-600 font-medium mb-4")
            
            # Placeholder Button for the next step
            btn_gen_meaning = jp.Button(text="GENERATE", a=card3, 
                                        classes="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded shadow transition-all cursor-pointer")
            
            # CONNECT THE NEW HANDLER
            btn_gen_meaning.on('click', run_meaning_generation)
            
        except Exception as e:
            print(f"[ERROR] Parsing failed: {e}")
            card2.delete_components()
            jp.Div(text=f"❌ Error: {str(e)}", a=card2, classes="text-red-600 font-bold")
    
    # ------------------------------------------------------------------
    # 4. NEW: MEANING GENERATION LOGIC WITH TIMER
    # ------------------------------------------------------------------
    async def run_meaning_generation(self, msg):
        # 1. IMMEDIATE UI UPDATE
        self.disabled = True
        self.text = "" 
        
        # Spinner inside the button
        self.inner_html = """
        <div class="flex items-center justify-center">
            <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            GENERATING...
        </div>
        """
        self.classes = "w-full bg-gray-400 text-white font-sans font-bold italic py-3 px-6 rounded shadow transition-all cursor-not-allowed"

        # --- LOCK CARDS ---
        card1_original = card1.classes
        card2_original = card2.classes
        card1.classes = f"{card1_original} opacity-50 pointer-events-none"
        if "opacity-100" in card2.classes:
            card2.classes = card2.classes.replace("opacity-100", "opacity-50 pointer-events-none")
        else:
            card2.classes += " opacity-50 pointer-events-none"

        # FORCE UI UPDATE: Ensure "Generating..." and the Label appear BEFORE we start work
        await msg.page.update()
        await asyncio.sleep(0.1)
        
        # --- START CLIENT-SIDE TIMER (JavaScript) ---
        # This runs in the browser, so it won't freeze when Python gets busy
        start_time_py = time.time()
        
        # Get paths
        cleaned_file = msg.page.state.cleaned_file_path
        base_name, _ = os.path.splitext(cleaned_file)
        parsed_excel_path = f"{base_name}_analysis.xlsx"
        
        if not os.path.exists(parsed_excel_path):
            print(f"[ERROR] Parsed file not found: {parsed_excel_path}")
            self.inner_html = ""
            self.text = "❌ Error: Input file missing"
            # Restore UI
            card1.classes = card1_original
            card2.classes = card2_original
            return

        try:
            # 2. RUN GENERATOR
            meaning_excel_path, count = await asyncio.to_thread(generate_meanings_for_file, parsed_excel_path)
            
            # --- STOP CLIENT TIMER ---
            # Calculate final static time for the report
            total_elapsed = int(time.time() - start_time_py)
            m, s = divmod(total_elapsed, 60)
            h, m = divmod(m, 60)
            if h > 0: total_duration = f"{h}h {m}m {s}s"
            elif m > 0: total_duration = f"{m}m {s}s"
            else: total_duration = f"{s}s"

            msg.page.state.meaning_file_path = meaning_excel_path
            
            # --- UNLOCK UI ---
            card1.classes = card1_original
            card2.classes = card2_original
            
            # 3. SUCCESS UPDATE
            card3.delete_components()
            jp.Div(text="Step 3: Template Meaning Generation", a=card3, classes="text-xl font-bold mb-4 text-slate-800 border-b pb-2")
            
            # Success Box (Now includes Time Taken)
            meaning_status = jp.Div(a=card3, classes="mt-4 text-sm font-mono text-green-800 bg-green-50 p-4 rounded border border-green-200 shadow-sm mb-2")
            meaning_status.inner_html = f"""
            <div class="font-bold text-lg mb-2">✅ Meanings Generated</div>
            <div class="ml-4">
                • <b>Time Taken:</b> {total_duration}<br>
                • <b>Templates Processed:</b> {count}<br>
                • <b>Model:</b> meta-llama/Llama-3.1-8B
            </div>
            """
            
            # Output File Name
            jp.Div(text=f"(Output File: {os.path.basename(meaning_excel_path)})", a=card3, classes="text-xs text-blue-600 italic mb-4")

            # 4. COLLAPSIBLE TABLE
            df = pd.read_excel(meaning_excel_path, sheet_name='Template Summary')
            df = df.sort_values(by="Template ID")
            
            summary_wrap = jp.Div(a=card3, classes="border rounded shadow-sm bg-white mt-4 overflow-hidden")
            
            summary_header = jp.Div(a=summary_wrap, classes="p-3 bg-gray-50 cursor-pointer flex justify-between items-center hover:bg-gray-100 transition select-none")
            jp.Span(text=f"🧠 View AI Interpretations ({len(df)})", a=summary_header, classes="font-bold text-slate-700 text-sm")
            toggle_icon = jp.Span(text="▼", a=summary_header, classes="text-xs text-gray-500")
            
            summary_content = jp.Div(a=summary_wrap, classes="hidden overflow-y-auto max-h-96 border-t")
            
            table = jp.Table(a=summary_content, classes="w-full text-left text-xs text-gray-600")
            thead = jp.Thead(a=table, classes="bg-gray-100 text-gray-700 uppercase font-bold sticky top-0")
            tr_head = jp.Tr(a=thead)
            jp.Th(text="ID", a=tr_head, classes="px-4 py-2 w-16 bg-gray-100")
            jp.Th(text="Template Pattern", a=tr_head, classes="px-4 py-2 w-1/3 bg-gray-100")
            jp.Th(text="AI Meaning", a=tr_head, classes="px-4 py-2 bg-gray-100")
            
            tbody = jp.Tbody(a=table, classes="divide-y divide-gray-100")
            
            for index, row in df.iterrows():
                tr = jp.Tr(a=tbody, classes="hover:bg-blue-50 transition-colors")
                jp.Td(text=row['Template ID'], a=tr, classes="px-4 py-2 font-mono text-blue-600 align-top")
                jp.Td(text=row['Template Pattern'], a=tr, classes="px-4 py-2 font-mono break-all align-top text-gray-500")
                jp.Td(text=row['Event Meaning'], a=tr, classes="px-4 py-2 font-medium text-slate-800 align-top")

            def toggle_meaning_summary(self, msg):
                if "hidden" in summary_content.classes:
                    summary_content.classes = summary_content.classes.replace("hidden", "")
                    toggle_icon.text = "▲"
                else:
                    summary_content.classes = f"{summary_content.classes} hidden"
                    toggle_icon.text = "▼"
            
            summary_header.on('click', toggle_meaning_summary)
            
            # ========================================================
            # UNLOCK STEP 4
            # ========================================================
            card4.classes = "bg-white p-6 rounded-xl shadow border border-gray-200 opacity-100 transition-all duration-500 mt-8"
            card4.delete_components()
            jp.Div(text="Step 4: Analytics & Report", a=card4, classes="text-xl font-bold mb-4 text-slate-800 border-b pb-2")
            
            jp.Div(text="Ready to compile the final executive report.", a=card4, classes="text-green-600 font-medium mb-4")
            
            # Create the Report Button
            btn_report = jp.Button(text="CREATE REPORT", a=card4, 
                                    classes="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded shadow transition-all cursor-pointer")
            
            # Connect the handler
            btn_report.on('click', run_report_generation)

        except Exception as e:
            print(f"[ERROR] Meaning Generation failed: {e}")
            
            card1.classes = card1_original
            card2.classes = card2_original
            
            
            self.inner_html = "" 
            self.text = "RETRY GENERATION"
            self.disabled = False
            self.classes = "w-full bg-red-600 hover:bg-red-700 text-white font-bold py-3 px-6 rounded shadow transition-all cursor-pointer"    
            jp.Div(text=f"❌ Error: {str(e)}", a=card3, classes="text-red-600 font-bold mt-2")  
            
    # ------------------------------------------------------------------
    # 5. STEP 4: ANALYTICS & REPORT GENERATION LOGIC
    # ------------------------------------------------------------------
    async def run_report_generation(self, msg):
        print("------ [LOG REPORT] ------")
        
        # --- UI UPDATE: SPINNER ---
        self.disabled = True
        self.text = "" 
        self.inner_html = """
        <div class="flex items-center justify-center">
            <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            CREATING...
        </div>
        """
        self.classes = "w-full bg-gray-400 text-white font-sans font-bold italic py-3 px-6 rounded shadow transition-all cursor-not-allowed"
        # --- [INSERT THIS BLOCK] ---
        # 1. Save original states (in case of error)
        card1_original = card1.classes
        card2_original = card2.classes
        card3_original = card3.classes

        # 2. Lock Card 1
        card1.classes = f"{card1_original} opacity-50 pointer-events-none"

        # 3. Lock Card 2 (Handle existing opacity)
        if "opacity-100" in card2.classes:
            card2.classes = card2.classes.replace("opacity-100", "opacity-50 pointer-events-none")
        else:
            card2.classes += " opacity-50 pointer-events-none"

        # 4. Lock Card 3 (Handle existing opacity)
        if "opacity-100" in card3.classes:
            card3.classes = card3.classes.replace("opacity-100", "opacity-50 pointer-events-none")
        else:
            card3.classes += " opacity-50 pointer-events-none"
        # --- [END INSERT] ---
        await msg.page.update()
        
        try:
            # Get input file (The output from Step 3)
            input_file = msg.page.state.meaning_file_path
            
            if not input_file or not os.path.exists(input_file):
                raise FileNotFoundError("Step 3 output file missing.")

            # --- 1. MERGE ---
            file_merged = await asyncio.to_thread(step_1_merge_sentences, input_file)
            
            # --- 2. SORT ---
            file_sorted = await asyncio.to_thread(step_2_sort_logs, file_merged)
            
            # --- 3. REPORT ---
            report_path = await asyncio.to_thread(step_3_generate_report, file_sorted)
            
            # Terminal footer (requested format)
            print("---------------------------------------------------------------------------")
            print(f"File Saved To: {os.path.abspath(file_sorted)}")
            
            # --- [INSERT THIS BLOCK TO UNLOCK CARDS ON SUCCESS] ---
            card1.classes = card1_original
            card2.classes = card2_original
            card3.classes = card3_original
            # Reveal and Enable Step 5
            card5.classes = "bg-white p-6 rounded-xl shadow border border-gray-200 opacity-100 mt-8 transition-all duration-500"
            c5_header.classes = "text-xl font-bold mb-4 text-slate-800 border-b pb-2" # Removed 'italic'
            # TOGGLE: Hide Waiting, Show Content
            c5_waiting.classes = "hidden"
            c5_content.classes = "block"
            
            # --- SUCCESS: WIPE CARD & SHOW RESULTS ---
            card4.delete_components()
            
            # Re-add Header
            jp.Div(text="Step 4: Analytics & Report", a=card4, classes="text-xl font-bold mb-4 text-slate-800 border-b pb-2")
            
            # Display Verification Results (No Button)
            result_box = jp.Div(a=card4, classes="mt-4 bg-green-50 border border-green-200 p-6 rounded-lg text-sm text-green-900 font-mono shadow-sm")
            result_box.inner_html = f"""
            <div class="text-green-800 font-bold text-lg mb-2">✅ Log Analytics & Report Created</div>
            <div class="ml-2 text-green-700">
                Merged parameters to event meanings and then sorted the logs.<br>
                Full detailed report with charts have been generated.
            </div>
            <div class="mt-4 text-green-900 ml-2">
                <b>📄 Full Detailed Report:</b> {os.path.basename(report_path)}
            </div>
            """
            # --- [NEW CODE: EXTERNAL BLUE LABEL] ---
            jp.Div(
                text=f"(Files and charts have been saved to the 'Logs' folder.)",
                a=card4,
                classes="text-xs text-blue-600 italic mt-3"
            )
            base_dir = os.path.dirname(os.path.abspath(__file__))
            logs_dir = os.path.join(base_dir, "Logs")
            
            expected_charts = [
                "1_log_volume.png", 
                "2_top_services.png", 
                "3_top_templates.png", 
                "4_top_users.png", 
                "5_top_ips.png"
            ]

            # ========================================================
            # NEW: COLLAPSIBLE VISUAL ANALYTICS (Matches Previous Style)
            # ========================================================
            
            # 1. Main Container (Matches Step 2/3 wrappers)
            analytics_wrap = jp.Div(a=card4, classes="border rounded shadow-sm bg-white mt-4 overflow-hidden")
            
            # 2. Header (Clickable - Matches previous headers exactly)
            analytics_header = jp.Div(a=analytics_wrap, classes="p-3 bg-gray-50 cursor-pointer flex justify-between items-center hover:bg-gray-100 transition select-none")
            
            # Title Text (Matches "text-sm" from previous cards)
            jp.Span(text="📊 View Analytics", a=analytics_header, classes="font-bold text-slate-700 text-sm")
            toggle_icon_charts = jp.Span(text="▼", a=analytics_header, classes="text-xs text-gray-500")
            
            # 3. Content Area (Hidden by default)
            # Added "border-t" to separate header from content, just like the tables
            analytics_content = jp.Div(a=analytics_wrap, classes="hidden p-4 bg-gray-50 grid grid-cols-1 gap-4 border-t")
            
            # 4. Loop & Display Images
            charts_found = 0
            for chart_name in expected_charts:
                chart_path = os.path.join(logs_dir, chart_name)
                
                # Get Base64
                img_src = get_b64_image(chart_path)
                
                if img_src:
                    charts_found += 1
                    # Image Container
                    img_card = jp.Div(a=analytics_content, classes="bg-white p-3 rounded shadow-sm border border-gray-200")
                    
                    # Title for the Chart
                    clean_name = chart_name.split('.')[0].replace('_', ' ').title()[2:] 
                    jp.Div(text=clean_name, a=img_card, classes="text-xs font-bold text-slate-700 mb-2 border-b pb-1")

                    # --- [UPDATED IMAGE LOGIC] ---
                    # We create the image directly (no <a> link wrapper needed)
                    img = jp.Img(src=img_src, a=img_card, 
                                 classes="w-full h-auto rounded hover:opacity-95 transition-opacity cursor-zoom-in",
                                 title="Click to expand")
                    
                    # Define the Click Handler for THIS specific image
                    def open_in_lightbox(self, msg):
                        # 1. Update the lightbox image source to match this chart
                        lightbox_img.src = self.src
                        # 2. Show the lightbox (Change 'hidden' to 'flex' with animation)
                        lightbox.classes = "fixed inset-0 z-50 bg-black bg-opacity-90 flex items-center justify-center p-4 cursor-zoom-out transition-opacity duration-300"
                    
                    # Attach the handler
                    img.on('click', open_in_lightbox)
                    # --- [END UPDATE] ---

            # 5. Handle "No Charts Found"
            if charts_found == 0:
                jp.Div(text="(No charts generated)", a=analytics_content, classes="text-xs text-gray-400 italic")

            # 6. Toggle Function
            def toggle_analytics(self, msg):
                if "hidden" in analytics_content.classes:
                    analytics_content.classes = analytics_content.classes.replace("hidden", "")
                    toggle_icon_charts.text = "▲"
                else:
                    analytics_content.classes = f"{analytics_content.classes} hidden"
                    toggle_icon_charts.text = "▼"
            
            analytics_header.on('click', toggle_analytics)
            
            # ========================================================
            # NEW: COLLAPSIBLE FULL REPORT (With Print/PDF Action)
            # ========================================================
            
            # 1. Main Container
            report_wrap = jp.Div(a=card4, classes="border rounded shadow-sm bg-white mt-4 overflow-hidden")
            
            # 2. Header (Refactored for Layout)
            # We use a Flex container to separate the "Toggle Trigger" from the "Print Button"
            report_header = jp.Div(a=report_wrap, classes="p-3 bg-gray-50 flex justify-between items-center border-b border-gray-200")

            # LEFT SIDE: The Clickable Toggle Area
            header_left = jp.Div(a=report_header, classes="flex items-center gap-2 cursor-pointer hover:opacity-80 transition select-none")
            toggle_icon_report = jp.Span(text="▼", a=header_left, classes="text-xs text-gray-500")
            jp.Span(text="📄 View Detailed Log Report", a=header_left, classes="font-bold text-slate-700 text-sm")

            # RIGHT SIDE: The Action Button
            header_right = jp.Div(a=report_header, classes="flex items-center")
            
            # [NEW] Print/PDF Button
            btn_print = jp.Button(text="🖨️ Print / Save PDF", a=header_right, 
                                  classes="bg-white border border-gray-300 text-gray-600 text-xs font-bold px-3 py-1 rounded hover:bg-blue-50 hover:text-blue-600 hover:border-blue-300 shadow-sm transition-colors")

            # 3. Content Area
            report_content = jp.Div(a=report_wrap, classes="hidden p-8 bg-white text-sm text-slate-800 overflow-auto max-h-screen leading-relaxed")
            
            # 4. Render Markdown
            html_report_content = render_markdown_report(report_path)
            report_content.inner_html = html_report_content

            # 5. Toggle Logic (Attached ONLY to the Left Side)
            def toggle_report(self, msg):
                if "hidden" in report_content.classes:
                    report_content.classes = report_content.classes.replace("hidden", "")
                    toggle_icon_report.text = "▲"
                else:
                    report_content.classes = f"{report_content.classes} hidden"
                    toggle_icon_report.text = "▼"
            
            header_left.on('click', toggle_report)
            
            # 6. [NEW] Print / Download PDF Logic (COMPACT VERSION)
            async def print_report_pdf(self, msg):
                """
                Opens the report in a new window with COMPACT styling to save paper/PDF pages.
                """
                # Escape backticks/quotes for JS safety
                safe_html = html_report_content.replace('`', '\\`').replace('${', '\\${')
                
                script_code = f"""
                var printWin = window.open('', '_blank');
                printWin.document.write(`
                    <html>
                        <head>
                            <title>Log Analysis Report</title>
                            <style>
                                /* --- COMPACT PRINT STYLES --- */
                                @media print {{
                                    @page {{ margin: 15mm; size: auto; }} /* Set reasonable print margins */
                                }}
                                body {{ 
                                    font-family: ui-sans-serif, system-ui, -apple-system, sans-serif; 
                                    padding: 20px; 
                                    color: #1e293b; 
                                    line-height: 1.3; /* Tighter lines */
                                    font-size: 11px;  /* Smaller base font */
                                }}
                                h1 {{ 
                                    font-size: 18px; 
                                    border-bottom: 2px solid #e2e8f0; 
                                    padding-bottom: 5px; 
                                    margin-bottom: 10px; 
                                }}
                                h2 {{ 
                                    font-size: 14px; 
                                    margin-top: 15px; 
                                    margin-bottom: 5px; 
                                    color: #0f172a; 
                                    border-left: 3px solid #3b82f6; 
                                    padding-left: 8px; 
                                    page-break-after: avoid; /* Keep header with content */
                                }}
                                h3 {{ 
                                    font-size: 12px; 
                                    margin-top: 10px; 
                                    margin-bottom: 2px;
                                    color: #334155; 
                                    font-weight: bold; 
                                    page-break-after: avoid;
                                }}
                                /* COMPACT TABLES */
                                table {{ 
                                    width: 100%; 
                                    border-collapse: collapse; 
                                    margin-top: 8px; 
                                    margin-bottom: 8px; 
                                    font-size: 10px; /* Very compact table text */
                                }}
                                th, td {{ 
                                    border: 1px solid #cbd5e1; 
                                    padding: 4px 6px; /* Reduced cell padding */
                                    text-align: left; 
                                }}
                                th {{ 
                                    background-color: #f1f5f9; 
                                    font-weight: bold; 
                                    -webkit-print-color-adjust: exact; /* Force background color print */
                                    print-color-adjust: exact;
                                }}
                                tr:nth-child(even) {{ 
                                    background-color: #f8fafc; 
                                    -webkit-print-color-adjust: exact;
                                    print-color-adjust: exact;
                                }}
                                code {{ 
                                    background-color: #f1f5f9; 
                                    padding: 1px 3px; 
                                    border-radius: 3px; 
                                    font-family: monospace; 
                                    font-size: 0.95em; 
                                    border: 1px solid #e2e8f0;
                                }}
                                blockquote {{ 
                                    border-left: 3px solid #cbd5e1; 
                                    padding-left: 10px; 
                                    color: #64748b; 
                                    font-style: italic; 
                                    margin: 8px 0; 
                                }}
                                .no-print {{ display: none; }}
                            </style>
                        </head>
                        <body>
                            {safe_html}
                            <script>
                                window.onload = function() {{ 
                                    window.print(); 
                                }};
                            </script>
                        </body>
                    </html>
                `);
                printWin.document.close();
                """
                await msg.page.run_javascript(script_code)

            btn_print.on('click', print_report_pdf)
            
                        
        except Exception as e:
            print(f"[ERROR] Report failed: {e}")
            # --- [INSERT THIS BLOCK] ---
            # Restore cards if error occurs
            card1.classes = card1_original
            card2.classes = card2_original
            card3.classes = card3_original
            self.inner_html = "" 
            self.text = "FAILED"
            self.classes = "w-full bg-red-600 text-white font-bold py-3 px-6 rounded shadow cursor-pointer"
            self.disabled = False
            jp.Div(text=f"Error: {str(e)}", a=card4, classes="text-red-600 font-bold mt-2")
    
    # ------------------------------------------------------------------
    # 6. STEP 5: AI LOGIC HANDLERS
    # ------------------------------------------------------------------
    
    async def run_ai_summary(self, msg):
        """Generates the initial summary based on selected style."""
        
        # --- 1. UI Loading State (Spinner + Italics) ---
        btn_ai_gen.disabled = True
        btn_ai_gen.text = "" # Clear text to make room for HTML
        btn_ai_gen.inner_html = """
        <div class="flex items-center justify-center">
            <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span class="italic">SUMMARIZING...</span>
        </div>
        """
        btn_ai_gen.classes = "w-full bg-gray-400 text-white font-bold py-3 px-6 rounded shadow cursor-not-allowed"
        
        # --- [NEW] LOCK PREVIOUS STEPS ---
        # Save original classes to restore later
        card1_original = card1.classes
        card2_original = card2.classes
        card3_original = card3.classes
        card4_original = card4.classes

        # Apply Disabled Styles (Opacity 50% + No Pointer Events)
        card1.classes = f"{card1_original} opacity-50 pointer-events-none"
        
        # Helper to handle cards that might already be Opacity-100
        def lock_card(c):
            if "opacity-100" in c.classes:
                return c.classes.replace("opacity-100", "opacity-50 pointer-events-none")
            else:
                return c.classes + " opacity-50 pointer-events-none"

        card2.classes = lock_card(card2)
        card3.classes = lock_card(card3)
        card4.classes = lock_card(card4)
        # ---------------------------------

        await msg.page.update()
        
        # 2. Get Data
        base_dir = os.path.dirname(os.path.abspath(__file__))
        report_path = os.path.join(base_dir, "Logs", "Log_Analysis_Report.md")
        
        selected_style = getattr(msg.page.state, 'ai_style', 'structured')
        
        # 3. Call AI (Async)
        summary_text = await asyncio.to_thread(generate_summary, report_path, selected_style)
        
        # 4. Update UI with Result
        ai_output_wrap.classes = "mt-6 border-t pt-6 block" # Unhide container
        ai_result_box.inner_html = render_markdown_text(summary_text)
        
        # 5. Unlock Chat Interface
        chat_wrap.classes = "mt-8 border-t pt-6 block" # Unhide chat
        
        # 6. Reset Button (Restore Blue Color)
        btn_ai_gen.inner_html = "" 
        btn_ai_gen.text = "SUMMARIZE"
        btn_ai_gen.disabled = False
        btn_ai_gen.classes = "w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded shadow transition-all cursor-pointer"
        
        # --- [NEW] RESTORE PREVIOUS STEPS ---
        card1.classes = card1_original
        card2.classes = card2_original
        card3.classes = card3_original
        card4.classes = card4_original
        # ------------------------------------
        
    async def handle_chat_message(self, msg):
        """Handles sending user questions to the AI."""
        user_text = chat_input.value
        if not user_text.strip(): return
        
        # 1. Clear Input & Update History
        chat_input.value = ""
        msg.page.state.chat_history.append({'role': 'user', 'content': user_text})
        
        # 2. Render User Bubble Immediately
        jp.Div(text=user_text, a=chat_window, 
               classes="bg-blue-100 text-blue-800 p-3 rounded-lg self-end max-w-xs text-sm shadow-sm")
        
        # Loading Bubble
        loading_bubble = jp.Div(text="Thinking...", a=chat_window, 
                                classes="bg-gray-100 text-gray-500 p-3 rounded-lg self-start text-xs italic")
        await msg.page.update()
        
        # 3. Call AI (Async)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        report_path = os.path.join(base_dir, "Logs", "Log_Analysis_Report.md")
        
        ai_response = await asyncio.to_thread(chat_with_log, report_path, msg.page.state.chat_history, user_text)
        
        # 4. Remove Loading & Render AI Bubble
        chat_window.remove_component(loading_bubble)
        msg.page.state.chat_history.append({'role': 'assistant', 'content': ai_response})
        
        # --- [UPDATED] RENDER MARKDOWN BUBBLE ---
        # 1. Convert raw text to HTML (Bold, Code blocks, Tables)
        formatted_html = render_markdown_text(ai_response)
        
        # 2. Render Bubble
        # - max-w-3xl: Wider width to fit tables/logs without cramping
        # - Removed 'overflow' classes: Forces the bubble to expand fully instead of scrolling
        jp.Div(inner_html=formatted_html, a=chat_window, 
               classes="bg-gray-50 text-slate-800 p-4 rounded-lg self-start max-w-3xl text-sm shadow-sm border border-gray-200")
        
        # 5. Auto-scroll to bottom (Robust Timeout Version)
        # We wait 100ms for the large bubble to render, then scroll the window
        await msg.page.run_javascript(f"""
            setTimeout(function() {{
                var chat = document.getElementById('{chat_window.id}');
                chat.scrollTop = chat.scrollHeight; 
            }}, 100);
        """)

    # Connect Events
    btn_ai_gen.on('click', run_ai_summary)
    # Form submit handles both Button Click and Enter Key
    # (And ignores clicks outside the box!)
    input_box.on('submit', handle_chat_message)             
    return wp
jp.justpy(app, port=8000)