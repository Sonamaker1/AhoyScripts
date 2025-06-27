import psutil

def get_wireshark_filter(process_name):
    ip_set = set()
    port_set = set()
    local_ip_set = set()

    found = False

    for proc in psutil.process_iter(['pid', 'name']):
        if process_name.lower() in proc.info['name'].lower():
            found = True
            try:
                for conn in proc.connections(kind='inet'):
                    if conn.raddr:
                        ip_set.add(conn.raddr.ip)
                        port_set.add(str(conn.raddr.port))
                    if conn.laddr:
                        local_ip_set.add(conn.laddr.ip)
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                pass

    if not found:
        print(f"[!] No process found with name containing: {process_name}")
        return

    # Generate Wireshark filter
    ip_filter = " or ".join([f"ip.addr == {ip}" for ip in ip_set])
    port_filter = " or ".join([f"tcp.port == {port} or udp.port == {port}" for port in port_set])

    combined_filter = ""
    if ip_filter and port_filter:
        combined_filter = f"({ip_filter}) and ({port_filter})"
    elif ip_filter:
        combined_filter = ip_filter
    elif port_filter:
        combined_filter = port_filter
    else:
        combined_filter = "No active connections found."

    print("\n=== Wireshark Display Filter ===")
    print(combined_filter)

    print("\nOptional: Filter your IP as well")
    for ip in local_ip_set:
        print(f"(ip.src == {ip} or ip.dst == {ip}) and ({combined_filter})")


if __name__ == "__main__":
    pname = input("Enter process name to generate Wireshark filter: ")
    get_wireshark_filter(pname)
