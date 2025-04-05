import os

# Interrogate the dn42 registry


def load_authorized_keys(user):
    import paramiko
    import base64
    authorized_keys = []
    try:
        with open(os.environ['DN42_REGISTRY_DIRECTORY'] + "/data/mntner/" + user.upper() + "-MNT", 'r') as file:
            for line in file:
                l = line.strip().split()
                if len(l) >= 3 and l[0] == 'auth:':
                    key_type = l[1]
                    key_data = l[2]
                    if key_type == 'ssh-ed25519':
                        key = paramiko.Ed25519Key(data=base64.b64decode(key_data))
                    elif key_type == 'ssh-rsa':
                        key = paramiko.RSAKey(data=base64.b64decode(key_data))
                    else:
                        continue
                    authorized_keys.append(key)
    except BaseException:
        pass
    return authorized_keys


def as_maintained_by(user):
    as_nums = []

    directory = os.environ['DN42_REGISTRY_DIRECTORY'] + "/data/aut-num"
    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)
        try:
            with open(filepath, "r") as file:
                for line in file:
                    l = line.strip().split()
                    if len(l) == 2 and l[0] == 'mnt-by:' and l[1] == user.upper() + "-MNT":
                        as_nums.append(filename[2:])
        except BaseException:
            pass

    return as_nums

# Verify host conformity


def get_ipv6(host):
    try:
        import socket
        socket.inet_pton(socket.AF_INET6, host)
        return [host]
    except BaseException:
        pass

    try:
        from dns import resolver
        answers = resolver.resolve(host, 'AAAA')
        return [rdata.address for rdata in answers]
    except BaseException:
        return []

# Interrogate peering info


def get_local_config(as_id):
    local_config = {
        "wg_pub_key": os.environ['DN42_WG_PUB_KEY'],
        "wg_endpoint_addr": os.environ['DN42_SERVER'],
        "wg_endpoint_port": str(int(os.environ['DN42_WG_BASE_PORT']) + int(as_id)),
        "link_local": os.environ['DN42_WG_LINK_LOCAL'] + '1:' + hex(int(as_id))[2:]
    }
    return local_config


def peer_status(as_num):
    wg_cmd = f"wg show wg-{ as_num }"
    wg_output = os.popen(wg_cmd).read()
    birdc_cmd = f"birdc show protocols all ibgp_{ as_num }"
    birdc_output = os.popen(birdc_cmd).read()
    return "$ " + wg_cmd + "\n" + wg_output + \
        "\n$ " + birdc_cmd + "\n" + birdc_output

# Gen config


def gen_wireguard_config(user, as_id, wg_endpoint_port, link_local):
    local_config = get_local_config(as_id)

    wireguard = f"""
[Interface]
PrivateKey = **REPLACEME**
ListenPort = { wg_endpoint_port }
PostUp = /sbin/ip addr add dev %i { link_local }/128 peer { local_config["link_local"] }/128
Table = off

[Peer]
PublicKey = { local_config["wg_pub_key"] }
Endpoint = { local_config["wg_endpoint_addr"] }:{ local_config["wg_endpoint_port"] }
PersistentKeepalive = 30
AllowedIPs = 172.16.0.0/12, 10.0.0.0/8, fd00::/8, fe80::/10
"""
    return wireguard


def gen_bird_config(user, as_num, as_id):
    local_config = get_local_config(as_id)

    bird = f"""
protocol bgp flipflap {{
    local as { as_num }
    neighbor {local_config["link_local"]} as { os.environ["DN42_ASN"] };
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
