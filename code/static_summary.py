import pandas as pd
import textwrap
import os

def write_executive_summary(df_logs, output_path, min_time, max_time, peak_str, peak_vol, total_hours, generic_map, ai_summary_text=""):
    """
    Writes the text-based executive summary.
    Now accepts 'ai_summary_text' to print the BART/Phi-3 generated brief.
    """
    print(f"[SUMMARY] Writing report to {os.path.basename(output_path)}...")
    
    # --- Helper to format top lists ---
    def get_top_3_str(series):
        if series.empty: return "None"
        items = []
        total = len(df_logs)
        for name, count in series.head(3).items():
            pct = (count / total) * 100
            items.append(f"{name} ({count}, {pct:.1f}%)")
        return "; ".join(items)

    # --- Metrics Calculation ---
    total_events = len(df_logs)
    sev_counts = df_logs['Severity'].value_counts()
    crit_count = sev_counts.get('CRITICAL', 0)
    warn_count = sev_counts.get('WARNING', 0)
    
    # Use str.contains to count overlapping tags
    priv_events = df_logs[df_logs['Security_Tag'].str.contains('Privilege Activity', na=False)]
    auth_fails = df_logs[df_logs['Security_Tag'].str.contains('Auth Failure', na=False)]
    success_logins = df_logs[df_logs['Security_Tag'].str.contains('Successful Login', na=False)]
    
    # Security Analyst Insight: Unique IPs
    unique_ips = df_logs[df_logs['RHOST'] != 'N/A']['RHOST'].nunique()
    
    # --- RAREST LOGS LOGIC ---
    template_counts = df_logs['Template ID'].value_counts()
    if not template_counts.empty:
        min_occurrence = template_counts.min()
        rare_template_ids = template_counts[template_counts == min_occurrence].index.tolist()
        rare_count = len(rare_template_ids)
    else:
        min_occurrence = 0
        rare_template_ids = []
        rare_count = 0

    # --- Report Structure ---
    lines = [
        "============================================================",
        "             LOG ANALYSIS REPORT",
        "============================================================",
        f"Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "0. EXECUTIVE BRIEF (AI Generated)",
        "---------------------------------",
        textwrap.fill(ai_summary_text, width=80) if ai_summary_text else "[No AI Summary Generated]",
        "",
        "1. EXECUTIVE OVERVIEW",
        "---------------------",
        f"Analysis Period:      {min_time.strftime('%Y-%b-%d %H:%M')} to {max_time.strftime('%Y-%b-%d %H:%M')}",
        f"Total Log Entries:    {total_events}",
        f"Unique Source IPs:    {unique_ips} (Distinct machines contacting this server)",
        f"Health Status:        {'⚠️ ATTENTION NEEDED' if crit_count > 0 else '✅ STABLE'}",
        "",
        "2. SECURITY AUDIT",
        "---------------------",
        f"🔴 Critical Events:     {crit_count}",
        f"🟠 Warning Events:      {warn_count}",
        f"🔐 Auth Failures:       {len(auth_fails)}",
        f"⚡ Privilege Activity:  {len(priv_events)} (sudo, su, uid=0)",
        f"✅ Successful Logins:   {len(success_logins)}",
        f"🔍 Rare Anomalies:      {rare_count} log types appeared {min_occurrence} time(s) (Least Frequent)",
        "",
        "3. ACTIVITY ANALYSIS",
        "---------------------",
        f"Peak Activity Time:   {peak_str} ({peak_vol} events)",
        f"Avg Event Rate:       {total_events / (total_hours if total_hours > 0 else 1):.1f} events/hour",
        "",
        "4. CRITICAL BREAKDOWN",
        "---------------------",
        f"Top Services:    {get_top_3_str(df_logs['Service'].value_counts())}",
        f"Top Users:       {get_top_3_str(df_logs[df_logs['USERNAME'] != 'N/A']['USERNAME'].value_counts())}",
        f"Top IPs:         {get_top_3_str(df_logs[df_logs['RHOST'] != 'N/A']['RHOST'].value_counts())}",
        ""
    ]

    # --- 5. RISK EVENT HIGHLIGHTS ---
    lines.append("5. RISK EVENT HIGHLIGHTS (Strictly Critical/Warning)")
    lines.append("--------------------------------------------------")
    
    def add_section_content(group_list):
        if not group_list:
            lines.append("✅ None found.")
            return

        for tid, group in group_list:
            if group.empty: continue
            count = len(group)
            row = group.iloc[0]
            
            if count == 1:
                log_content = str(row['Raw Log']).strip()
                meaning_content = str(row['Meaning Log']).strip()
                label = "RAW"
            else:
                if 'Drained Named Log' in df_logs.columns:
                    log_content = str(row['Drained Named Log']).strip()
                else:
                    log_content = str(row['Raw Log']).strip()
                meaning_content = generic_map.get(str(tid), str(row['Meaning Log'])).strip()
                label = "TEMPLATE"

            lines.append(f"   [Count: {count}] Template {tid}")
            lines.append(f"   {label}:    {textwrap.fill(log_content, width=100, subsequent_indent='            ')}")
            lines.append(f"   MEANING: {textwrap.fill(meaning_content, width=100, subsequent_indent='            ')}")
            lines.append("")

    # Add Critical
    if crit_count > 0:
        lines.append(f"🔴 CRITICAL EVENTS:")
        crit_groups = df_logs[df_logs['Severity'] == 'CRITICAL'].groupby('Template ID')
        sorted_crit = sorted(crit_groups, key=lambda x: len(x[1]), reverse=True)
        add_section_content(sorted_crit)
    else:
        lines.append("✅ No Critical events found.")
    
    lines.append("")

    # Add Warning
    if warn_count > 0:
        lines.append(f"🟠 WARNING EVENTS:")
        warn_groups = df_logs[df_logs['Severity'] == 'WARNING'].groupby('Template ID')
        sorted_warn = sorted(warn_groups, key=lambda x: len(x[1]), reverse=True)
        add_section_content(sorted_warn)
    else:
        lines.append("✅ No Warning events found.")

    lines.append("")

    # --- 6. RAREST LOG PATTERNS (New Section) ---
    lines.append(f"6. RAREST LOG PATTERNS (Occurred {min_occurrence} times)")
    lines.append("--------------------------------------------------")
    lines.append("These are the least frequent events, often indicating anomalies or outliers.")
    lines.append("")
    
    # Filter the groups for rare templates
    rare_groups = []
    for tid in rare_template_ids:
        group = df_logs[df_logs['Template ID'] == str(tid)]
        if not group.empty:
            rare_groups.append((tid, group))
            
    # Reuse the display logic
    add_section_content(rare_groups)

    # Write File
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))