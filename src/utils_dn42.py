import os
import socket
from dns import resolver

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
        socket.inet_pton(socket.AF_INET6, host)
        return [host]
    except BaseException:
        pass

    try:
        answers = resolver.resolve(host, 'AAAA')
        return [rdata.address for rdata in answers]
    except BaseException:
        return []

# Interrogate peering info


def get_local_config(as_num):
    id = get_asn_id(as_num)
    local_config = {
        "wg_pub_key": 'rj0SORruOE/hGVJ5IkDXNedsL9Nxs8j0kTujRB01XXk=',
        "wg_endpoint_addr": '2001:bc8:3feb:100::1',
        "wg_endpoint_port": str(52000 + int(id)),
        "link_local": "fe80:0263::1:" + str(id)
    }
    return local_config


def get_asn_id(as_num):
    return 1


def get_peer_config(as_num):
    return get_peer_list()[as_num]


def get_peer_list():
    peer_list = {}
    peer_list["4242420266"] = {
        "id": 1,
        "wg_pub_key": 'rj0SORruOE/hGVJ5IkDXNedsL9Nxs8j0kTujRB01XXk=',
        "wg_endpoint_addr": '2001:bc8:3feb:100::2',
        "wg_endpoint_port": '51902',
        "link_local": "fe80:0263::2::1"
    }
    peer_list["4242420276"] = {
        "id": 2,
        "wg_pub_key": 'aa0SORruOE/hGVJ5IkDXNedsL9Nxs8j0kTujRB01XXk=',
        "wg_endpoint_addr": '2001:bc8:3feb:100::3',
        "wg_endpoint_port": '51903',
        "link_local": "fe80:0263::2::2"
    }

    return peer_list

# Actions


def peer_create(as_num, wg_pub_key, wg_end_point_addr, wg_end_point_port):
    return True


def peer_remove(as_num):
    return True


def peer_status(as_num):
    wg_cmd = "wg show wg-peer-int"
    wg_output = os.popen("ssh nl-ams2.flap sudo " + wg_cmd).read()
    birdc_cmd = "birdc show protocols all ibgp_nl_ams1"
    birdc_output = os.popen("ssh nl-ams2.flap sudo " + birdc_cmd).read()
    return "$ " + wg_cmd + "\n" + wg_output + \
        "\n$ " + birdc_cmd + "\n" + birdc_output

# Gen config


def gen_wireguard_config(as_num):
    #    local_config = get_local_config(as_num)
    #    peer_config = get_peer_config(as_num)

    wireguard = """
[Interface]
PrivateKey =
ListenPort = 51823
PostUp = /sbin/ip addr add dev %i fe80::103/128 peer fe80::2717/128
Table = off

[Peer]
PublicKey = cokP4jFBH0TlBD/m3sWCpc9nADLOhzM2+lcjAb3ynFc=
Endpoint = nl.vm.whojk.com:23441
PersistentKeepalive = 30
AllowedIPs = 172.16.0.0/12, 10.0.0.0/8, fd00::/8, fe80::/10
"""
    return wireguard


def gen_bird_config(as_num):
    #    local_config = get_local_config(as_num)
    #    peer_config = get_peer_config(as_num)

    bird = """
protocol bgp whojk_v6 from dnpeers {
    neighbor fe80::2717 as 4242422717;
    interface "wg-peer-whojk";
    ipv4 {
        extended next hop on;
    };

    ipv6 {
        extended next hop off;
    };
}
"""
    return bird
