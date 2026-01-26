import os
import ollama

# ==========================================
# CONFIGURATION
# ==========================================
MODEL_NAME = "llama3.1:8b"

# ==========================================
# PART 1: INTRO & RISK OVERVIEW
# Content: Intro, Executive Overview, Security Metrics, Risk Highlights
# ==========================================
NARRATIVE_P1 = (
    "You are a Senior Linux System Administrator explaining the Executive Overview of a log analysis report "
    "to a stakeholder in a calm, story-like manner. Write a single flowing paragraph that explains what was reviewed, "
    "when the report was generated, and the time period covered. Then describe the overall system health and why it "
    "was considered stable or critical basically the executive overview section, followed by a simple explanation of the key Security Audit Metrics — such as "
    "critical events, warnings, or authentication failures — and what they indicate in plain language. "
    "End by clearly explaining the most important risk event highlights and why they matter. "
    "Keep the explanation easy to follow and avoid technical depth; inline emphasis may be used. "
    "Keep at Maximum of 100 words."
)


STRUCTURED_P1 = (
    "You are a Senior System Administrator generating the first section of a log analysis report in markdown.\n\n"

    "BEGIN with one sentence stating the report is auto-generated and clearly mention the analysis timeframe.\n\n"

    "### Executive Overview\n"
    "- System health: <Stable|Critical>\n"
    "- Primary reason: <brief reason>\n"
    "- Total log events: <number>\n\n"

    "### Security Audit Matrix\n"
    "- Critical events: <number>\n"
    "- Warning events: <number>\n"
    "- Authentication failures: <number>\n\n"

    "### Risk Event Highlights\n"
    "- High-risk event: <description> (occurrences: <number>)\n"
    "- Affected component/process: <name>\n\n"

    "CONSTRAINTS:\n"
    "- Use only Executive Overview, Security Audit Matrix, and Risk Event data.\n"
    "- Include exact numeric values from the report.\n"
    "- Be precise, technical, and concise.\n"
    "- Maximum 100 words."
)


# ==========================================
# PART 2: THREAT INTELLIGENCE
# Content: Threat Intelligence (Fail2Ban Candidates)
# ==========================================
NARRATIVE_P2 = (
    "You are a Senior Linux System Administrator continuing the report explanation by talking only about "
    "Threat Intelligence derived from Fail2Ban-style analysis. Write a single, easy-to-follow paragraph that "
    "explains what kind of hostile or suspicious activity was observed, such as repeated login failures or "
    "automated attempts, and how this behavior was identified. Describe the situation as a story — who or what "
    "was being targeted, how often it happened, and what it suggests about external attack pressure — using "
    "clear, non-technical language. You may highlight a few representative IP addresses or user accounts inline "
    "for clarity, but avoid deep technical detail. Do NOT discuss system health, user sessions, or risk events. "
    "Do NOT conclude. Maximum 100 words."
)


STRUCTURED_P2 = (
    "You are a Senior System Administrator summarizing Threat Intelligence findings strictly from the "
    "Fail2Ban Candidates table.\n\n"

    "### High-Intensity Attack Sources\n"
    "- IP/Host: <ip_or_host> | Burst/10min: <number> | Total failures: <number> | First trigger: <timestamp>\n"
    "- IP/Host: <ip_or_host> | Burst/10min: <number> | Total failures: <number> | First trigger: <timestamp>\n\n"

    "### Attack Characteristics\n"
    "- Peak burst rate observed: <max_burst>/10min\n"
    "- Highest total failure count: <number>\n"
    "- Distinct attacking sources identified: <count>\n\n"

    "CONSTRAINTS:\n"
    "- Use ONLY values present in the Fail2Ban Candidates table.\n"
    "- Copy IPs/hosts, timestamps, burst rates, and totals exactly.\n"
    "- No assumptions, no interpretation beyond numeric facts.\n"
    "- Maximum 100 words."
)


