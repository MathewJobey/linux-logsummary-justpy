import os
import matplotlib
matplotlib.use('Agg') # Headless mode
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

def create_all_charts(df_logs, output_dir, resample_rule, time_unit, date_format, xlabel_text):
    """
    Generates all 6 visualization charts and saves them to output_dir.
    Returns: (peak_time_string, peak_volume) for the report.
    """
    print("[GRAPHS] Generating visualizations...")
    
    def add_bar_labels(ax):
        for p in ax.patches:
            if p.get_width() > 0:
                ax.text(p.get_width(), p.get_y() + p.get_height()/2, 
                        f' {int(p.get_width())}', ha='left', va='center')

    # 1. Volume Chart
    plt.figure(figsize=(10, 5))
    time_counts = df_logs.resample(resample_rule, on='datetime').size()
    peak_str, peak_vol = "N/A", 0
    
    if not time_counts.empty:
        ax = time_counts.plot(kind='line', marker='o', color='#1f77b4')
        plt.title(f'Log Volume Over Time (Grouped by {time_unit})')
        plt.ylabel('Event Count')
        plt.xlabel(xlabel_text)
        plt.grid(True, alpha=0.5)
        ax.xaxis.set_major_formatter(mdates.DateFormatter(date_format))
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, '1_log_volume.png'))
        
        peak_str = time_counts.idxmax().strftime(date_format)
        peak_vol = time_counts.max()
    plt.close()

    # 2. Top Services
    plt.figure(figsize=(10, 5))
    ax = df_logs['Service'].value_counts().head(10).sort_values().plot(kind='barh', color='#2ca02c')
    add_bar_labels(ax)
    plt.title('Top System Services')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, '2_top_services.png'))
    plt.close()

    # 3. Top Templates
    plt.figure(figsize=(10, 6))
    top_templates = df_logs['Template ID'].value_counts().head(8).sort_values()
    if not top_templates.empty:
        ax = top_templates.plot(kind='barh', color='#ff7f0e')
        ax.set_yticklabels([f"Template {tid}" for tid in top_templates.index])
        add_bar_labels(ax) 
        plt.title('Top Log Event Types')
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, '3_top_templates.png'))
    plt.close()

    # 4. Top Users
    plt.figure(figsize=(10, 5))
    ax = df_logs[df_logs['USERNAME'] != 'N/A']['USERNAME'].value_counts().head(10).sort_values().plot(kind='barh', color='#9467bd')
    add_bar_labels(ax)
    plt.title('Top Active Users')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, '4_top_users.png'))
    plt.close()

    # 5. Top IPs
    plt.figure(figsize=(10, 5))
    ax = df_logs[df_logs['RHOST'] != 'N/A']['RHOST'].value_counts().head(10).sort_values().plot(kind='barh', color='#d62728')
    add_bar_labels(ax)
    plt.title('Top Remote IPs')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, '5_top_ips.png'))
    plt.close()

    # 6. Security Breakdown
    plt.figure(figsize=(8, 6))
    sec_counts = df_logs[df_logs['Security_Tag'] != 'Normal']['Security_Tag'].value_counts()
    
    # Custom colors
    color_map = {
        'Successful Login': '#99ff99', 
        'Auth Failure': '#ff9999', 
        'Root Activity': '#ffcc99', 
        'Illegal Access': '#c2c2f0', 
        'Normal': '#f0f0f0'
    }
    colors = [color_map.get(x, '#cccccc') for x in sec_counts.index]

    if not sec_counts.empty:
        sec_counts.plot(kind='pie', autopct='%1.1f%%', colors=colors)
        plt.title('Security Event Distribution')
        plt.ylabel('')
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, '6_security_breakdown.png'))
    plt.close()
    
    return peak_str, peak_vol