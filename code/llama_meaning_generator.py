import os
import json
import pandas as pd
import ollama

# Configuration
MODEL_NAME = "llama3.1:8b" 

# Cache Configuration
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache")
CACHE_FILE = os.path.join(CACHE_DIR, "template_meanings.json")

# ==========================================
# 1. CACHE FUNCTIONS
# ==========================================
def load_template_cache():
    """Loads the dictionary of {template_pattern: meaning} from JSON."""
    if not os.path.exists(CACHE_FILE):
        return {}
    try:
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"[CACHE] Warning: Could not read cache file ({e}). Starting fresh.")
        return {}

def save_template_cache(cache_data):
    """Saves the updated dictionary to JSON."""
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=4, ensure_ascii=False)
        print(f"[CACHE] Updated cache with {len(cache_data)} templates.")
    except Exception as e:
        print(f"[CACHE] Error saving cache: {e}")

# ==========================================
# 2. AI PROMPT
# ==========================================
SYSTEM_PROMPT = """You are a Linux Log Template Expander.
Your goal is to turn a technical log pattern into a natural English sentence structure.

### VARIABLE DICTIONARY (What the placeholders mean)
- <TIMESTAMP>: Date/Time of the event.
- <HOSTNAME>: The server or machine name.
- <RHOST> / <IP>: Remote host or IP address.
- <USER> / <USERNAME>: User account involved.
- <UID>: User ID.
- <PID>: Process ID.
- <STATE>: Event status (e.g., failed, opened).
- <NUM>: Numeric values.

### UNIVERSAL RULES
1. **Preservation:** Every placeholder inside < > MUST appear in the output exactly as written.
2. **Grammar:** Structure the sentence so it makes sense regardless of variables.
3. **Completeness:** Do not summarize.

### EXAMPLES
Input: <TIMESTAMP> sshd[<PID>]: Failed password for <USER> from <RHOST>
Output: At <TIMESTAMP>, the sshd service (PID <PID>) recorded a failed password attempt for user <USER> originating from <RHOST>.
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
# 3. MAIN FILE PROCESSOR (The Missing Part!)
# ==========================================
def generate_meanings_for_file(input_excel_path):
    """
    Reads the parsed Excel, loops through templates, calls Llama, 
    and saves the result.
    """
    if not os.path.exists(input_excel_path):
        raise FileNotFoundError(f"Input file not found: {input_excel_path}")
    
    print("------ [GENERATING WITH LLAMA] ------")
    print(f"[AI] Reading templates from: {os.path.basename(input_excel_path)}")
    
    # 1. Read Data
    df_summary = pd.read_excel(input_excel_path, sheet_name="Template Summary")
    df_logs = pd.read_excel(input_excel_path, sheet_name="Log Analysis")
    
    # Sort for cleaner processing
    df_summary = df_summary.sort_values(by="Template ID")
    templates = df_summary['Template Pattern'].tolist()
    template_ids = df_summary['Template ID'].tolist()
    
    # 2. Load Cache
    cache = load_template_cache()
    final_meanings = [""] * len(templates)
    
    # 3. Identify New Templates
    new_indices = []
    for i, t in enumerate(templates):
        if t in cache:
            final_meanings[i] = cache[t] # Use cached version
        else:
            new_indices.append(i) # Mark for generation
            
    print(f"[AI] Total Templates: {len(templates)}")
    print(f"[AI] Cached: {len(templates) - len(new_indices)}")
    print(f"[AI] New to Generate: {len(new_indices)}")
    
    # 4. Generate Loop
    if new_indices:
        print("\n" + "=" * 50)
        print("   STARTING GENERATION LOOP")
        print("=" * 50)
        
        for idx in new_indices:
            template = templates[idx]
            t_id = template_ids[idx]
            
            # CALL OLLAMA
            meaning = generate_single_meaning(template)
            
            # Store & Update Cache
            final_meanings[idx] = meaning
            cache[template] = meaning
            
            # Print Progress
            print(f"[{t_id}] -> {meaning[:60]}...")
            
        # Save Cache to disk
        save_template_cache(cache)
    else:
        print("[AI] All templates found in cache. Skipping generation!")
        
    # 5. Save Output Excel
    df_summary['Event Meaning'] = final_meanings
    
    base_dir = os.path.dirname(input_excel_path)
    base_name = os.path.basename(input_excel_path)
    output_filename = base_name.replace("_analysis.xlsx", "_meaning.xlsx")
    save_path = os.path.join(base_dir, output_filename)
    
    with pd.ExcelWriter(save_path, engine='openpyxl') as writer:
        df_logs.to_excel(writer, sheet_name='Log Analysis', index=False)
        df_summary.to_excel(writer, sheet_name='Template Summary', index=False)
        
    print(f"[AI] Saved to: {save_path}")
    
    # RETURN THE TWO VALUES PIPELINE.PY EXPECTS
    return save_path, len(df_summary)