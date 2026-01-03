import justpy as jp

# Default blacklist (expand/adjust as needed)
BLACKLIST = [
    # 1. Hardware & Boot
    "kernel", "rc", "irqbalance", "sysctl", "network", "random", "udev",
    "apmd", "smartd", "init",
    # 2. Peripherals
    "bluetooth", "sdpd", "hcid", "cups", "gpm",
    # 3. System Housekeeping
    "logrotate", "syslog", "klogd", "crond", "anacron", "atd", "readahead",
    "messagebus", "ntpd", "dd",
    # 4. Network Plumbing
    "rpc.statd", "rpcidmapd", "portmap", "nfslock", "automount", "ifup",
    "netfs", "autofs",
    # 5. Proxies & Servers
    "privoxy", "squid", "sendmail", "spamassassin", "httpd", "xfs",
    "IIim", "htt", "htt_server", "canna", "named", "rsyncd", "mysqld", "FreeWnn",
]

def build_clean_card(parent):
    card = jp.Div(a=parent, classes="bg-white shadow-xl rounded-2xl w-full max-w-3xl p-6 border border-gray-200")
    jp.Div(text="Linux Log Analysis Pipeline", a=card, classes="text-3xl font-bold text-center text-slate-900 mb-2")
    jp.Div(text="Step 1: Clean Log File", a=card, classes="text-lg font-semibold text-slate-800 flex items-center gap-2 mb-1")
    jp.Div(text="Remove noise from hardware, boot, peripheral, and housekeeping processes.", a=card, classes="text-sm text-slate-600 mb-4")

    drop_area = jp.Div(
        a=card, text="Drag and drop file here",
        classes="border-2 border-dashed border-gray-300 bg-gray-50 rounded-xl h-36 flex flex-col items-center justify-center text-slate-600 mb-3 "
    )
    jp.Input(
        a=drop_area, type="file",
        classes="mt-3 block text-sm text-slate-600 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-600 hover:file:bg-blue-100"
    )

    

    jp.Button(
        a=card, text="Clean Log File",
        classes="mt-4 w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 rounded-lg shadow"
    )

    details = jp.Details(a=card, classes="mt-4 text-sm text-slate-700", open=False)
    jp.Summary(
        text="View blacklisted process keywords", a=details,
        classes="flex items-center gap-2 cursor-pointer text-blue-600 font-medium"
    )
    jp.Ul(
        a=details, classes="mt-2 list-disc list-inside space-y-1 text-slate-700",
        children=[jp.Li(text=proc) for proc in BLACKLIST]
    )