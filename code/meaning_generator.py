import os
import torch
import pandas as pd
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

# ==========================================
# 1. CONFIGURATION
# ==========================================
MODEL_ID = "microsoft/Phi-3-mini-4k-instruct"
# Global cache for the model so we don't reload it every time
_LOADED_PIPELINE = None

# ==========================================
# 2. MODEL LOADING
# ==========================================
def load_model():
    """
    Loads the Phi-3 model. On the first run, it downloads the model locally.
    On subsequent runs, it loads from the local cache (offline).
    """
    global _LOADED_PIPELINE
    if _LOADED_PIPELINE is not None:
        return _LOADED_PIPELINE
    print(f"\n[AI] Loading Model: {MODEL_ID}...")
    print("[AI] NOTE: First run requires internet to download weights (~8GB).")
    print("[AI] Once downloaded, it runs 100% locally/offline.")
    
    try:
        tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
        # Load Model (Optimized for hardware)
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[AI] Hardware detected: {device.upper()}")

        model = AutoModelForCausalLM.from_pretrained(
            MODEL_ID, 
            device_map=device, 
            dtype="auto", 
            trust_remote_code=False,
            # This ensures we use the local cache if available
            local_files_only=False 
        )
        _LOADED_PIPELINE = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
            max_new_tokens=120,
            return_full_text=False,
            do_sample=False
        )
        print("[AI] SUCCESS: Model loaded and ready!")
        return _LOADED_PIPELINE
        
    except Exception as e:
        print(f"[AI] Error loading model: {e}")
        return None

# ==========================================
# 3. PROMPT GENERATION
# ==========================================
def build_prompt(template):
    system_instruction = """You are a Linux Log Template Expander.
Your goal is to turn a technical log pattern into a natural English sentence structure.

### VARIABLE DICTIONARY (What the placeholders mean)
- <TIMESTAMP>: Date/Time of the event (e.g., Jan 12 14:32:10 2024, Jun 22 04:30:55).
- <HOSTNAME>: The server or machine name (e.g., combo, web-server-01).
- <RHOST> / <IP>: Remote host or IP address involved (e.g., 192.168.1.45, 061092085098.ctinets.com, massive.merukuru.org, 220-135-151-1.hinet-ip.hinet.net).
- <USER> / <USERNAME>: User account involved in the event (e.g., root, admin, john, cyrus).
- <UID>: Identifies the actual user who owns the process; User ID (e.g., 0, 1, 2)
- <PID>: Process ID numbers (e.g., 0, 1001, 3456).
- <STATE>: Event or system status (e.g., startup, shutdown, opened, closed, failed).
- <NUM>: Any numeric value such as counts, durations, or error numbers (e.g., 3, 98, 120).
- <EUID>: Effective User ID of the running process (e.g., 0, 1000).
- <TTY>: Terminal or pseudo-terminal used (e.g., pts/0, tty1, NODEVssh).
- <FD>: File descriptor number used by a process (e.g., 3, 5, 12).
- <ERRNO>: Operating system error number indicating failure (e.g., 98, 13).

### CORE TASK
Create a sentence that describes the event while preserving ALL variable placeholders as **fixed data slots**. 
Do not interpret the variables (e.g., do not change "<STATE>" to "initiated" or "closed"). Treat them as proper nouns that must appear in the final output.

### UNIVERSAL RULES
1. **Preservation:** Every placeholder inside < > (e.g., <TIMESTAMP>, <PID>, <STATE>) MUST appear in the output exactly as written.
2. **Grammar:** Structure the sentence so it makes sense regardless of what value fills the placeholder. 
   - *Bad:* "The session was <STATE>." (grammatically risky if state is 'failure')
   - *Good:* "The session entered a state of <STATE>." (always works)
3. **Completeness:** Never summarize. If a template has 5 variables, your sentence must contain 5 variables.

### EXAMPLES
Input: <TIMESTAMP> <HOSTNAME> su: session <STATE> for user <USERNAME>
Output: At <TIMESTAMP>, on the server <HOSTNAME>, a 'su' session for user <USERNAME> was recorded with a status of <STATE>.

Input: <TIMESTAMP> <HOSTNAME> sshd[<PID>]: Failed password for <USERNAME> from <RHOST>
Output: At <TIMESTAMP>, the server <HOSTNAME> recorded a failed password attempt for user <USERNAME> coming from remote host <RHOST>, handled by process ID <PID>.
"""
    
    # Phi-3 Chat Format Tags
    return f"<|user|>\n{system_instruction}\n\nInput:\n{template}\n<|end|>\n<|assistant|>"

