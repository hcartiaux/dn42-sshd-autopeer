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
