import os
import json
import pandas as pd
import ollama
import shutil      # <--- ADD THIS
import subprocess  # <--- ADD THIS
# Configuration
MODEL_NAME = "llama3.1:8b" 

# Cache Configuration
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache")
CACHE_FILE = os.path.join(CACHE_DIR, "template_meanings.json")

# ==========================================
# SYSTEM CHECKS (Moved from ai_assistant.py)
# ==========================================
def check_system_resources():
    """Checks if a GPU is available for processing."""
    print("\n--- [SYSTEM CHECK] ---")
    
    # Simple check for NVIDIA GPU via command line
    if shutil.which('nvidia-smi'):
        try:
            result = subprocess.run(['nvidia-smi', '-L'], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ GPU Detected: {result.stdout.strip()}")
                print(">> Ollama will automatically offload to GPU.")
            else:
                print("⚠️ NVIDIA-SMI found but returned error. Falling back to CPU logic.")
        except:
            print("⚠️ Error checking GPU. Assuming CPU.")
    else:
        print("ℹ️ No dedicated GPU detected (nvidia-smi missing). Running on CPU.")
    print("----------------------")

def ensure_model_available():
    """Checks if the model exists in Ollama. Pulls it if missing."""
    print(f"🔍 Checking for model: {MODEL_NAME}...")
    
    try:
        # List available models
        models_info = ollama.list()
        
        # Robustly extract model names (Handles different API versions)
        existing_models = []
        model_list = models_info.get('models', []) if isinstance(models_info, dict) else getattr(models_info, 'models', [])

        for m in model_list:
            if isinstance(m, dict):
                name = m.get('name') or m.get('model')
            else:
                name = getattr(m, 'name', None) or getattr(m, 'model', None)
            
            if name:
                existing_models.append(str(name))
        
        # 1. Exact Match Check
        if any(MODEL_NAME in m for m in existing_models):
            print(f"✅ Model '{MODEL_NAME}' is ready.")
            return True
        
        # 2. Fallback Check
        base_name = MODEL_NAME.split(':')[0]
        if any(base_name in m for m in existing_models):
            print(f"⚠️ Exact tag '{MODEL_NAME}' not found, but '{base_name}' exists.")
            return True

        # 3. Download
        print(f"⚠️ Model '{MODEL_NAME}' not found locally.")
        print(f"⬇️ Downloading {MODEL_NAME}... (This may take a while)")
        ollama.pull(MODEL_NAME)
        print(f"✅ Download complete: {MODEL_NAME}")
            
    except Exception as e:
        print(f"❌ Error communicating with Ollama: {e}")
        print("💡 Is the Ollama app running?")
        return False
    return True

# ==========================================
# 1. CACHE FUNCTIONS
# ==========================================
def load_template_cache():
    """Loads the dictionary of {template_pattern: meaning} from JSON."""
    if not os.path.exists(CACHE_FILE):
        print(f"[CACHE] No existing cache found at: {CACHE_FILE}")
        return {}
    try:
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # FIX: Normalize keys on load to ensure matching works
            normalized_data = {k.strip(): v for k, v in data.items()}
            print(f"[CACHE] Loaded {len(normalized_data)} templates from: {CACHE_FILE}")
            return normalized_data
    except Exception as e:
        print(f"[CACHE] Warning: Could not read cache file ({e}). Starting fresh.")
        return {}

def save_template_cache(cache_data):
    """Saves the updated dictionary to JSON."""
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=4, ensure_ascii=False)
        print(f"[CACHE] Saved cache to disk ({len(cache_data)} total items).")
    except Exception as e:
        print(f"[CACHE] Error saving cache: {e}")

# ==========================================
# 2. AI PROMPT
# ==========================================
SYSTEM_PROMPT = """You are a Linux Log Template Expander.
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

### COMMON SERVICE KNOWLEDGE BASE (Translate these terms)
- sshd: Secure Shell service (handles secure remote logins)
- ftpd: File Transfer Protocol service (handles file uploads/downloads)
- telnetd: Telnet service (handles unencrypted remote logins)
- su: Substitute User utility (handles switching user accounts)
- login: System Login process (handles local console sign-ins)
- unix_chkpwd: Password Verification Helper (verifies user passwords)
- passwd: Password Management tool (handles password changes)
- klogind: Kerberos Login service (handles network authentication)
- xinetd: Extended Internet Services daemon (manages network connections for other services)
- snmpd: Network Management service (reports system status for monitoring)
- gdm / gdm-binary: GNOME Display Manager (handles the graphical login screen)
- PAM-rootok: Root Permission Checker (verifies superuser access rights)

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
Input: <TIMESTAMP> <HOSTNAME> su(pam_unix)[<PID>]: session <STATE> for user <USERNAME>
Output: At <TIMESTAMP>, on server <HOSTNAME>, the Substitute User utility (su) running as process <PID> reported that a session entered the <STATE> state for user <USERNAME>.

Input: <TIMESTAMP> <HOSTNAME> ftpd[<PID>]: connection from <RHOST>
Output: At <TIMESTAMP>, the File Transfer service (ftpd) running as process <PID> on <HOSTNAME> received a connection request from remote host <RHOST>.

Input: <TIMESTAMP> <HOSTNAME> unix_chkpwd[<PID>]: check pass; user <USERNAME>
Output: At <TIMESTAMP>, the Password Verification Helper (unix_chkpwd) running as process <PID> on <HOSTNAME> reported a password check error regarding user <USERNAME>.
"""

