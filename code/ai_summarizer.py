import os
import torch
import gc
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

# ==========================================
# CONFIGURATION
# ==========================================
# Point to the LOCAL folder we just downloaded to
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
LOCAL_MODEL_PATH = os.path.join(BASE_DIR, "models", "llama3_8b")

def generate_ai_summary(report_path):
    """
    Reads the Executive Summary and generates a brief using the LOCALLY saved Llama 3 model.
    """
    if not os.path.exists(report_path):
        print(f"[AI] Error: Report file not found at {report_path}")
        return None

    # Check if model exists locally
    if not os.path.exists(LOCAL_MODEL_PATH):
        print(f"\n[AI] ❌ CRITICAL ERROR: Model not found at {LOCAL_MODEL_PATH}")
        print("[AI] Please run 'python code/download_model.py' first!")
        return None

    print(f"\n[AI] Loading Llama 3 from: {LOCAL_MODEL_PATH}...")

    # 1. Read Report
    try:
        with open(report_path, "r", encoding="utf-8") as f:
            report_content = f.read()
    except Exception as e:
        print(f"[AI] Failed to read report: {e}")
        return None

    # 2. Setup Output
    base_dir = os.path.dirname(report_path)
    output_path = os.path.join(base_dir, "ai_summary.txt")

    try:
        # 3. Load from Local Folder with CPU Offload
        # This config allows the model to use System RAM if VRAM is full
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            llm_int8_enable_fp32_cpu_offload=True  # <--- PREVENTS CRASHES
        )

        tokenizer = AutoTokenizer.from_pretrained(LOCAL_MODEL_PATH)
        
        model = AutoModelForCausalLM.from_pretrained(
            LOCAL_MODEL_PATH,
            quantization_config=bnb_config,
            device_map="auto", # Smartly splits between GPU and CPU
            low_cpu_mem_usage=True
        )

        pipe = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
        )

        # 4. Prompt
        system_msg = (
            "You are a Cybersecurity Expert. "
            "Read the following log analysis report and write a concise 'Management Summary'. "
            "Focus on the Health Status, Critical Threats, and Key Recommendations. "
            "Do not simply repeat the metrics; analyze them."
        )

        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": f"Here is the detailed report:\n\n{report_content}"}
        ]

        terminators = [
            pipe.tokenizer.eos_token_id,
            pipe.tokenizer.convert_tokens_to_ids("<|eot_id|>")
        ]

        # 5. Generate
        print("[AI] Generating summary with Llama 3 (Offline Mode)...")
        outputs = pipe(
            messages,
            max_new_tokens=1024,
            eos_token_id=terminators,
            do_sample=True,
            temperature=0.6,
            top_p=0.9,
        )

        summary_text = outputs[0]["generated_text"][-1]["content"]

        # 6. Save
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(summary_text)
        
        # Cleanup
        del model
        del pipe
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        print(f"[AI] ✅ Summary generated and saved to: {os.path.basename(output_path)}")
        return output_path

    except Exception as e:
        print(f"[AI] ❌ Generation failed: {e}")
        return None