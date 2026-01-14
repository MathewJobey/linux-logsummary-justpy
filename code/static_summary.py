import pandas as pd
import textwrap
import os

def write_executive_summary(df_logs, output_path, min_time, max_time, peak_str, peak_vol, total_hours, generic_map):
    """
    Writes the text-based executive summary to the specified path.
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
    
    root_events = df_logs[df_logs['Security_Tag'] == 'Root Activity']
    auth_fails = df_logs[df_logs['Security_Tag'] == 'Auth Failure']
    success_logins = df_logs[df_logs['Security_Tag'] == 'Successful Login']
    
    # --- Report Structure ---
    lines = [
        "============================================================",
        "             LOG ANALYSIS REPORT",
        "============================================================",
        f"Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "1. EXECUTIVE OVERVIEW",
        "---------------------",
        f"Analysis Period:      {min_time.strftime('%Y-%b-%d %H:%M')} to {max_time.strftime('%Y-%b-%d %H:%M')}",
        f"Total Log Entries:    {total_events}",
        f"Health Status:        {'⚠️ ATTENTION NEEDED' if crit_count > 0 else '✅ STABLE'}",
        "",
        "2. SECURITY AUDIT",
        "---------------------",
        f"🔴 Critical Events:     {crit_count} events detected",
        f"🟠 Warning Events:      {warn_count} events detected",
        f"🔐 Auth Failures:       {len(auth_fails)} failed login attempts",
        f"⚡ Root Activity:       {len(root_events)} sessions involving root user",
        f"✅ Successful Logins:   {len(success_logins)} sessions established",
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
    
    def add_risk_section(sev_label, group_list):
        if not group_list:
            lines.append(f"✅ No '{sev_label}' events found.")
        else:
            lines.append(f"{'🔴' if sev_label == 'CRITICAL' else '🟠'} {sev_label} EVENTS ({len(group_list)} types):")
            for tid, group in group_list:
                if group.empty: continue
                count = len(group)
                row = group.iloc[0]
                
                # Logic to show specific log vs generic template
                if count == 1:
                    log_content = str(row['Raw Log']).strip()
                    meaning_content = str(row['Meaning Log']).strip()
                    label_type = "RAW"
                else:
                    if 'Drained Named Log' in df_logs.columns:
                        log_content = str(row['Drained Named Log']).strip()
                    else:
                        log_content = str(row['Raw Log']).strip()
                    
                    # FIX: Use correct variable name 'generic_map'
                    meaning_content = generic_map.get(str(tid), str(row['Meaning Log'])).strip()
                    label_type = "TEMPLATE"

                lines.append(f"   [Count: {count}] Template {tid}")
                lines.append(f"   {label_type}:     {textwrap.fill(log_content, width=100, subsequent_indent='            ')}")
                lines.append(f"   MEANING: {textwrap.fill(meaning_content, width=100, subsequent_indent='            ')}")
                lines.append("")

    # Critical Section
    crit_groups = df_logs[df_logs['Severity'] == 'CRITICAL'].groupby('Template ID')
    sorted_crit = sorted(crit_groups, key=lambda x: len(x[1]), reverse=True)
    add_risk_section("CRITICAL", sorted_crit)
    
    lines.append("")
    
    # Warning Section
    warn_groups = df_logs[df_logs['Severity'] == 'WARNING'].groupby('Template ID')
    sorted_warn = sorted(warn_groups, key=lambda x: len(x[1]), reverse=True)
    add_risk_section("WARNING", sorted_warn)
    
    # Write File
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))