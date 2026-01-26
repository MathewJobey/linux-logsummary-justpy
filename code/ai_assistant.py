import os
import ollama

# ==========================================
# CONFIGURATION
# ==========================================
MODEL_NAME = "llama3.1:8b"

# ==========================================
# PART 1 PROMPTS (Security Core)
# Sections: Executive Overview, Security Metrics, Risk Highlights, Threat Intel
# ==========================================

NARRATIVE_P1 = (
    "You are a Senior Linux System Administrator explaining a log analysis report to a technical stakeholder.\n"
    "Write as if you are speaking naturally, not reading from a report.\n\n"
    "**FOCUS AREAS:** Executive Overview, Security Audit Metrics, Risk Event Highlights, Threat Intelligence.\n\n"
    "**INSTRUCTIONS:**\n"
    "1. Begin immediately by stating when the report was generated and the timeframe the logs cover. "
    "Then smoothly transition into explaining the executive overview and its key findings in your own words.\n"
    "2. Continue into the security audit metrics, explaining what the numbers indicate rather than restating them.\n"
    "3. Discuss the risk event highlights, especially critical and warning-level events, clearly explaining what they mean and why they matter.\n"
    "4. Summarize the threat intelligence by mentioning a few notable attacking IPs, domains, brute-force attempts, and authentication failures, "
    "adding your professional interpretation.\n"
    "5. Maintain a single, flowing narrative.\n"
    "6. Do not quote or copy sentences directly from the report.\n"
    "7. Do not write a conclusion, summary, or closing statement. Stop naturally after the threat intelligence discussion."
    "8. The entire response must be **150 words or fewer**. Be concise without losing meaning."
)

STRUCTURED_P1 = (
    "You are a Senior System Administrator generating a professional server log analysis report.\n"
    "The report must be concise, structured, and suitable for executive and security review.\n\n"

    "BEGIN with a static opening line stating that the report is auto-generated.\n"
    "Clearly mention the log analysis timeframe (start timestamp to end timestamp).\n\n"

    "### Executive Overview\n"
    "Provide a high-level summary of overall system health and security posture.\n\n"
    "State the system status (Stable or Critical) and the total log event volume.\n"
    "Mention only key operational observations.\n\n"

    "### Security Audit Matrix\n"
    "Summarize only the most important security findings.\n"
    "Avoid listing all metrics; focus on admin-relevant issues.\n\n"

    "### Risk Event Highlights\n"
    "Highlight high-risk or abnormal events.\n"
    "Briefly explain involved processes or activities with technical precision.\n\n"

    "### Threat Intelligence Analysis\n"
    "Analyze threat intelligence data such as attacking IPs, authentication abuse, and patterns.\n"
    "Provide analytical insights rather than raw statistics.\n\n"

    "CONSTRAINTS:\n"
    "- Maximum 150 words total.\n"
    "- Use Markdown headers.\n"
    "- Professional, clear, and non-repetitive language.\n"
)


# ==========================================
# PART 2 PROMPTS (Operations & Activity)
# Sections: User Session Activity, Rare Log Patterns, Critical Breakdown
# ==========================================

NARRATIVE_P2 = (
    "You are a Senior Linux System Administrator explaining a log analysis report to a non-technical stakeholder in simple, clear language.\n\n"
    "**FOCUS AREAS:** User Session Activity, Rare Log Patterns, Critical Breakdown.\n\n"
    "**INSTRUCTIONS:**\n"
    "1. Begin the narrative naturally by describing the User Session Activity section like who logged in, notable commands or services used, and any repeated login attempts plus what you inferred from them. "
    "Briefly highlight a few specific users and patterns you observed; do not attempt to cover everything.\n"
    "2. Move on to the Rare Log Patterns only if they represent a meaningful anomaly. Explain their significance in plain language instead of copying text from the report.\n"
    "3. Finally use the Critical Breakdown section to emphasize the most impactful services, users, or IP addresses and what you understood from them.\n"
    "4. Maintain a smooth, continuous narrative without section headers or bullet points.\n"
    "5. Do not include raw log lines, metrics tables, or timestamps.\n"
    "6. The entire response must be **150 words or fewer**. Be concise without losing meaning."
    "7. End with the following footer exactly as written, in italics:\n"
    "*Further detailed info can be found in the Log_Analysis_Report.md file.*"
)


