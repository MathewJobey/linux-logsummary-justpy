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
from meaning_generator import generate_meanings_for_file

# 2. STATE MANAGEMENT
class PipelineState:
    def __init__(self):
        self.cleaned_file_path = None
        self.uploaded_file = None
        self.meaning_file_path = None
        self.custom_blacklist = set()
        self.active_blacklist=[]

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
                    # --- ADD THIS: RESET STEP 3 ---
                    card3.classes = "bg-gray-50 p-6 rounded-xl shadow border border-gray-200 opacity-50 pointer-events-none mt-8"
                    card3.delete_components()
                    jp.Div(text="Step 3: Template Meaning Generation", a=card3, classes="text-xl font-bold italic mb-2 text-slate-800")
                    jp.Div(text="Waiting for Step 2 completion...", a=card3, classes="text-sm text-gray-500 italic")
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
        status1.text = "Running..."
        status1.classes = "mt-4 text-sm font-mono text-blue-600"
        
        # Check page state
        if not msg.page.state.uploaded_file:
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
        
        # --- CONNECT THE PARSER BUTTON ---
        btn_parse = jp.Button(text="PARSE", a=card2, 
                              classes="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded shadow transition-all cursor-pointer")
        btn_parse.on('click', run_parser) # <--- THIS IS THE KEY LINK
        
    # Connect Events
    upload_form.on('submit', handle_upload)
    btn_scan.on('click', run_scan)
    btn_clean.on('click', run_cleaner)
    btn_add_blacklist.on('click', add_to_blacklist)
    
    # ------------------------------------------------------------------
    # 3. RUN PARSER LOGIC
    # ------------------------------------------------------------------
    async def run_parser(self, msg):
        # 1. Update UI to show "Processing"
        self.text = "⏳ Parsing..."
        self.disabled = True
        self.classes = "bg-gray-400 text-white font-bold py-2 px-4 rounded cursor-wait"
        
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
            
           # Updated style: Blue, Italic, Centered (matches your request)
            timer_label = jp.Div(text="", a=card3, classes="mt-2 text-center text-sm text-blue-600 italic font-bold hidden")
            btn_gen_meaning.timer_label = timer_label
            
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
        
        # --- SHOW LABEL ---
        if hasattr(self, 'timer_label'):
            self.timer_label.text = "Time Elapsed: 0s"
            # Unhide the label
            self.timer_label.classes = self.timer_label.classes.replace("hidden", "block")

        # --- LOCK CARDS ---
        card1_original = card1.classes
        card2_original = card2.classes
        card1.classes = f"{card1_original} opacity-50 pointer-events-none"
        if "opacity-100" in card2.classes:
            card2.classes = card2.classes.replace("opacity-100", "opacity-50 pointer-events-none")
        else:
            card2.classes += " opacity-50 pointer-events-none"
        
        await msg.page.update()
        
        # FORCE UI UPDATE: Ensure "Generating..." and the Label appear BEFORE we start work
        await msg.page.update()
        await asyncio.sleep(0.1)
        
        # --- START CLIENT-SIDE TIMER (JavaScript) ---
        # This runs in the browser, so it won't freeze when Python gets busy
        start_time_py = time.time()
        # We need the HTML ID of the label to update it via JS
        label_id = self.timer_label.id 
        current_time_ms = int(time.time() * 1000)
        # JS Code: Calculates elapsed time and updates the div text every second
        js_code = f"""
        if (window.genTimer) clearInterval(window.genTimer);
        var startTime = {current_time_ms};
        window.genTimer = setInterval(function() {{
            var now = new Date().getTime();
            var diff = Math.floor((now - startTime) / 1000);
            var m = Math.floor(diff / 60);
            var s = diff % 60;
            var h = Math.floor(m / 60);
            m = m % 60;
            var timeStr = s + "s";
            if (m > 0) timeStr = m + "m " + timeStr;
            if (h > 0) timeStr = h + "h " + timeStr;
            
            var el = document.getElementById('{label_id}');
            if (el) el.innerText = "Time Elapsed: " + timeStr;
        }}, 1000);
        """
        await msg.page.run_javascript(js_code)
        
        # Get paths
        cleaned_file = msg.page.state.cleaned_file_path
        base_name, _ = os.path.splitext(cleaned_file)
        parsed_excel_path = f"{base_name}_analysis.xlsx"
        
        if not os.path.exists(parsed_excel_path):
            await msg.page.run_javascript("clearInterval(window.genTimer);")
            print(f"[ERROR] Parsed file not found: {parsed_excel_path}")
            self.inner_html = ""
            self.text = "❌ Error: Input file missing"
            # Restore UI
            card1.classes = card1_original
            card2.classes = card2_original
            if hasattr(self, 'timer_label'): self.timer_label.classes = self.timer_label.classes.replace("block", "hidden")
            return

        try:
            # 2. RUN GENERATOR
            meaning_excel_path, count = await asyncio.to_thread(generate_meanings_for_file, parsed_excel_path)
            
            # --- STOP CLIENT TIMER ---
            await msg.page.run_javascript("clearInterval(window.genTimer);")
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
                • <b>Model:</b> Microsoft Phi-3 Mini
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

        except Exception as e:
            print(f"[ERROR] Meaning Generation failed: {e}")
            await msg.page.run_javascript("clearInterval(window.genTimer);")
            
            card1.classes = card1_original
            card2.classes = card2_original
            
            self.inner_html = "" 
            self.text = "RETRY GENERATION"
            self.disabled = False
            self.classes = "w-full bg-red-600 hover:bg-red-700 text-white font-bold py-3 px-6 rounded shadow transition-all cursor-pointer"
            
            # Hide timer label on error
            if hasattr(self, 'timer_label'):
                self.timer_label.classes = self.timer_label.classes.replace("block", "hidden")
                
            jp.Div(text=f"❌ Error: {str(e)}", a=card3, classes="text-red-600 font-bold mt-2")  
    return wp

jp.justpy(app, port=8000)