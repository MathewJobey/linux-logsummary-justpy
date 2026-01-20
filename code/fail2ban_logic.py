import pandas as pd

def scan_threats(df_logs, findtime='10min', maxretry=5):
    """
    Implements Fail2Ban logic on a static DataFrame.
    Handles RHOSTs that may contain multiple values (IP + Domain).
    """
    print(f"[THREAT] Scanning for patterns: >{maxretry} failures in {findtime}...")
    
    # 1. FILTER: Select only "Failure" events
    fail_mask = (
        (df_logs['Security_Tag'].str.contains('Auth Failure', na=False)) |
        (df_logs['Security_Tag'].str.contains('Illegal Access', na=False)) |
        (df_logs['Severity'] == 'CRITICAL')
    )
    df_fails = df_logs[fail_mask].copy()
    
    if df_fails.empty:
        return pd.DataFrame()

    # 2. BUCKET & COUNT
    df_fails = df_fails.sort_values('datetime')
    
    # --- CRITICAL FIX: FORCE STRING TYPE ---
    # If RHOST is a list ['IP', 'Domain'], this converts it to "['IP', 'Domain']"
    # This guarantees that ALL values in the RHOST parameter are used for grouping/banning.
    df_fails['RHOST'] = df_fails['RHOST'].astype(str)

    # Group by RHOST (which is now guaranteed to be a unique string containing all hosts)
    rolling_counts = (
        df_fails
        .set_index('datetime')
        .groupby('RHOST')['Raw Log']
        .rolling(findtime)
        .count()
        .reset_index()
    )
    
    rolling_counts.rename(columns={'Raw Log': 'Fail_Count'}, inplace=True)

    # 3. FLAG
    ban_trigger_events = rolling_counts[rolling_counts['Fail_Count'] >= maxretry]
    
    if ban_trigger_events.empty:
        return pd.DataFrame()

    # 4. AGGREGATE
    flagged_hosts = ban_trigger_events['RHOST'].unique()
    
    report_data = []
    
    for host in flagged_hosts:
        # Get data specific to this Host/IP string
        host_events = df_fails[df_fails['RHOST'] == host]
        
        triggers = ban_trigger_events[ban_trigger_events['RHOST'] == host]
        first_ban_time = triggers['datetime'].min()
        total_failures = len(host_events)
        max_burst = triggers['Fail_Count'].max()
        
        report_data.append({
            'Target_Host': host,  # Contains the full string (e.g., "['10.0.0.1', 'site.com']")
            'Ban_Triggered_At': first_ban_time,
            'Max_Burst_Rate': int(max_burst),
            'Total_Failures': total_failures,
            'Status': 'BANNABLE'
        })
        
    return pd.DataFrame(report_data)