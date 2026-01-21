import os
import ollama

# ==========================================
# CONFIGURATION
# ==========================================
MODEL_NAME = "llama3.1"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT_FILENAME = "Log_Analysis_Report.txt"

# ==========================================
# PROMPTS
# ==========================================

PROMPT_NARRATIVE = (
    "You are a Senior System Administrator with deep knowledge about Linux server logs. "
    "Write a fluid, narrative summary of the provided Log Analysis Report.\n\n"
    "**STYLE GUIDELINES:**\n"
    "- **Narrative Flow:** Do not use bullet points or rigid section headers. Write in cohesive paragraphs that connect the events together logically.\n"
    "- **Plain English:** Avoid technical jargon like 'Template IDs' or raw log timestamps. For example; instead of saying 'Template 11 occurred', say the meaning of it that's provided , in this case 'We noticed repeated Kerberos authentication failures'.\n"
    "- **Synthesize:** Explain the whole report. Start with the overall health status. Then, weave together the critical threats, security warnings, and user activity into a story. For example, if there are failed logins and a brute force attack, connect them.\n"
    "- **Data Handling:** Mention only the top 2-3 worst offender IPs or hosts or users naturally within the sentences. Do not list them all.\n\n"
    "**CLOSING:**\n"
    "End the summary naturally and add this exact footer in italics: \n"
    "'*Further detailed info can be found in the Log_Analysis_Report.txt file.*'"
)

PROMPT_STRUCTURED = (
    "You are a Senior System Administrator required to write a professional, easy-to-understand summary of the Log Analysis Report for a Linux server. "
    "The Log Analysis report content consists of these sections which you can go through: Executive Overview, Security Audit Metrics, Risk Event Highlights, Threat Intelligence, User Session Activity, Rare Log Patterns, and Critical Breakdown.\n\n"
    "**INSTRUCTIONS:**\n"
    "- Synthesize: Go through each section and summarize them all together.\n"
    "- Cleaner Output: Try not to mention 'Template IDs' (e.g., Template 11) or quote the raw log templates (e.g., <TIMESTAMP>...). Instead, describe the event using the 'MEANING' provided in the report.\n"
    "- Handling Data Lists: Do not list every IP or host or usernames. Mention the top 2-3 examples and maybe how many more number of elements are there and then at the very bottom of the summary strictly state in italics: 'Further detailed info can be found in the Log_Analysis_Report.txt file.'\n"
    "**FORMAT:**\n"
    "- Keep the response concise (250-300 words max). Prioritize the most critical information first."
)

def test_summary_generation():
    print("--- Ollama Llama 3.1 Summary Tester (Dual Mode) ---")
    
    # 1. Find Report
    possible_paths = [
        os.path.join(BASE_DIR, "Logs", REPORT_FILENAME),
        os.path.join(BASE_DIR, REPORT_FILENAME),
        REPORT_FILENAME
    ]
    
    report_path = None
    for path in possible_paths:
        if os.path.exists(path):
            report_path = path
            break
            
    if not report_path:
        print(f"❌ Error: Could not find {REPORT_FILENAME}")
        return

    print(f"✅ Found report at: {report_path}")
    
    # 2. Ask User for Prompt Preference
    print("\nSelect Output Style:")
    print("1. Natural/Narrative (Fluid, story-like)")
    print("2. Professional/Structured (Concise sections)")
    
    user_choice = input("Enter choice (1 or 2): ").strip()
    
    if user_choice == "1":
        print(">> Selected: Natural/Narrative Style")
        system_instruction = PROMPT_NARRATIVE
        output_filename = "ai_summary_narrative.txt"
    elif user_choice == "2":
        print(">> Selected: Professional/Structured Style")
        system_instruction = PROMPT_STRUCTURED
        output_filename = "ai_summary_structured.txt"
    else:
        print(">> Invalid input. Defaulting to Professional/Structured Style.")
        system_instruction = PROMPT_STRUCTURED
        output_filename = "ai_summary_structured.txt"

    # 3. Read File
    try:
        with open(report_path, "r", encoding="utf-8") as f:
            report_content = f.read()
    except Exception as e:
        print(f"❌ Failed to read report: {e}")
        return

    # 4. Call Ollama
    print(f"🔄 Sending request to Ollama ({MODEL_NAME})...")

    try:
        response = ollama.chat(model=MODEL_NAME, messages=[
            {'role': 'system', 'content': system_instruction},
            {'role': 'user', 'content': f"Log Analysis Report content:\n{report_content}"},
        ])
        
        summary_text = response['message']['content']

        # 5. Output
        print("\n" + "="*50)
        print("         AI SUMMARY REPORT")
        print("="*50)
        print(summary_text)
        print("="*50)

        # Save
        output_path = os.path.join(BASE_DIR, output_filename)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(summary_text)
        print(f"\n✅ Saved summary to: {output_path}")

    except Exception as e:
        print(f"\n❌ Failed to connect to Ollama: {e}")

if __name__ == "__main__":
    test_summary_generation()