# ==========================================
# 4. GENERATION FUNCTION
# ==========================================
def generate_meanings_for_file(input_excel_path):
    """
    Reads the parsed Excel, generates meanings using Phi-3, 
    and saves a new Excel file.
    """
    if not os.path.exists(input_excel_path):
        raise FileNotFoundError(f"Input file not found: {input_excel_path}")
    
    #1. Load Model
    pipe=load_model()
    if not pipe:
        raise RuntimeError("Model failed to load.")
    
    # 2. Read Excel
    print(f"[AI] Reading templates from: {os.path.basename(input_excel_path)}")
    df_summary = pd.read_excel(input_excel_path, sheet_name="Template Summary")
    df_logs = pd.read_excel(input_excel_path, sheet_name="Log Analysis")
    
    #3. Build Prompts
    #sorting by temp id to keep order
    df_summary = df_summary.sort_values(by="Template ID")
    templates = df_summary['Template Pattern'].tolist()
    template_ids = df_summary['Template ID'].tolist()
    
    prompts = [build_prompt(t) for t in templates]
    print(f"[AI] Generating meanings for {len(prompts)} templates...")
    print("-" * 60)
    print(f"{'ID':<5} | {'TEMPLATE (Truncated)':<40} | {'GENERATED MEANING'}")
    print("-" * 60)
    
    explanations = []
    
    # 4. Run Inference (Iterate one by one to print status)
    # Using the pipeline in batch mode is faster, but loop allows live printing
    results = pipe(prompts, batch_size=4) # Batch size speeds up GPU usage
    
    for i, output in enumerate(results):
        raw_result = output[0]['generated_text'].strip()
        
        # Clean Output
        clean_result = raw_result.split('\n')[0]
        clean_result = clean_result.replace('Output:', '').replace('Result:', '').strip()
        clean_result = clean_result.replace('"', '').replace("'", "")
        
        if clean_result and not clean_result.endswith('.'):
            clean_result += "."
            
        explanations.append(clean_result)
        
        # Live Terminal Output
        t_trunc = (templates[i][:37] + '...') if len(templates[i]) > 37 else templates[i]
        print(f"{template_ids[i]:<5} | {t_trunc:<40} | {clean_result}")

    # 5. Save Output
    df_summary['Event Meaning'] = explanations
    base_dir = os.path.dirname(input_excel_path)
    base_name = os.path.basename(input_excel_path)
    output_filename = base_name.replace("_analysis.xlsx", "_meaning.xlsx")
    save_path = os.path.join(base_dir, output_filename)
    
    with pd.ExcelWriter(save_path, engine='openpyxl') as writer:
        df_logs.to_excel(writer, sheet_name='Log Analysis', index=False)
        df_summary.to_excel(writer, sheet_name='Template Summary', index=False)
        
    print("-" * 60)
    print(f"[AI] Generation Complete. Saved to: {os.path.basename(save_path)}")
    
    return save_path, len(df_summary)
"""# ==========================================
# 4. MAIN EXECUTION LOGIC
# ==========================================
def main():
    # Load the AI model
    pipe = load_model()

    # Locate Data
    print(f"\nLooking for files in: {os.path.abspath(DATA_FOLDER)}")
    
    # Ensure data folder exists
    current_data_folder = DATA_FOLDER
    if not os.path.exists(current_data_folder):
        print(f"WARNING: Data folder '{DATA_FOLDER}' not found.")
        current_data_folder = "."  # Fallback to current directory
        print(f"Searching in current directory: {os.path.abspath(current_data_folder)}")

    available_files = [f for f in os.listdir(current_data_folder) if f.endswith('.xlsx')]
    target_filename = None

    # File Selection Logic
    if not available_files:
        print("WARNING: No Excel files found automatically.")
        user_input = input("Please paste the full path to your file: ").strip().replace('"', '')
        if os.path.exists(user_input):
            target_filename = user_input
    else:
        print("\nAvailable Files:")
        for i, f in enumerate(available_files):
            print(f" [{i+1}] {f}")
        
        selection = input("\nEnter the file number (or filename): ").strip()

        # Handle number selection
        if selection.isdigit() and 1 <= int(selection) <= len(available_files):
            target_filename = os.path.join(current_data_folder, available_files[int(selection)-1])
        # Handle filename input
        elif selection in available_files:
            target_filename = os.path.join(current_data_folder, selection)
        else:
            target_filename = selection.replace('"', '')

    # Processing Loop
    if not target_filename or not os.path.exists(target_filename):
        print(f"ERROR: File not found: {target_filename}")
        return

    print(f"\nReading {target_filename}...")
    try:
        df_summary = pd.read_excel(target_filename, sheet_name="Template Summary")
        df_logs = pd.read_excel(target_filename, sheet_name="Log Analysis")
        
        templates = df_summary['Template Pattern'].tolist()
        prompts = [build_prompt(t) for t in templates]
        
        print(f"Processing {len(prompts)} templates...")
        explanations = []

        # Run Inference
        for output in tqdm(pipe(prompts, max_new_tokens=120, return_full_text=False, do_sample=False), total=len(prompts)):
            
            raw_result = output[0]['generated_text'].strip()
            
            # Clean Output
            clean_result = raw_result.split('\n')[0] # First line only
            clean_result = clean_result.replace('Output:', '').replace('Result:', '').strip()
            clean_result = clean_result.replace('"', '').replace("'", "")
            
            if clean_result and not clean_result.endswith('.'):
                clean_result += "."
                
            explanations.append(clean_result)

        # Save Output
        df_summary['Event Meaning'] = explanations
        
        # Ensure output folder exists
        os.makedirs(OUTPUT_FOLDER, exist_ok=True)
        
        base_name = os.path.basename(target_filename)
        
        # --- CHANGED LINE BELOW ---
        # Renames file to: [OriginalName]_meaning.xlsx
        save_path = os.path.join(OUTPUT_FOLDER, base_name.replace(".xlsx", "_meaning.xlsx"))
        
        with pd.ExcelWriter(save_path, engine='openpyxl') as writer:
            df_logs.to_excel(writer, sheet_name='Log Analysis', index=False)
            df_summary.to_excel(writer, sheet_name='Template Summary', index=False)
            
        print("-" * 60)
        print("SAMPLE RESULTS:")
        for i in range(min(3, len(explanations))):
            print(f"TEMPLATE: {templates[i][:50]}...")
            print(f"MEANING:  {explanations[i]}")
        
        print("-" * 60)
        print(f"DONE! Saved to: {save_path}")
        
    except Exception as e:
        print(f"Error processing file: {e}")
        
if __name__ == "__main__":
    main()"""