def generate_single_meaning(template_pattern):
    """
    Sends a single template string to Ollama to get the English meaning.
    """
    try:
        response = ollama.chat(model=MODEL_NAME, messages=[
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': f"Input: {template_pattern}"}
        ])
        
        # Clean up the output
        clean_text = response['message']['content'].strip().replace('"', '').replace('\n', ' ')
        
        # Remove "Output:" prefix if the AI adds it
        if clean_text.lower().startswith("output:"):
            clean_text = clean_text[7:].strip()
            
        return clean_text
    except Exception as e:
        print(f"Error calling Llama: {e}")
        return template_pattern # Fallback to original

# ==========================================
# 3. MAIN FILE PROCESSOR
# ==========================================
def generate_meanings_for_file(input_excel_path):
    """
    Reads the parsed Excel, loops through templates, calls Llama, 
    and saves the result.
    """
    # --- [NEW] RUN CHECKS FIRST ---
    check_system_resources()
    if not ensure_model_available():
        raise RuntimeError("Ollama model not available. Cannot proceed.")
    # ------------------------------
    
    if not os.path.exists(input_excel_path):
        raise FileNotFoundError(f"Input file not found: {input_excel_path}")
    
    print("------ [GENERATING WITH LLAMA] ------")
    print(f"[AI] Reading templates from: {os.path.basename(input_excel_path)}")
    
    # 1. Read Data
    df_summary = pd.read_excel(input_excel_path, sheet_name="Template Summary")
    df_logs = pd.read_excel(input_excel_path, sheet_name="Log Analysis")
    
    # Sort for cleaner processing
    df_summary = df_summary.sort_values(by="Template ID")
    
    # FIX: Explicit string conversion and stripping for robust comparison
    raw_templates = df_summary['Template Pattern'].tolist()
    templates = [str(t).strip() for t in raw_templates]
    
    template_ids = df_summary['Template ID'].tolist()
    
    # 2. Load Cache
    cache = load_template_cache()
    final_meanings = [""] * len(templates)
    
    # 3. Identify New Templates
    new_indices = []
    
    # DEBUG: Track hit/miss for visibility
    hits = 0
    misses = 0

    for i, t in enumerate(templates):
        if t in cache:
            final_meanings[i] = cache[t] # Use cached version
            hits += 1
        else:
            new_indices.append(i) # Mark for generation
            misses += 1
            
    print(f"[AI] Total Templates: {len(templates)}")
    print(f"[AI] Cache Hits: {hits} (Skipping AI generation)")
    print(f"[AI] Cache Misses: {misses} (Queueing for AI)")
    
    # 4. Generate Loop
    if new_indices:
        print("\n" + "=" * 50)
        print("   STARTING GENERATION LOOP")
        print("=" * 50)
        
        count = 1
        total_new = len(new_indices)

        for idx in new_indices:
            template = templates[idx]
            t_id = template_ids[idx]
            
            # Print status
            print(f"[{count}/{total_new}] Generating for ID {t_id}...", end="\r")
            
            # CALL OLLAMA
            meaning = generate_single_meaning(template)
            
            # Store & Update Cache
            final_meanings[idx] = meaning
            cache[template] = meaning # Save stripped key
            
            # --- NEW FORMATTED OUTPUT ---
            # Clear the "Generating..." progress line first
            print(" " * 80, end="\r") 
            
            # Line 1: ID & Template
            print(f"[{t_id}] {template}")
            
            # Line 2: The Meaning
            print(f"      ↳ {meaning}")
            
            # Optional: Separator for readability
            print("-" * 60) 
            
            count += 1
            
        # Save Cache to disk
        save_template_cache(cache)
    else:
        print("\n[AI] All templates found in cache. No AI calls needed! 🚀")
        
    # 5. Save Output Excel
    df_summary['Event Meaning'] = final_meanings
    
    base_dir = os.path.dirname(input_excel_path)
    base_name = os.path.basename(input_excel_path)
    output_filename = base_name.replace("_analysis.xlsx", "_meaning.xlsx")
    save_path = os.path.join(base_dir, output_filename)
    
    with pd.ExcelWriter(save_path, engine='openpyxl') as writer:
        df_logs.to_excel(writer, sheet_name='Log Analysis', index=False)
        df_summary.to_excel(writer, sheet_name='Template Summary', index=False)
        
    print(f"[AI] Output saved to: {save_path}")
    
    # RETURN THE TWO VALUES PIPELINE.PY EXPECTS
    return save_path, len(df_summary)