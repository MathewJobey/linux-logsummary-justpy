import os
import torch

# ==========================================
# CRITICAL WINDOWS FIX
# ==========================================
os.environ["HF_HUB_DISABLE_SYMLINKS"] = "1"
os.environ["TRANSFORMERS_CACHE"] = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")

from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM

# ==========================================
# 1. CONFIGURATION
# ==========================================
SUMMARY_MODEL_ID = "facebook/bart-large-cnn"
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
LOCAL_MODEL_PATH = os.path.join(BASE_DIR, "models")
_SUMMARY_PIPELINE = None

# ==========================================
# 2. MODEL LOADER
# ==========================================
def get_device():
    """Returns 0 for GPU, -1 for CPU."""
    return 0 if torch.cuda.is_available() else -1

def load_summary_model():
    global _SUMMARY_PIPELINE
    if _SUMMARY_PIPELINE is not None:
        return _SUMMARY_PIPELINE

    print(f"\n[AI] Loading Summary Model ({SUMMARY_MODEL_ID})...")
    
    try:
        device = get_device()
        print(f"[AI] Device set to: {'GPU' if device == 0 else 'CPU'}")
        
        # 1. Load Tokenizer
        print("[AI] Loading Tokenizer...")
        tokenizer = AutoTokenizer.from_pretrained(
            SUMMARY_MODEL_ID, 
            cache_dir=LOCAL_MODEL_PATH,
            local_files_only=False,
            model_max_length=1024
        )
        
        # 2. Load Model
        print("[AI] Loading Model Weights...")
        model = AutoModelForSeq2SeqLM.from_pretrained(
            SUMMARY_MODEL_ID, 
            cache_dir=LOCAL_MODEL_PATH,
            local_files_only=False
        )

        # 3. Resize Embeddings (Safety Check)
        if len(tokenizer) > model.config.vocab_size:
            print(f"[AI] Resizing model embeddings from {model.config.vocab_size} to {len(tokenizer)}...")
            model.resize_token_embeddings(len(tokenizer))
        
        # 4. Create Pipeline
        _SUMMARY_PIPELINE = pipeline(
            "summarization", 
            model=model, 
            tokenizer=tokenizer,
            device=device
        )
        
        print("[AI] Summary Model Loaded Successfully!")
        return _SUMMARY_PIPELINE
        
    except Exception as e:
        print(f"[AI] ❌ Error loading summary model: {e}")
        return None

# ==========================================
# 3. GENERATION FUNCTION
# ==========================================
def generate_summary(context_text):
    summarizer = load_summary_model()
    if not summarizer:
        return "AI Summary unavailable (Model failed to load)."

    # --- FIX: SMART TOKEN TRUNCATION ---
    # Instead of blindly cutting at 3000 chars, we tokenize first to fit 
    # exactly 1024 tokens. This maximizes context without crashing.
    try:
        tokenizer = summarizer.tokenizer
        
        # 1. Convert text to tokens
        inputs = tokenizer(context_text, return_tensors="pt", truncation=False)
        input_ids = inputs["input_ids"]
        
        # 2. Check length
        curr_len = input_ids.shape[1]
        max_allowed = 1024  # BART's hard limit
        
        if curr_len > max_allowed:
            print(f"[AI] Input too long ({curr_len} tokens). Smart truncating to {max_allowed} tokens...")
            # Slice the tokens, not the characters
            input_ids = input_ids[:, :max_allowed]
            # Decode back to text (ignores special characters to prevent errors)
            context_text = tokenizer.decode(input_ids[0], skip_special_tokens=True)
        
        print("[AI] Generating Executive Brief using BART...")
        
        # 3. Generate with "Human-Readable" parameters
        output = summarizer(
            context_text, 
            max_length=450,       # Allow longer summary
            min_length=150,       # FORCE it to write at least a paragraph
            length_penalty=2.0,   # Encourages detailed sentences
            no_repeat_ngram_size=3, # Prevents robotic repetition
            do_sample=False,      # Keep it factual
            truncation=True
        )
        return output[0]['summary_text'].strip()
        
    except Exception as e:
        print(f"[AI] Summarization failed: {e}")
        return "Error generating summary."