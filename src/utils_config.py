from datetime import datetime
import logging
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
    wg_cmd = f"wg show wg-as{as_num}"
    wg_output = os.popen(wg_cmd).read()
    birdc_cmd = f"birdc show protocols all ebgp_{as_num}"
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


def gen_wireguard_local_config(as_num):
    """
    Generate the WireGuard configuration for a peering session (local side).

    Parameters:
        as_num (str): The AS number.

    Returns:
        str: The WireGuard configuration as a string.
    """
    from src.database_manager import DatabaseManager

    peer_config = DatabaseManager().get_peer_config(as_num)
    local_config = get_local_config(peer_config['id'])

    wireguard = f"""
[Interface]
PrivateKey =
ListenPort = {local_config["wg_endpoint_port"]}
PostUp = /sbin/ip addr add dev %i {local_config['link_local']}/128 peer {peer_config['link_local']}/128
Table = off

[Peer]
PublicKey = {peer_config['wg_pub_key']}
Endpoint = {peer_config['wg_endpoint_addr']}:{peer_config['wg_endpoint_port']}
PersistentKeepalive = 30
AllowedIPs = 172.16.0.0/12, 10.0.0.0/8, fd00::/8, fe80::/10
"""
    return wireguard.strip()


def gen_bird_local_config(as_num):
    """
    Generate the BIRD configuration for a peering session (local side)

    Parameters:
        as_num (str): The AS number.

    Returns:
        str: The BIRD configuration as a string.
    """

    from src.utils_network import get_latency, get_latency_bgp_community
    from src.database_manager import DatabaseManager

    peer_config = DatabaseManager().get_peer_config(as_num)

    latency = get_latency(peer_config['wg_endpoint_addr'])
    community = get_latency_bgp_community(latency)

    bird = f"""
define AS{as_num}_LATENCY = {community};

protocol bgp ebgp_as{as_num}_v6 from dnpeers {{
    neighbor {peer_config['link_local']} as {as_num};
    interface "wg-as{as_num}";

    ipv4 {{
        import where dn42_import_filter(AS{as_num}_LATENCY, BANDWIDTH, LINKTYPE);
        export where dn42_export_filter(AS{as_num}_LATENCY, BANDWIDTH, LINKTYPE);
        extended next hop on;
    }};

    ipv6 {{
        import where dn42_import_filter_v6(AS{as_num}_LATENCY, BANDWIDTH, LINKTYPE);
        export where dn42_export_filter_v6(AS{as_num}_LATENCY, BANDWIDTH, LINKTYPE);
        extended next hop off;
    }};
}}
    """

    return bird.strip()


def gen_all_config(as_nums):
    """Generates WireGuard and BIRD configurations for a list of AS numbers.

    It creates versioned directories based on the current timestamp and writes
    the configuration files for each AS number into these directories. Finally,
    it updates the 'current' symbolic link in the base directories to point to
    the newly created version.

    Args:
        as_nums: A list of autonomous system (AS) numbers to generate
            configurations for.

    Returns:
        True if all configurations were generated and links updated
        successfully, False otherwise.
    """

    wg_base_dir = os.environ.get("DN42_WG_CONFIG_DIR")
    bird_base_dir = os.environ.get("DN42_BIRD_CONFIG_DIR")

    if not wg_base_dir or not bird_base_dir:
        logging.error("Environment variables DN42_WG_CONFIG_DIR and DN42_BIRD_CONFIG_DIR must be set.")
        return False

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    # Create WireGuard versioned directory
    wg_version_dir = os.path.join(wg_base_dir, timestamp)
    try:
        os.makedirs(wg_version_dir, exist_ok=True)
        logging.info(f"Created WireGuard version directory: {wg_version_dir}")
    except OSError as e:
        logging.error(f"Error creating WireGuard version directory: {e}")
        return False

    # Create BIRD versioned directory
    bird_version_dir = os.path.join(bird_base_dir, timestamp)
    try:
        os.makedirs(bird_version_dir, exist_ok=True)
        logging.info(f"Created BIRD version directory: {bird_version_dir}")
    except OSError as e:
        logging.error(f"Error creating BIRD version directory: {e}")
        return False

    all_configs_written = True
    for as_num in as_nums:
        # Generate and write WireGuard config
        wg_config = gen_wireguard_local_config(as_num)
        wg_filename = f"wg-as{as_num}"
        wg_filepath = os.path.join(wg_version_dir, wg_filename)
        try:
            with open(wg_filepath, "w") as f:
                f.write(wg_config)
            logging.info(f"Written WireGuard config to: {wg_filepath}")
        except OSError as e:
            logging.error(f"Error writing WireGuard config for AS{as_num}: {e}")
            all_configs_written = False

        # Generate and write BIRD config
        bird_config = gen_bird_local_config(as_num)
        bird_filename = f"ebgp_as{as_num}"
        bird_filepath = os.path.join(bird_version_dir, bird_filename)
        try:
            with open(bird_filepath, "w") as f:
                f.write(bird_config)
            logging.info(f"Written BIRD config to: {bird_filepath}")
        except OSError as e:
            logging.error(f"Error writing BIRD config for AS{as_num}: {e}")
            all_configs_written = False

        if not all_configs_written:
            return False  # Return early if any config writing fails

    # Update WireGuard 'current' symlink
    wg_current_dir = os.path.join(wg_base_dir, "current")
    try:
        if os.path.islink(wg_current_dir):
            os.unlink(wg_current_dir)
        os.symlink(timestamp, wg_current_dir)
        logging.info(f"Updated 'current' link in {wg_base_dir} to point to: {wg_version_dir}")
    except OSError as e:
        logging.exception(f"Error updating WireGuard symlink: {e}")
        return False

    # Update BIRD 'current' symlink
    bird_current_dir = os.path.join(bird_base_dir, "current")
    try:
        if os.path.islink(bird_current_dir):
            os.unlink(bird_current_dir)
        os.symlink(timestamp, bird_current_dir)
        logging.info(f"Updated 'current' link in {bird_base_dir} to point to: {bird_version_dir}")
    except OSError as e:
        logging.exception(f"Error updating BIRD symlink: {e}")
        return False

    return True
