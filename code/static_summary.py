import pandas as pd
import textwrap
import os

def write_executive_summary(df_logs, output_path, min_time, max_time, peak_str, peak_vol, total_hours, generic_map, ai_summary_text="", threat_df=None):
    """
    Writes the text-based executive summary.
    - NO AI Summary at the top.
    - NO Deduplication (Shows all login events).
    - Includes Robust Threat Intelligence (Handles IP+Domain).
    - Triggered time displayed as full Datetime.
    """
    print(f"[SUMMARY] Writing report to {os.path.basename(output_path)}...")
    
    # ==========================================
    # 1. HELPER FUNCTIONS
    # ==========================================
    
    def get_session_analysis(df):
        # Label Events
        def get_event_type(row):
            tag = str(row.get('Security_Tag', ''))
            msg = (str(row.get('Meaning Log', '')) + " " + str(row.get('Raw Log', ''))).lower()
            if 'Successful Login' in tag or 'session opened' in msg or 'accepted password' in msg: return 'LOGIN'
            if 'session closed' in msg or 'logged out' in msg: return 'LOGOUT'
            return None

        df = df.copy()
        df['Event_Type'] = df.apply(get_event_type, axis=1)
        df = df.dropna(subset=['Event_Type']).sort_values(by='datetime')

        if df.empty: return ["No login/logout activity detected."]

        # Match Pairs (No Deduplication)
        user_stacks = {}
        completed = []

        for _, row in df.iterrows():
            user = row.get('USERNAME', 'N/A')
            if user == 'N/A': continue
            evt, ts = row['Event_Type'], row['datetime']

            if evt == 'LOGIN':
                if user not in user_stacks: user_stacks[user] = []
                user_stacks[user].append(ts)
            elif evt == 'LOGOUT':
                if user in user_stacks and user_stacks[user]:
                    start = user_stacks[user].pop()
                    duration = ts - start
                    s = int(duration.total_seconds())
                    h, rem = divmod(s, 3600)
                    m, s = divmod(rem, 60)
                    
                    if h > 0: dur_str = f"{h}h {m}m"
                    elif m > 0: dur_str = f"{m}m {s}s"
                    else: dur_str = f"{s}s"
                    
                    completed.append(f"User '{user}': Logged in for {dur_str} ({start.strftime('%Y-%m-%d %H:%M')} to {ts.strftime('%Y-%m-%d %H:%M')})")

        # Active Sessions
        for user, starts in user_stacks.items():
            for start in starts:
                completed.append(f"User '{user}': 🟢 Active Session (Since {start.strftime('%Y-%m-%d %H:%M')})")

        return completed[-15:] if completed else ["No complete sessions found."]
    
    def get_top_3_str(series):
        if series.empty: return "None"
        items = []
        total = len(df_logs)
        for name, count in series.head(3).items():
            pct = (count / total) * 100
            items.append(f"{name} ({count}, {pct:.1f}%)")
        return "; ".join(items)

    # ==========================================
    # 2. METRICS
    # ==========================================
    total_events = len(df_logs)
    sev_counts = df_logs['Severity'].value_counts()
    crit_count = sev_counts.get('CRITICAL', 0)
    warn_count = sev_counts.get('WARNING', 0)
    
    priv_events = df_logs[df_logs['Security_Tag'].str.contains('Privilege Activity', na=False)]
    auth_fails = df_logs[df_logs['Security_Tag'].str.contains('Auth Failure', na=False)]
    success_logins = df_logs[df_logs['Security_Tag'].str.contains('Successful Login', na=False)]
    unique_ips = df_logs[df_logs['RHOST'] != 'N/A']['RHOST'].nunique()
    
    template_counts = df_logs['Template ID'].value_counts()
    if not template_counts.empty:
        min_occurrence = template_counts.min()
        rare_template_ids = template_counts[template_counts == min_occurrence].index.tolist()
        rare_count = len(rare_template_ids)
    else:
        min_occurrence = 0
        rare_template_ids = []
        rare_count = 0
        
    session_list = get_session_analysis(df_logs)

    # ==========================================
    # 3. BUILD REPORT
    # ==========================================
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
        f"Unique Source IPs:    {unique_ips} (Distinct machines contacting this server)",
        f"Health Status:        {'⚠️ ATTENTION NEEDED' if crit_count > 0 else '✅ STABLE'}",
        "",
        "2. USER SESSION ACTIVITY",
        "------------------------",
        *[f"   • {s}" for s in session_list], 
        "",
        "3. SECURITY AUDIT",
        "---------------------",
        f"🔴 Critical Events:     {crit_count}",
        f"🟠 Warning Events:      {warn_count}",
        f"🔐 Auth Failures:       {len(auth_fails)}",
        f"⚡ Privilege Activity:  {len(priv_events)} (sudo, su, uid=0)",
        f"✅ Successful Logins:   {len(success_logins)}",
        f"🔍 Rare Anomalies:      {rare_count} log types appeared {min_occurrence} time(s) (Least Frequent)",
        "",
        "4. ACTIVITY ANALYSIS",
        "---------------------",
        f"Peak Activity Time:   {peak_str} ({peak_vol} events)",
        f"Avg Event Rate:       {total_events / (total_hours if total_hours > 0 else 1):.1f} events/hour",
        ""
    ]

    # ==========================================
    # 4. APPEND THREAT INTELLIGENCE (SECTION 5)
    # ==========================================
    lines.append("5. THREAT INTELLIGENCE (Fail2Ban Simulation)")
    lines.append("--------------------------------------------------")
    lines.append("Logic: >5 failures within any 10-minute sliding window.")
    lines.append("")

    if threat_df is not None and not threat_df.empty:
        threat_df = threat_df.sort_values('Max_Burst_Rate', ascending=False)
        for _, row in threat_df.iterrows():
            host = row['Target_Host'] 
            # --- FIX: Display as full Datetime (%Y-%m-%d %H:%M:%S) ---
            time = row['Ban_Triggered_At'].strftime('%Y-%m-%d %H:%M:%S')
            burst = row['Max_Burst_Rate']
            total = row['Total_Failures']
            
            lines.append(f"   [🚩 BANNABLE] Host/IP: {host}")
            lines.append(f"      • Triggered At: {time}")
            lines.append(f"      • Burst Rate:   {burst} failures / 10min")
            lines.append(f"      • Total Count:  {total} failures in full log")
            lines.append("")
    else:
        lines.append("   ✅ No IPs triggered the ban threshold.")
        lines.append("")

    # ==========================================
    # 5. REST OF REPORT
    # ==========================================
    lines.extend([
        "6. CRITICAL BREAKDOWN",
        "---------------------",
        f"Top Services:    {get_top_3_str(df_logs['Service'].value_counts())}",
        f"Top Users:       {get_top_3_str(df_logs[df_logs['USERNAME'] != 'N/A']['USERNAME'].value_counts())}",
        f"Top IPs:         {get_top_3_str(df_logs[df_logs['RHOST'] != 'N/A']['RHOST'].value_counts())}",
        ""
    ])

    lines.append("7. RISK EVENT HIGHLIGHTS (Strictly Critical/Warning)")
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

    if crit_count > 0:
        lines.append(f"🔴 CRITICAL EVENTS:")
        crit_groups = df_logs[df_logs['Severity'] == 'CRITICAL'].groupby('Template ID')
        sorted_crit = sorted(crit_groups, key=lambda x: len(x[1]), reverse=True)
        add_section_content(sorted_crit)
    else:
        lines.append("✅ No Critical events found.")
    
    lines.append("")

    if warn_count > 0:
        lines.append(f"🟠 WARNING EVENTS:")
        warn_groups = df_logs[df_logs['Severity'] == 'WARNING'].groupby('Template ID')
        sorted_warn = sorted(warn_groups, key=lambda x: len(x[1]), reverse=True)
        add_section_content(sorted_warn)
    else:
        lines.append("✅ No Warning events found.")

    lines.append("")

    lines.append(f"8. RAREST LOG PATTERNS (Occurred {min_occurrence} times)")
    lines.append("--------------------------------------------------")
    lines.append("These are the least frequent events, often indicating anomalies or outliers.")
    lines.append("")
    
    rare_groups = []
    for tid in rare_template_ids:
        group = df_logs[df_logs['Template ID'] == str(tid)]
        if not group.empty:
            rare_groups.append((tid, group))
            
    add_section_content(rare_groups)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))