# ==========================================
# PART 3: USER SESSION ACTIVITY
# Content: User Session Activity
# ==========================================
NARRATIVE_P3 = (
    "You are a Senior Linux System Administrator continuing the explanation by describing User Session Activity "
    "in a clear, story-like way. Write one flowing paragraph explaining how the system was accessed by legitimate "
    "users over time. Describe which users appeared most frequently, when their sessions usually occurred, and "
    "what stood out about the session behavior — such as very short logins or repeated access at consistent times. "
    "Explain what this suggests in plain language, without diving into technical mechanisms. You may highlight "
    "specific users inline for clarity."
    "Maximum 100 words."
)


STRUCTURED_P3 = (
    "You are a Senior System Administrator summarizing User Session Activity strictly from the User Session table.\n\n"

    "### Session Summary\n"
    "- Total distinct users: <number>\n"
    "- Total recorded sessions: <number>\n"
    "- Primary authentication process: <process>\n\n"

    "### User-Level Activity\n"
    "- User: <username> | Sessions: <count> | Typical duration: <duration>\n"
    "- User: <username> | Sessions: <count> | Typical duration: <duration>\n\n"

    "### Timing Characteristics\n"
    "- Common access window: <HH:MM range>\n"
    "- Sessions with zero duration: <count>\n\n"

    "CONSTRAINTS:\n"
    "- Use ONLY data from the User Session Activity table.\n"
    "- Copy counts, users, durations, and processes exactly.\n"
    "- Do not infer intent or security risk.\n"
    "- Maximum 100 words."
)


# ==========================================
# PART 4: ANOMALIES & BREAKDOWN
# Content: Rare Log Patterns, Critical Breakdown
# ==========================================
NARRATIVE_P4 = (
    "You are a Senior Linux System Administrator concluding the explanation by briefly discussing rare but noteworthy "
    "system events and overall activity concentration. Write one clear paragraph explaining that a small number of "
    "unusual log entries appeared only once, such as unexpected login attempts, unusual terminal input, legacy remote "
    "service connections, or system-level warnings, and describe why they stand out without reading raw logs. Then "
    "summarize the critical breakdown section like where did most activity was concentrated by explaining which services, users, and external sources appeared "
    "most frequently overall. Keep the language simple and explanatory, avoiding technical depth. "
    "End with this exact italicized line: *Further detailed info can be found in the Log_Analysis_Report.md file.* "
    "Maximum 100 words."
)
STRUCTURED_P4 = (
    "You are a Senior System Administrator summarizing Rare Log Patterns and the Critical Breakdown "
    "section of a log analysis report in markdown.\n\n"

    "### Notable Rare Log Patterns\n"
    "- Number of distinct rare templates observed: <count>\n"
    "- Occurrence pattern: <e.g., single occurrence per template>\n"
    "- Services involved: <comma-separated list of services>\n\n"

    "### Critical Breakdown\n"
    "- Top services by log volume:\n"
    "  - <service_name>: <event_count> events (<percentage>)\n"
    "  - <service_name>: <event_count> events (<percentage>)\n\n"
    "- Top users:\n"
    "  - <username>: <event_count> events (<percentage>)\n"
    "  - <username>: <event_count> events (<percentage>)\n\n"
    "- Top IPs or hosts:\n"
    "  - <ip_or_hostname>: <event_count> events (<percentage>)\n"
    "  - <ip_or_hostname>: <event_count> events (<percentage>)\n\n"

    "END with this exact footer in italics:\n"
    "*Further detailed info can be found in the Log_Analysis_Report.md file.*\n\n"

    "CONSTRAINTS:\n"
    "- Use ONLY Rare Log Patterns and Critical Breakdown data.\n"
    "- Replace placeholders with exact values from the report.\n"
    "- Do not invent, infer, or generalize data.\n"
    "- No interpretation or recommendations.\n"
    "- Maximum 100 words."
)

# ==========================================
# AI FUNCTIONS
# ==========================================

