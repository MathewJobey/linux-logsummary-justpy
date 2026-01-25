import pandas as pd
import textwrap
import os
from session_logic import analyze_sessions

def write_executive_report(df_logs, output_path, min_time, max_time, peak_str, peak_vol, total_hours, generic_map, threat_df=None):
    print(f"[REPORT] Writing grid-aligned report to {os.path.basename(output_path)}...")

    # ==========================================
    # 1. HELPER: DYNAMIC TABLE FORMATTER
    # ==========================================
    def format_table(headers, rows):
        """
        Takes headers (list) and rows (list of lists).
        Returns a list of strings representing a perfectly aligned Markdown table.
        """
        if not rows:
            return []
            
        # 1. Calculate max width for each column
        col_widths = [len(h) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                width = len(str(cell))
                if width > col_widths[i]:
                    col_widths[i] = width

        # 2. Add a buffer (2 spaces) for readability
        col_widths = [w + 2 for w in col_widths]

        # 3. Create format string (e.g., "| {:<20} | {:<10} |")
        row_fmt = "| " + " | ".join([f"{{:<{w}}}" for w in col_widths]) + " |"
        
        # 4. Build the table parts
        lines = []
        lines.append(row_fmt.format(*headers))
        
        # Separator (e.g., "| :------------------- | :--------- |")
        separator = "| " + " | ".join([f":{'-' * (w-1)}" for w in col_widths]) + " |"
        lines.append(separator)
        
        # Data Rows
        for row in rows:
            lines.append(row_fmt.format(*[str(r) for r in row]))
            
        return lines

    """# ==========================================
    # 2. HELPER: ANALYSIS FUNCTIONS
    # ==========================================
    def get_session_analysis(df):
        # 1. Label Events
        def get_event_type(row):
            tag = str(row.get('Security_Tag', ''))
            msg = (str(row.get('Meaning Log', '')) + " " + str(row.get('Raw Log', ''))).lower()
            if 'Successful Login' in tag or 'session opened' in msg or 'accepted password' in msg: return 'LOGIN'
            if 'session closed' in msg or 'logged out' in msg: return 'LOGOUT'
            return None

        df = df.copy()
        df['Event_Type'] = df.apply(get_event_type, axis=1)
        df = df.dropna(subset=['Event_Type']).sort_values(by='datetime')

        if df.empty: return ["- No login/logout activity detected."]

        # [CHANGE 1] Dictionary key is now (User, Service) instead of just User
        # This ensures 'sshd' events never mix with 'login' or 'su' events
        session_stacks = {} 
        completed = []
        
        # Trackers for deduplication (also keyed by User+Service)
        last_login_map = {} 
        last_logout_map = {}
        DEDUPE_WINDOW = 5 # seconds

        for _, row in df.iterrows():
            user = row.get('USERNAME', 'N/A')
            # [CHANGE 2] Fetch the Service Name (e.g., sshd, login, su)
            service = row.get('Service', 'Unknown') 
            
            if user == 'N/A': continue
            
            # Create a unique identity for this session stream
            stack_key = (user, service)
            
            evt, ts = row['Event_Type'], row['datetime']

            if evt == 'LOGIN':
                # Debounce: Only ignore if SAME user on SAME service logs in twice quickly
                last_time = last_login_map.get(stack_key)
                if last_time and (ts - last_time).total_seconds() < DEDUPE_WINDOW:
                    continue 
                
                last_login_map[stack_key] = ts
                if stack_key not in session_stacks: session_stacks[stack_key] = []
                session_stacks[stack_key].append(ts)

            elif evt == 'LOGOUT':
                # Debounce Logout
                last_time = last_logout_map.get(stack_key)
                if last_time and (ts - last_time).total_seconds() < DEDUPE_WINDOW:
                    continue

                last_logout_map[stack_key] = ts

                # Pop from the SPECIFIC service stack
                if stack_key in session_stacks and session_stacks[stack_key]:
                    start = session_stacks[stack_key].pop()
                    
                    # Calculate duration
                    duration = ts - start
                    s = int(duration.total_seconds())
                    h, rem = divmod(s, 3600)
                    m, s = divmod(rem, 60)
                    
                    if h > 0: dur_str = f"{h}h {m}m"
                    elif m > 0: dur_str = f"{m}m {s}s"
                    else: dur_str = f"{s}s"
                    
                    # [CHANGE 3] Include Service Name in report so you know which is which
                    completed.append(f"- **User '{user}'** ({service}): Logged in for {dur_str} ({start.strftime('%Y-%m-%d %H:%M')} to {ts.strftime('%Y-%m-%d %H:%M')})")

        # Active Sessions (Process Stale/Active)
        import datetime
        if not df['datetime'].empty:
            now = df['datetime'].max()
        else:
            now = pd.Timestamp.now()

        for stack_key, starts in session_stacks.items():
            user, service = stack_key
            for start in starts:
                duration_hours = (now - start).total_seconds() / 3600
                
                # Check for "Zombie" sessions (older than 24 hours)
                if duration_hours < 24:
                    status_icon = "🟢 Active Session"
                else:
                    status_icon = "⚠️ Stale Session (No Logout)"

                completed.append(f"- **User '{user}'** ({service}): {status_icon} (Since {start.strftime('%Y-%m-%d %H:%M')})")

        # Increase limit to 50 (or remove the slice [:] entirely to see everything)
        return completed[-25:] if completed else ["- No complete sessions found."]"""
    
    def get_top_3_str(series):
        if series.empty: return "None"
        items = []
        total = len(df_logs)
        for name, count in series.head(3).items():
            pct = (count / total) * 100
            items.append(f"`{name}` ({count}, {pct:.1f}%)")
        return "; ".join(items)

    def add_risk_content(lines_list, group_list, severity_label):
        if not group_list:
            lines_list.append(f"> ✅ No {severity_label} events.")
            return

        lines_list.append(f"### {severity_label} Events Details")
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
                
                # 1. Get the generic template (with <LABELS>)
                raw_meaning = generic_map.get(str(tid), str(row['Meaning Log'])).strip()
                
                # 2. Escape the brackets so HTML displays "<TIMESTAMP>" instead of hiding it
                meaning_content = raw_meaning.replace("<", "&lt;").replace(">", "&gt;")
                
                label = "TEMPLATE"

            lines_list.append(f"### Template ID: {tid} (Count: {count})")
            lines_list.append(f"- **{label}**: `{log_content}`")
            lines_list.append(f"- **Meaning**: {meaning_content}")
            lines_list.append("")

    # ==========================================
    # 3. PREPARE METRICS
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
        min_occurrence, rare_template_ids, rare_count = 0, [], 0
        
    session_list = analyze_sessions(df_logs)
    avg_rate = total_events / (total_hours if total_hours > 0 else 1)

    # ==========================================
    # 4. BUILD REPORT STRUCTURE
    # ==========================================
    lines = []
    # Centered report title + generated timestamp (italic)
    report_date = pd.Timestamp.now()

    # Use HTML <h1> to get the size of '#' but with centering
    lines.append('<h1 style="text-align: center; font-size: 40px; margin-bottom: 5px;">Log Analysis Report</h1>')
    lines.append(f'<div style="text-align: center; font-size: 16px; color: #555;"><i>Generated: {report_date.strftime("%Y-%m-%d %H:%M:%S")}</i></div>')

    lines.append("")
    
    # --- 1. Executive Overview ---
    lines.append("## 1. Executive Overview")
    lines.append(f"- **Analysis Period:** {min_time.strftime('%Y-%m-%d %H:%M')} to {max_time.strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"- **Health Status:** {'⚠️ CRITICAL' if crit_count > 0 else '✅ STABLE'}")
    lines.append(f"- **Total Events:** {total_events}")
    lines.append(f"- **Unique IPs:** {unique_ips}")
    lines.append(f"- **Peak Activity:** {peak_str} ({peak_vol} events)")
    lines.append(f"- **Avg Rate:** {avg_rate:.1f} events/hour")
    lines.append("")

    # --- 2. Security Audit (Dynamic Table) ---
    lines.append("## 2. Security Audit Metrics")
    sec_headers = ["Metric", "Count"]
    sec_rows = [
        ["🔴 Critical Events", crit_count],
        ["🟠 Warning Events", warn_count],
        ["🔐 Auth Failures", len(auth_fails)],
        ["⚡ Privilege Activity", len(priv_events)],
        ["✅ Successful Logins", len(success_logins)],
        ["🔍 Rare Anomalies", rare_count]
    ]
    lines.extend(format_table(sec_headers, sec_rows))
    lines.append("")

    # --- 3. Risk Event Highlights ---
    lines.append("## 3. Risk Event Highlights")
    if crit_count > 0:
        crit_groups = sorted(df_logs[df_logs['Severity'] == 'CRITICAL'].groupby('Template ID'), key=lambda x: len(x[1]), reverse=True)
        add_risk_content(lines, crit_groups, "🔴 Critical")
    else:
        lines.append("> ✅ No Critical events.")

    if warn_count > 0:
        warn_groups = sorted(df_logs[df_logs['Severity'] == 'WARNING'].groupby('Template ID'), key=lambda x: len(x[1]), reverse=True)
        add_risk_content(lines, warn_groups, "🟠 Warning")
    else:
        lines.append("> ✅ No Warning events.")
    lines.append("")
    
    # --- 4. Threat Intelligence (Dynamic Table) ---
    lines.append("## 4. Threat Intelligence (Fail2Ban Candidates)")
    if threat_df is not None and not threat_df.empty:
        threat_df = threat_df.sort_values('Max_Burst_Rate', ascending=False)
        threat_headers = ["IP/Host", "Trigger Time", "Burst/10min", "Total Failures"]
        threat_rows = []
        
        for _, row in threat_df.iterrows():
            threat_rows.append([
                str(row['Target_Host']),
                row['Ban_Triggered_At'].strftime('%Y-%m-%d %H:%M:%S'),
                f"{row['Max_Burst_Rate']}",
                f"{row['Total_Failures']}"
            ])
            
        lines.extend(format_table(threat_headers, threat_rows))
    else:
        lines.append("> ✅ No automated attacks detected.")
    lines.append("")

    # --- 5. User Session Activity ---
    lines.append("## 5. User Session Activity")
    lines.extend(session_list)
    lines.append("")

    # --- 6. Rare Patterns ---
    lines.append(f"## 6. Rare Log Patterns (Occurred {min_occurrence} times)")
    rare_groups = []
    for tid in rare_template_ids:
        group = df_logs[df_logs['Template ID'] == str(tid)]
        if not group.empty:
            rare_groups.append((tid, group))
            
    add_risk_content(lines, rare_groups, "🔍 Rare")
    lines.append("")

    # --- 7. Critical Breakdown ---
    lines.append("## 7. Critical Breakdown")
    lines.append(f"- **Top Services:** {get_top_3_str(df_logs['Service'].value_counts())}")
    lines.append(f"- **Top Users:** {get_top_3_str(df_logs[df_logs['USERNAME'] != 'N/A']['USERNAME'].value_counts())}")
    lines.append(f"- **Top IPs:** {get_top_3_str(df_logs[df_logs['RHOST'] != 'N/A']['RHOST'].value_counts())}")

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))