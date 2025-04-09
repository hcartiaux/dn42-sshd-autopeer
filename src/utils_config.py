import os

# Interrogate peering info and generate bird+wireguard configuration


def get_local_config(as_id):
    """
    Retrieve the local configuration for a given AS ID.

    Parameters:
        as_id (str): The AS ID for which to retrieve the configuration.

    Returns:
        dict: A dictionary containing the local configuration.
    """
    local_config = {
        "wg_pub_key": os.environ['DN42_WG_PUB_KEY'],
        "wg_endpoint_addr": os.environ['DN42_SERVER'],
        "wg_endpoint_port": str(int(os.environ['DN42_WG_BASE_PORT']) + int(as_id)),
        "link_local": os.environ['DN42_WG_LINK_LOCAL'] + '1:' + hex(int(as_id))[2:]
    }
    return local_config


def peer_status(as_num):
    """
    Retrieve the status of a peer AS number.

    Parameters:
        as_num (str): The AS number of the peer.

    Returns:
        str: The status output of the peer.
    """
    wg_cmd = f"wg show wg-{as_num}"
    wg_output = os.popen(wg_cmd).read()
    birdc_cmd = f"birdc show protocols all ibgp_{as_num}"
    birdc_output = os.popen(birdc_cmd).read()
    return "$ " + wg_cmd + "\n" + wg_output + \
        "\n$ " + birdc_cmd + "\n" + birdc_output

# Gen config


def gen_wireguard_peer_config(as_id, wg_endpoint_port, link_local):
    """
    Generate the WireGuard configuration for a peering session (remote side).

    Parameters:
        as_id (str): The AS ID.
        wg_endpoint_port (str): The WireGuard endpoint port.
        link_local (str): The link-local address.

    Returns:
        str: The WireGuard configuration as a string.
    """
    local_config = get_local_config(as_id)

    wireguard = f"""
[Interface]
PrivateKey = **REPLACEME**
ListenPort = {wg_endpoint_port}
PostUp = /sbin/ip addr add dev %i {link_local}/128 peer {local_config["link_local"]}/128
Table = off

[Peer]
PublicKey = {local_config["wg_pub_key"]}
Endpoint = {local_config["wg_endpoint_addr"]}:{local_config["wg_endpoint_port"]}
PersistentKeepalive = 30
AllowedIPs = 172.16.0.0/12, 10.0.0.0/8, fd00::/8, fe80::/10
"""
    return wireguard


def gen_bird_peer_config(as_num, as_id):
    """
    Generate the BIRD configuration for a peering session (remote side)

    Parameters:
        as_num (str): The AS number.
        as_id (str): The AS ID.

    Returns:
        str: The BIRD configuration as a string.
    """
    local_config = get_local_config(as_id)

    bird = f"""
protocol bgp flipflap {{
    local as {as_num}
    neighbor {local_config["link_local"]} as {os.environ["DN42_ASN"]};
    path metric 1;
    interface "wg-peer-flipflap";
    ipv4 {{
        extended next hop on;
        import limit 9000 action block;
        import table;
    }};

    ipv6 {{
        extended next hop off;
        import limit 9000 action block;
        import table;
    }};
}}
"""
    return bird
