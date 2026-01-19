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
    # FORCE CPU (-1) to ensure stability on Windows
    return -1 

def load_summary_model():
    global _SUMMARY_PIPELINE
    if _SUMMARY_PIPELINE is not None:
        return _SUMMARY_PIPELINE

    print(f"\n[AI] Loading Summary Model ({SUMMARY_MODEL_ID})...")
    
    try:
        device = get_device()
        print(f"[AI] Device set to: {'GPU' if device == 0 else 'CPU'}")
        
        # 1. Load Tokenizer (WITH EXPLICIT LIMIT)
        print("[AI] Loading Tokenizer...")
        tokenizer = AutoTokenizer.from_pretrained(
            SUMMARY_MODEL_ID, 
            cache_dir=LOCAL_MODEL_PATH,
            local_files_only=False,
            model_max_length=1024  # <--- FIX 1: Explicitly tell it the limit
        )
        
        # 2. Load Model
        print("[AI] Loading Model Weights...")
        model = AutoModelForSeq2SeqLM.from_pretrained(
            SUMMARY_MODEL_ID, 
            cache_dir=LOCAL_MODEL_PATH,
            local_files_only=False
        )

        # 3. Resize Embeddings (Vocab Mismatch Fix)
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

    # FIX 2: MANUAL "NUCLEAR" TRUNCATION
    # BART crashes if input tokens > 1024. 
    # We strip the text to 3000 chars (approx 750 tokens) to stay safely inside the limit.
    if len(context_text) > 3000:
        print(f"[AI] Input too long ({len(context_text)} chars). Truncating to safe limit...")
        context_text = context_text[:3000]

    print("[AI] Generating Executive Brief using BART...")
    try:
        output = summarizer(
            context_text, 
            max_length=200, 
            min_length=60, 
            do_sample=False,
            truncation=True 
        )
        return output[0]['summary_text'].strip()
    except Exception as e:
        print(f"[AI] Summarization failed: {e}")
        return "Error generating summary."