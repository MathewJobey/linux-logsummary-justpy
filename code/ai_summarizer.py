import os
import torch
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM

# ==========================================
# CONFIGURATION
# ==========================================
MODEL_ID = "meta-llama/Meta-Llama-3.1-8B-Instruct"

def generate_ai_summary(report_path):
    """
    Reads the full Executive Summary text file and generates a 
    high-level AI summary using Llama-3.1-8B-Instruct.
    """
    if not os.path.exists(report_path):
        print(f"[AI] Error: Report file not found at {report_path}")
        return None

    print(f"\n[AI] Initializing Llama-3.1 to summarize: {os.path.basename(report_path)}...")

    # 1. Read the Executive Summary
    try:
        with open(report_path, "r", encoding="utf-8") as f:
            report_content = f.read()
    except Exception as e:
        print(f"[AI] Failed to read report: {e}")
        return None

    # 2. Setup Output Path
    base_dir = os.path.dirname(report_path)
    output_path = os.path.join(base_dir, "ai_summary.txt")

    try:
        # 3. Load Model
        # device_map="auto" will automatically use GPU if available
        tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_ID,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            device_map="auto"
        )

        pipe = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
        )

        # 4. Construct Prompt (Llama 3 Instruct Format)
        system_msg = (
            "You are a Cybersecurity Expert. "
            "Read the following log analysis report and write a concise Summary about the LOG ANALYSIS REPORT."
            "Focus on all the sections of the report and dont miss any important details. "
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
        print("[AI] Generating summary (this may take a moment)...")
        outputs = pipe(
            messages,
            max_new_tokens=1024, # Default length limit
            eos_token_id=terminators,
            do_sample=True,
            temperature=0.6,
            top_p=0.9,
        )

        summary_text = outputs[0]["generated_text"][-1]["content"]

        # 6. Save Output
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(summary_text)
        
        print(f"[AI] ✅ Summary generated and saved to: {os.path.basename(output_path)}")
        return output_path

    except Exception as e:
        print(f"[AI] ❌ Generation failed: {e}")
        return None