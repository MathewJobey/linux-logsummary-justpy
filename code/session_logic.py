import pandas as pd
import datetime

def format_duration(seconds):
    """Converts seconds into a readable string (e.g., '2h 15m' or '45s')."""
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, s = divmod(rem, 60)
    
    if h > 0: return f"{h}h {m}m"
    if m > 0: return f"{m}m {s}s"
    return f"{s}s"

def detect_event_type(row):
    """
    Determines if a log line is a LOGIN, LOGOUT, or None.
    """
    tag = str(row.get('Security_Tag', ''))
    msg = (str(row.get('Meaning Log', '')) + " " + str(row.get('Raw Log', ''))).lower()
    
    # LOGIN Detection
    if 'Successful Login' in tag: return 'LOGIN'
    if 'session opened' in msg: return 'LOGIN'
    if 'accepted password' in msg or 'accepted publickey' in msg: return 'LOGIN'
    
    # LOGOUT Detection
    if 'session closed' in msg: return 'LOGOUT'
    # 'logged out' is risky if it appears in chat logs, but fine for syslogs/auth logs
    if 'logged out' in msg: return 'LOGOUT' 
    
    return None

def analyze_sessions(df):
    """
    Scans the dataframe for Login/Logout pairs and returns a formatted 
    Markdown table grouped by User and Process.
    """
    # 1. Prepare Data
    df = df.copy()
    df['Event_Type'] = df.apply(detect_event_type, axis=1)
    
    # Filter only relevant events and sort chronologically
    df_events = df.dropna(subset=['Event_Type']).sort_values(by='datetime')

    if df_events.empty:
        return ["- No login/logout activity detected."]

    # 2. Initialize Trackers
    # Stack Key = (User, Service) -> Ensures 'su' sessions don't mix with 'sshd'
    session_stacks = {} 
    
    # Store completed sessions: {'user':, 'service':, 'start':, 'end':, 'duration':, 'status':}
    all_sessions = []
    
    # Deduplication trackers (to handle rapid duplicate logs)
    last_seen_map = {} 
    DEDUPE_WINDOW = 2 # seconds

    # 3. Iterate through events (The "Closest Match" Logic)
    for _, row in df_events.iterrows():
        user = row.get('USERNAME', 'N/A')
        service = row.get('Service', 'Unknown')
        ts = row['datetime']
        evt = row['Event_Type']
        
        if user == 'N/A': continue

        # Unique ID for this user+process stream
        stack_key = (user, service)
        
        # --- DEDUPLICATION ---
        last_seen_key = (user, service, evt)
        last_time = last_seen_map.get(last_seen_key)
        if last_time and (ts - last_time).total_seconds() < DEDUPE_WINDOW:
            continue 
        last_seen_map[last_seen_key] = ts
        # ---------------------

        if evt == 'LOGIN':
            if stack_key not in session_stacks: 
                session_stacks[stack_key] = []
            session_stacks[stack_key].append(ts)

        elif evt == 'LOGOUT':
            # Check if there is an open session to close for this specific User+Service
            if stack_key in session_stacks and session_stacks[stack_key]:
                # Pop the most recent login (LIFO - Last In First Out)
                # This finds the "closest matching entry" as requested
                start_time = session_stacks[stack_key].pop()
                
                duration_sec = (ts - start_time).total_seconds()
                
                all_sessions.append({
                    'user': user,
                    'service': service,
                    'start': start_time,
                    'end': ts,
                    'duration_str': format_duration(duration_sec),
                    'status': 'Closed'
                })

    # 4. Process Active/Stale Sessions (Leftovers in stack)
    if not df['datetime'].empty:
        now = df['datetime'].max()
    else:
        now = pd.Timestamp.now()

    for stack_key, start_times in session_stacks.items():
        user, service = stack_key
        for start in start_times:
            hours_open = (now - start).total_seconds() / 3600
            
            if hours_open < 24:
                status_label = "🟢 Active"
            else:
                status_label = "⚠️ Stale (>24h)"

            all_sessions.append({
                'user': user,
                'service': service,
                'start': start,
                'end': None, # No end time
                'duration_str': status_label,
                'status': 'Active'
            })

    # 5. Build the Aggregated Table
    if not all_sessions:
        return ["- No complete sessions found."]

    # Group by (User, Service)
    grouped_data = {}
    for sess in all_sessions:
        key = (sess['user'], sess['service'])
        if key not in grouped_data:
            grouped_data[key] = []
        grouped_data[key].append(sess)

    # Construct Markdown Table Lines
    table_lines = []
    # Header
    table_lines.append("| User | Count | Process | Timeframes (Start ➝ End) | Duration |")
    table_lines.append("| :--- | :---: | :--- | :--- | :--- |")

    for (user, service), sessions in grouped_data.items():
        count = len(sessions)
        
        # Build multi-line cells using HTML break <br>
        timeframe_lines = []
        duration_lines = []
        
        # Sort sessions by start time for the report
        sessions.sort(key=lambda x: x['start'])
        
        for s in sessions:
            start_str = s['start'].strftime('%Y-%m-%d %H:%M')
            if s['end']:
                end_str = s['end'].strftime('%H:%M') # Just show time for end to save space
                timeframe_lines.append(f"{start_str} ➝ {end_str}")
            else:
                timeframe_lines.append(f"{start_str} ➝ ...")
            
            duration_lines.append(s['duration_str'])

        # Join with <br> for multi-line table cells
        timeframe_cell = "<br>".join(timeframe_lines)
        duration_cell = "<br>".join(duration_lines)
        
        row_str = f"| **{user}** | {count} | `{service}` | {timeframe_cell} | {duration_cell} |"
        table_lines.append(row_str)

    return table_lines