import pandas as pd
import datetime
import json

def format_duration(seconds):
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, s = divmod(rem, 60)
    if h > 0: return f"{h}h {m}m"
    if m > 0: return f"{m}m {s}s"
    return f"{s}s"

def detect_event_type(row):
    tag = str(row.get('Security_Tag', ''))
    msg = (str(row.get('Meaning Log', '')) + " " + str(row.get('Raw Log', ''))).lower()
    
    if 'Successful Login' in tag: return 'LOGIN'
    if 'session opened' in msg: return 'LOGIN'
    if 'accepted password' in msg or 'accepted publickey' in msg: return 'LOGIN'
    
    if 'session closed' in msg: return 'LOGOUT'
    if 'logged out' in msg: return 'LOGOUT' 
    return None

def analyze_sessions(df):
    """
    Scans for Login/Logout pairs. 
    CRITICAL: Does NOT re-sort by time. Trusts the order provided (Original Log Order).
    """
    df = df.copy()
    df['Event_Type'] = df.apply(detect_event_type, axis=1)
    
    # [FIX] REMOVED .sort_values(by='datetime')
    # We strictly respect the order from step_2_sort_logs
    df_events = df.dropna(subset=['Event_Type'])

    if df_events.empty:
        return ["- No login/logout activity detected."]

    open_sessions = {} 
    completed_sessions = []
    
    for _, row in df_events.iterrows():
        try:
            raw_params = row.get('Parameters', '{}')
            if pd.isna(raw_params): raw_params = '{}'
            params = json.loads(str(raw_params))
        except:
            params = {}
        
        pid = str(params.get('PID', 'Unknown'))
        user = params.get('USERNAME')
        if not user: user = row.get('USERNAME', 'N/A')

        ts = row['datetime']
        service = row.get('Service', 'Unknown')
        evt = row['Event_Type']

        if pid == 'Unknown': continue

        # Matching Key: PID only (Unique per session)
        session_key = pid

        if evt == 'LOGIN':
            if user == 'N/A': continue 
            if session_key not in open_sessions:
                open_sessions[session_key] = []
            
            open_sessions[session_key].append({
                'start': ts,
                'user': user,
                'service': service
            })

        elif evt == 'LOGOUT':
            if session_key in open_sessions and open_sessions[session_key]:
                session_data = open_sessions[session_key].pop()
                start_time = session_data['start']
                
                # Calculate duration
                duration_sec = (ts - start_time).total_seconds()
                
                completed_sessions.append({
                    'user': session_data['user'],
                    'service': session_data['service'],
                    'start': start_time,
                    'end': ts,
                    'duration_str': format_duration(duration_sec),
                    'status': 'Closed'
                })

    # Active Sessions
    now = df['datetime'].max() if not df.empty else pd.Timestamp.now()
    for pid, sessions in open_sessions.items():
        for s in sessions:
            start = s['start']
            hours_open = (now - start).total_seconds() / 3600
            status_label = "🟢 Active" if hours_open < 24 else "⚠️ Stale (>24h)"

            completed_sessions.append({
                'user': s['user'],
                'service': s['service'],
                'start': start,
                'end': None,
                'duration_str': status_label,
                'status': 'Active'
            })

    # Format Table
    if not completed_sessions:
        return ["- No complete sessions found."]

    grouped_data = {}
    for sess in completed_sessions:
        key = (sess['user'], sess['service'])
        if key not in grouped_data: grouped_data[key] = []
        grouped_data[key].append(sess)

    table_lines = []
    table_lines.append("| User | Count | Process | Timeframes (Start ➝ End) | Duration |")
    table_lines.append("| :--- | :---: | :--- | :--- | :--- |")

    for (user, service), sessions in grouped_data.items():
        # Sort by start time ONLY for display purposes
        sessions.sort(key=lambda x: x['start'])
        
        timeframe_lines = []
        duration_lines = []
        
        for s in sessions:
            start_str = s['start'].strftime('%Y-%m-%d %H:%M:%S')
            if s['end']:
                end_str = s['end'].strftime('%Y-%m-%d %H:%M:%S')
                timeframe_lines.append(f"{start_str} ➝ {end_str}")
            else:
                timeframe_lines.append(f"{start_str} ➝ ...")
            duration_lines.append(s['duration_str'])

        timeframe_cell = "<br>".join(timeframe_lines)
        duration_cell = "<br>".join(duration_lines)
        table_lines.append(f"| **{user}** | {len(sessions)} | `{service}` | {timeframe_cell} | {duration_cell} |")

    return table_lines