import os
import socket
import sqlite3
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

# Database creation


def database():
    db_path = os.environ['DB_PATH']
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()
    table = """ CREATE TABLE IF NOT EXISTS peering_links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    as_num INTEGER UNIQUE NOT NULL,
                    wg_pub_key TEXT NOT NULL,
                    wg_endpoint_addr TEXT NOT NULL,
                    wg_endpoint_port INTEGER NOT NULL CHECK(wg_endpoint_port BETWEEN 1 AND 65535)
            ); """
    cursor.execute(table)
    connection.commit()
    connection.close()

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
    db_path = os.environ['DB_PATH']
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row  # provides dictionary-like interface
        cursor = connection.execute("SELECT id FROM peering_links WHERE as_num = ?", (as_num,))
        row = cursor.fetchone()
        return row['id'] if row else None


def get_peer_config(user, as_num):
    return get_peer_list(user)[as_num]


def get_peer_list(user):
    db_path = os.environ['DB_PATH']
    as_nums = as_maintained_by(user)
    placeholders = ",".join("?" * len(as_nums))
    query = f"""SELECT id, as_num, wg_pub_key, wg_endpoint_addr, wg_endpoint_port
                FROM peering_links
                WHERE as_num IN ({placeholders})"""

    peer_list = {}
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row  # Enables dictionary-like row access
        cursor = connection.cursor()
        cursor.execute(query, as_nums)
        rows = cursor.fetchall()

        for row in rows:
            peer_list[str(row["as_num"])] = {
                "id": row["id"],
                "wg_pub_key": row["wg_pub_key"],
                "wg_endpoint_addr": row["wg_endpoint_addr"],
                "wg_endpoint_port": str(row["wg_endpoint_port"]),  # Convert to string if needed
                "link_local": "fe80:0263::2:" + str(row["id"])
            }
    return peer_list

# Actions


def peer_create(as_num, wg_pub_key, wg_endpoint_addr, wg_endpoint_port):
    db_path = os.environ['DB_PATH']
    query = """INSERT INTO peering_links (as_num, wg_pub_key, wg_endpoint_addr, wg_endpoint_port)
               VALUES (?, ?, ?, ?)"""

    try:
        with sqlite3.connect(db_path) as connection:
            cursor = connection.cursor()
            cursor.execute(query, (as_num, wg_pub_key, wg_endpoint_addr, wg_endpoint_port))
            connection.commit()
    except sqlite3.IntegrityError as e:
        print(f"Error inserting peer: {e}")
        return False
    return True

def peer_remove(as_num):
    db_path = os.environ['DB_PATH']
    query = "DELETE FROM peering_links WHERE as_num = ?"

    try:
        with sqlite3.connect(db_path) as connection:
            cursor = connection.cursor()
            cursor.execute(query, (as_num,))
            connection.commit()
            return True
    except sqlite3.Error as e:
        print(f"Error removing peer: {e}")
        return False

def peer_status(as_num):
    wg_cmd = "wg show wg-peer-int"
    wg_output = os.popen("ssh nl-ams2.flap sudo " + wg_cmd).read()
    birdc_cmd = "birdc show protocols all ibgp_nl_ams1"
    birdc_output = os.popen("ssh nl-ams2.flap sudo " + birdc_cmd).read()
    return "$ " + wg_cmd + "\n" + wg_output + \
        "\n$ " + birdc_cmd + "\n" + birdc_output

# Gen config


def gen_wireguard_config(user, as_num):
    local_config = get_local_config(as_num)
    peer_config = get_peer_config(user, as_num)

    wireguard = f"""
[Interface]
PrivateKey = **REPLACEME**
ListenPort = { peer_config["wg_endpoint_port"] }
PostUp = /sbin/ip addr add dev %i { peer_config["link_local"] }/128 peer { local_config["link_local"] }/128
Table = off

[Peer]
PublicKey = { local_config["wg_pub_key"] }
Endpoint = { local_config["wg_endpoint_addr"] }:{ local_config["wg_endpoint_port"] }
PersistentKeepalive = 30
AllowedIPs = 172.16.0.0/12, 10.0.0.0/8, fd00::/8, fe80::/10
"""
    return wireguard


def gen_bird_config(user, as_num):
    local_config = get_local_config(as_num)

    bird = f"""
protocol bgp flipflap {{
    local as { as_num }
    neighbor {local_config["link_local"]} as { os.environ["ASN"] };
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
