import os
import torch
# CHANGED: Added AutoTokenizer and AutoModelForSeq2SeqLM
from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM
# ==========================================
# 1. CONFIGURATION
# ==========================================
# The "Gold Standard" summarization model (Higher quality, but ~1.6GB)
SUMMARY_MODEL_ID = "facebook/bart-large-cnn"

# Path setup
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
LOCAL_MODEL_PATH = os.path.join(BASE_DIR, "models")

# Global holder
_SUMMARY_PIPELINE = None

# ==========================================
# 2. MODEL LOADER
# ==========================================
def get_device():
    """Returns 0 for GPU, -1 for CPU."""
    # return 0 if torch.cuda.is_available() else -1  <-- Comment this out
    return -1  # <-- Force CPU

def load_summary_model():
    """
    Loads the BART model for summarization safely.
    """
    global _SUMMARY_PIPELINE
    if _SUMMARY_PIPELINE is not None:
        return _SUMMARY_PIPELINE

    print(f"\n[AI] Loading Summary Model ({SUMMARY_MODEL_ID})...")
    print(f"[AI] Note: This is a large model (1.6GB). First run will take time to download.")
    
    try:
        device = get_device()
        
        # 1. Load Tokenizer explicitly (Safe place for cache_dir)
        print("[AI] Loading Tokenizer...")
        tokenizer = AutoTokenizer.from_pretrained(
            SUMMARY_MODEL_ID, 
            cache_dir=LOCAL_MODEL_PATH
        )
        
        # 2. Load Model explicitly (Safe place for cache_dir)
        print("[AI] Loading Model Weights...")
        model = AutoModelForSeq2SeqLM.from_pretrained(
            SUMMARY_MODEL_ID, 
            cache_dir=LOCAL_MODEL_PATH
        )
        
        # 3. Create Pipeline (Clean, no extra args to cause confusion)
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
    """
    Takes a long text block (stats/narrative) and returns a concise summary.
    """
    summarizer = load_summary_model()
    if not summarizer:
        return "AI Summary unavailable (Model failed to load)."

    print("[AI] Generating Executive Brief using BART...")
    
    try:
        # BART parameters for Log Summaries:
        # max_length: 200 words (enough for a solid paragraph)
        # min_length: 60 words (forces it to be detailed, not just one sentence)
        # do_sample=False: Deterministic (we want consistent reports)
        output = summarizer(
            context_text, 
            max_length=200, 
            min_length=60, 
            do_sample=False 
        )
        
        # Extract text
        summary_text = output[0]['summary_text']
        return summary_text.strip()
        
    except Exception as e:
        print(f"[AI] Summarization failed: {e}")
        return "Error generating summary."