def generate_summary(report_path, style="structured"):
    """
    Splits the report into 4 chunks to ensure detailed coverage of Threats and Sessions.
    """
    print(f"\n🚀 Generative AI running ({style} mode - 4-Way Split Strategy)...")

    # 1. Read Report
    if not os.path.exists(report_path):
        return "Error: Report file not found."
    
    try:
        with open(report_path, "r", encoding="utf-8") as f:
            full_content = f.read()
    except Exception as e:
        return f"Error reading report: {e}"

    # 2. INTELLIGENT 4-WAY SPLIT
    # Markers based on static_report.py structure
    m1 = "## 4. Threat Intelligence"
    m2 = "## 5. User Session Activity"
    m3 = "## 6. Rare Log Patterns"

    try:
        # Split 1: Isolate Part 1 (Start to Threat Intel)
        # Covers: Intro, Executive Overview, Security Metrics, Risk Highlights
        if m1 in full_content:
            part1_text, rest1 = full_content.split(m1, 1)
            rest1 = m1 + rest1 
        else:
            part1_text = full_content
            rest1 = ""

        # Split 2: Isolate Part 2 (Threat Intel to User Session)
        # Covers: Threat Intelligence
        if m2 in rest1:
            part2_text, rest2 = rest1.split(m2, 1)
            rest2 = m2 + rest2
        else:
            part2_text = rest1
            rest2 = ""

        # Split 3: Isolate Part 3 (User Session to Rare Patterns)
        # Covers: User Session Activity
        if m3 in rest2:
            part3_text, rest3 = rest2.split(m3, 1)
            part4_text = m3 + rest3 # Part 4 is the remainder
        else:
            part3_text = rest2
            part4_text = ""
            
        # Part 4 Covers: Rare Log Patterns, Critical Breakdown

    except Exception as e:
        print(f"[WARN] Split failed ({e}), falling back to single pass.")
        part1_text = full_content
        part2_text = ""
        part3_text = ""
        part4_text = ""

    # 3. Select Prompts
    if style == "narrative":
        p1, p2, p3, p4 = NARRATIVE_P1, NARRATIVE_P2, NARRATIVE_P3, NARRATIVE_P4
    else:
        p1, p2, p3, p4 = STRUCTURED_P1, STRUCTURED_P2, STRUCTURED_P3, STRUCTURED_P4

    # 4. RUN INFERENCE (4 separate calls)
    final_parts = []
    
    # --- PASS 1: Overview ---
    if part1_text.strip():
        print("   -> Processing Part 1 (Overview & Risks)...")
        r1 = ollama.chat(model=MODEL_NAME, messages=[
            {'role': 'system', 'content': p1},
            {'role': 'user', 'content': part1_text}
        ])
        final_parts.append(r1['message']['content'].strip())

    # --- PASS 2: Threats ---
    if part2_text.strip():
        print("   -> Processing Part 2 (Threat Intelligence)...")
        r2 = ollama.chat(model=MODEL_NAME, messages=[
            {'role': 'system', 'content': p2},
            {'role': 'user', 'content': part2_text}
        ])
        final_parts.append(r2['message']['content'].strip())

    # --- PASS 3: Sessions ---
    if part3_text.strip():
        print("   -> Processing Part 3 (User Sessions)...")
        r3 = ollama.chat(model=MODEL_NAME, messages=[
            {'role': 'system', 'content': p3},
            {'role': 'user', 'content': part3_text}
        ])
        final_parts.append(r3['message']['content'].strip())

    # --- PASS 4: Anomalies ---
    if part4_text.strip():
        print("   -> Processing Part 4 (Anomalies & Stats)...")
        r4 = ollama.chat(model=MODEL_NAME, messages=[
            {'role': 'system', 'content': p4},
            {'role': 'user', 'content': part4_text}
        ])
        final_parts.append(r4['message']['content'].strip())

    # 5. COMBINE
    final_summary = "\n\n".join(final_parts)
    
    # Save
    base_dir = os.path.dirname(report_path)
    output_filename = f"AI_Summary_{style}.md"
    output_path = os.path.join(base_dir, output_filename)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(final_summary)
        
    print(f"✅ Summary saved to: {output_path}")
    return final_summary

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