STRUCTURED_P2 = (
    "You are a Senior System Administrator generating an operational analysis report of the server.\n"
    "The report must focus on usage behavior, service activity, and operational patterns.\n\n"

    "### User Activity\n"
    "Summarize legitimate user sessions, login behavior, and services accessed.\n"
    "Focus on normal operational usage rather than security threats. provide few of the users and their patterns of usage.\n\n"

    "### Notable Anomalies\n"
    "Briefly mention rare, unusual, or unexpected operational log patterns if relevant.\n"
    "Do not speculate; state observations only.\n\n"

    "### Top Operational Statistics\n"
    "Mention top users, services, or processes based on the Critical Breakdown.\n"
    "Highlight only the most operationally significant items.\n\n"

    "END the report with this exact footer in italics:\n"
    "*Further detailed info can be found in the Log_Analysis_Report.md file.*\n\n"

    "CONSTRAINTS:\n"
    "- Maximum 150 words total.\n"
    "- Use Markdown headers.\n"
    "- Professional, concise, and non-repetitive language.\n"
)


# ==========================================
# AI FUNCTIONS
# ==========================================

def generate_summary(report_path, style="structured"):
    """
    Splits the report into two chunks to prevent 'Recency Bias', 
    processes them separately, and combines the result.
    """
    print(f"\n🚀 Generative AI running ({style} mode - Split Strategy)...")

    # 1. Read Report
    if not os.path.exists(report_path):
        return "Error: Report file not found."
    
    try:
        with open(report_path, "r", encoding="utf-8") as f:
            full_content = f.read()
    except Exception as e:
        return f"Error reading report: {e}"

    # 2. INTELLIGENT SPLIT (The "Map" Step)
    # Splitting exactly where Part 2 begins: Section 5
    split_marker = "## 5. User Session Activity"
    
    if split_marker in full_content:
        parts = full_content.split(split_marker)
        chunk_security = parts[0] # Contains Sections 1, 2, 3, 4
        chunk_operations = split_marker + parts[1] # Contains Sections 5, 6, 7
    else:
        # Fallback if marker is missing
        midpoint = len(full_content) // 2
        chunk_security = full_content[:midpoint]
        chunk_operations = full_content[midpoint:]

    # 3. Select Prompts
    if style == "narrative":
        prompt_p1 = NARRATIVE_P1
        prompt_p2 = NARRATIVE_P2
    else:
        prompt_p1 = STRUCTURED_P1
        prompt_p2 = STRUCTURED_P2

    # 4. RUN INFERENCE (Two separate calls)
    try:
        # --- PASS 1: Security & Health ---
        print("   -> Processing Part 1 (Security Core)...")
        response_1 = ollama.chat(model=MODEL_NAME, messages=[
            {'role': 'system', 'content': prompt_p1},
            {'role': 'user', 'content': f"Report Part 1:\n{chunk_security}"},
        ])
        text_part_1 = response_1['message']['content'].strip()

        # --- PASS 2: Operations & Activity ---
        print("   -> Processing Part 2 (User Activity)...")
        response_2 = ollama.chat(model=MODEL_NAME, messages=[
            {'role': 'system', 'content': prompt_p2},
            {'role': 'user', 'content': f"Report Part 2:\n{chunk_operations}"},
        ])
        text_part_2 = response_2['message']['content'].strip()

        # 5. COMBINE (The "Reduce" Step)
        # Add a newline separator between the two parts
        final_summary = f"{text_part_1}\n\n{text_part_2}"
        
        # Save
        base_dir = os.path.dirname(report_path)
        output_filename = f"AI_Summary_{style}.md"
        output_path = os.path.join(base_dir, output_filename)
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(final_summary)
            
        print(f"✅ Summary saved to: {output_path}")
        return final_summary

    except Exception as e:
        print(f"❌ Generation failed: {e}")
        return f"AI Generation Failed: {str(e)}"

def chat_with_log(report_path, chat_history, user_question):
    """
    Allows the user to chat with the specific log report context.
    """
    try:
        with open(report_path, "r", encoding="utf-8") as f:
            report_content = f.read()
    except:
        return "Error: Could not read report context."

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
    
    messages.extend(chat_history[-10:])
    messages.append({'role': 'user', 'content': user_question})
    
    try:
        response = ollama.chat(model=MODEL_NAME, messages=messages)
        return response['message']['content']
    except Exception as e:
        return f"Error: {str(e)}"