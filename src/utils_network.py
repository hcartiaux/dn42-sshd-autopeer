# Verify host conformity


def get_ipv6(host):
    """
    Retrieve the IPv6 address(es) associated with a host.

    Parameters:
        host (str): The hostname to resolve or IP address to validate.

    Returns:
        list: A list containing the IPv6 address(es) of the host.
    """
    try:
        # Is host an IP address ? If yes, return  [host]
        import socket
        socket.inet_pton(socket.AF_INET6, host)
        return [host]
    except BaseException:
        pass

    try:
        # if host is a domain name, returns all the AAAA records or [] if none
        from dns import resolver
        answers = resolver.resolve(host, 'AAAA')
        return [rdata.address for rdata in answers]
    except BaseException:
        return []


def validate_ipv6(ip, forbidden_networks=[]):
    """
    Validate an IPv6 address, ensure that it is not private, configured locally or part
    of a list of private networks.

    Parameters:
        ip (str): The IPv6 address to validate.
        forbidden_networks (list): A list of forbidden network prefixes.

    Returns:
        bool: True if the IP is valid, False otherwise.
    """
    try:
        import socket
        import psutil
        import ipaddress

        is_private = False
        is_local = False
        is_forbidden = False

        # Is ip a private address ?
        is_private = ipaddress.ip_address(ip).is_private

        # Is ip already configured on the local system ?
        interfaces = psutil.net_if_addrs()
        for interface, addrs in interfaces.items():
            for addr in addrs:
                if addr.family == socket.AF_INET6 and addr.address == ip:
                    is_local = True
                    break

        # Is ip part of a network in forbidden_networks
        ip_obj = ipaddress.ip_address(ip)
        for network in forbidden_networks:
            if ip_obj in ipaddress.ip_network(network, strict=False):
                is_forbidden = True
                break

        return not (is_private or is_local or is_forbidden)

    except BaseException:
        return False

def get_latency(host):
    """
    Measure the average latency to a host using ping.

    Parameters:
        host (str): The hostname or IP address to ping.

    Returns:
        float or None: The average round-trip time in milliseconds, or None if the ping failed
                      or the average time couldn't be parsed from the output.
    """
    import re
    import subprocess

    ping = subprocess.Popen(
        ["ping", "-c", "4", host],
        stdout = subprocess.PIPE,
        stderr = subprocess.PIPE
    )
    out, error = ping.communicate()

    # Parse the average time from the output
    # Example output line: "rtt min/avg/max/mdev = 20.923/21.548/21.947/0.388 ms"
    avg_pattern = r'min/avg/max/mdev = \d+\.\d+/(\d+\.\d+)/\d+\.\d+/\d+\.\d+'
    match = re.search(avg_pattern, out.decode('utf-8'))

    if match:
        return float(match.group(1))
    else:
        return None

def get_latency_bgp_community(lat):
    """
    Return a BGP community value (1-9) based on the provided latency number.

    Implements the values given here: https://dn42.eu/howto/BGP-communities

    Args:
        lat (float): Latency value in milliseconds

    Returns:
        int: Community number between 1 and 9
    """
    if lat == None:
        return 9
    if lat <= 2.7:
        return 1
    elif lat <= 7.3:
        return 2
    elif lat <= 20:
        return 3
    elif lat <= 55:
        return 4
    elif lat <= 148:
        return 5
    elif lat <= 403:
        return 6
    elif lat <= 1097:
        return 7
    elif lat <= 2981:
        return 8
    else:
        return 9
