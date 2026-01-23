import os
import ollama


# ==========================================
# CONFIGURATION
# ==========================================
MODEL_NAME = "llama3.1:8b"

# ==========================================
# PROMPTS
# ==========================================

PROMPT_NARRATIVE = (
    "You are a Senior System Administrator with deep knowledge about Linux server logs. "
    "Write a fluid, narrative summary (250-300 words max) of the provided Log Analysis Report.\n\n"
    "**STYLE GUIDELINES:**\n"
    "- **Narrative Flow:** Do not use bullet points or rigid section headers. Write in cohesive paragraphs that connect the events together logically.\n"
    "- **Plain English:** Avoid technical jargon like 'Template IDs' or raw log timestamps. For example; instead of saying 'Template 11 occurred', say the meaning of it that's provided , in this case 'We noticed repeated Kerberos authentication failures'.\n"
    "- **Synthesize:** Explain the whole report. Start with the overall health status. Then, weave together the critical threats, security warnings, and user activity into a story. For example, if there are failed logins and a brute force attack, connect them.\n"
    "- **Data Handling:** Mention only the top 2-3 worst offender IPs or hosts or users naturally within the sentences. Do not list them all.\n\n"
    "**CLOSING:**\n"
    "End the summary naturally and add this exact footer in italics: \n"
    "'*Further detailed info can be found in the Log_Analysis_Report.md file.*'"
)

PROMPT_STRUCTURED = (
    "You are a Senior System Administrator required to write a professional, easy-to-understand summary of the Log Analysis Report for a Linux server. "
    "The Log Analysis report content consists of these sections which you can go through: Executive Overview, Security Audit Metrics, Risk Event Highlights, Threat Intelligence, User Session Activity, Rare Log Patterns, and Critical Breakdown.\n\n"
    "**INSTRUCTIONS:**\n"
    "- Synthesize: Go through each section and summarize them all together.\n"
    "- Cleaner Output: Try not to mention 'Template IDs' (e.g., Template 11) or quote the raw log templates (e.g., <TIMESTAMP>...). Instead, describe the event using the 'MEANING' provided in the report.\n"
    "- Handling Data Lists: Do not list every IP or host or usernames. Mention the top 2-3 examples and maybe how many more number of elements are there and then at the very bottom of the summary strictly state in italics: 'Further detailed info can be found in the Log_Analysis_Report.md file.'\n"
    "**FORMAT:**\n"
    "- Keep the response concise (250-300 words max). Prioritize the most critical information first."
)
# ==========================================
# AI FUNCTIONS
# ==========================================

def generate_summary(report_path, style="structured"):
    """
    Generates a summary of the log report using Ollama.
    Saves the output to the Logs folder.
    """
    # 1. System Prep (Assumes Step 3 has already prepared the model)
    print(f"\n🚀 Generative AI running ({style} mode)...")

    # 2. Select Prompt
    if style == "narrative":
        system_prompt = PROMPT_NARRATIVE
        suffix = "narrative"
    else:
        system_prompt = PROMPT_STRUCTURED
        suffix = "structured"

    # 3. Read Report
    if not os.path.exists(report_path):
        return "Error: Report file not found."
    
    try:
        with open(report_path, "r", encoding="utf-8") as f:
            report_content = f.read()
    except Exception as e:
        return f"Error reading report: {e}"
    
    # 4. Generate
    try:
        response = ollama.chat(model=MODEL_NAME, messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': f"Log Analysis Report content:\n{report_content}"},
        ])
        
        summary_text = response['message']['content']
        
        # 5. Save to Logs Folder
        base_dir = os.path.dirname(report_path) # Should be the Logs folder
        output_filename = f"AI_Summary_{suffix}.md"
        output_path = os.path.join(base_dir, output_filename)
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(summary_text)
            
        print(f"✅ Summary saved to: {output_path}")
        return summary_text

    except Exception as e:
        print(f"❌ Generation failed: {e}")
        return f"AI Generation Failed: {str(e)}"

def chat_with_log(report_path, chat_history, user_question):
    """
    Allows the user to chat with the specific log report context.
    chat_history: List of {'role': 'user'/'assistant', 'content': '...'}
    """
    # 1. Read Report Context
    try:
        with open(report_path, "r", encoding="utf-8") as f:
            report_content = f.read()
    except:
        return "Error: Could not read report context."

    # 2. Build Message Chain
    # System prompt injects the report content so the AI knows what to talk about
    messages = [
        {
            'role': 'system', 
            'content': (
                f"You are a helpful AI Assistant analyzing a Linux Log Report. "
                f"Here is the report context:\n\n{report_content}\n\n"
                f"You have an overall understanding of Linux system administration and log analysis. "
                f"Answer the user's questions based ONLY on this report. "
                f"Be concise and technical."
            )
        }
    ]
    
    # Add history (Limit to last 10 messages to save context window if needed)
    messages.extend(chat_history[-10:])
    
    # Add current question
    messages.append({'role': 'user', 'content': user_question})
    
    # 3. Generate Response
    try:
        response = ollama.chat(model=MODEL_NAME, messages=messages)
        return response['message']['content']
    except Exception as e:
        return f"Error: {str(e)}"