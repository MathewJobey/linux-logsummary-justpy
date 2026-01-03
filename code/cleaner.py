import os

# Default blacklist (shared)
BASE_BLACKLIST = [
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
    # 5. PROXIES & SERVERS
    "privoxy", "squid", "sendmail", "spamassassin", "httpd", "xfs",
    "IIim", "htt", "htt_server", "canna", "named", "rsyncd", "mysqld", "FreeWnn"
]

def extract_process_name(line: str) -> str | None:
    tokens = line.strip().split()
    if len(tokens) < 5:
        return None
    return tokens[4]  # e.g., sshd[123]:

def clean_log_file(input_filename: str, extra_blacklist=None):
    if not os.path.exists(input_filename):
        print(f"Error: Could not find '{input_filename}'.")
        return None

    blacklist = set(BASE_BLACKLIST) | set(extra_blacklist or [])
    base_name, extension = os.path.splitext(input_filename)
    output_filename = f"{base_name}_clean{extension}"
    trash_filename = f"{base_name}_trash{extension}"

    removed_count = 0
    kept_count = 0

    try:
        with open(input_filename, "r") as infile, \
             open(output_filename, "w") as outfile, \
             open(trash_filename, "w") as trashfile:

            for line in infile:
                if not line.strip():
                    continue
                proc = extract_process_name(line)
                if proc is None:
                    outfile.write(line); kept_count += 1; continue

                matched = None
                for bad in blacklist:
                    if proc.startswith(bad):
                        matched = bad
                        break

                if matched:
                    trashfile.write(f"[MATCHED: {matched}] {line}")
                    removed_count += 1
                else:
                    outfile.write(line)
                    kept_count += 1

        return output_filename, trash_filename, kept_count, removed_count
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

def find_new_processes(input_filename: str, known=None):
    """Return a sorted set of process tokens not in known."""
    known = set(known or BASE_BLACKLIST)
    unseen = set()
    if not os.path.exists(input_filename):
        return unseen
    with open(input_filename, "r") as infile:
        for line in infile:
            proc = extract_process_name(line or "")
            if proc and not any(proc.startswith(k) for k in known):
                unseen.add(proc.split("[")[0].rstrip(":"))
    return sorted(unseen)
