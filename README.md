# dn42 Auto-Peering SSH Service (AS4242420263)

A Python-based self-service SSH server that enables dn42 network maintainers
to automatically establish and manage peering connections with AS4242420263.

## Overview

This project implements a custom SSH server using [Paramiko](https://github.com/paramiko/paramiko/)
that authenticates users against the dn42 registry. It allows network operators to request peering
sessions without manual intervention, storing all peering information in a SQLite database.

## Quick Start

### Prerequisites

- Debian >= 12
- Python 3

### Installation

1. Clone this repository
2. Clone the [dn42 registry](https://git.dn42.dev/dn42/registry)
3. Install dependencies: `apt install git python3-dnspython python3-packaging python3-paramiko python3-psutil python3-rich`
4. Generate a SSH host key with `ssh-keygen`
5. Set up environment variables (see Configuration section)
6. Run the server:

```
$ python dn42-autopeer.py --server
2025-04-06 22:15:34,391:INFO:[SSHServerBase] Listening thread started
```

### Usage

```
python dn42-autopeer.py --help                                                                                                                                (↑✗main)
usage: dn42-sshd [-h] (--server | --genconfig | --gaming)

options:
  -h, --help   show this help message and exit
  --server     Start the auto peering server
  --genconfig  Generate the configuration from the peering db
  --gaming     Start the gaming server
```

## Configuration

### Environment variables

These environment variables can be set to configure the service

| Variable                  | Description                                               | Default                           |
|---------------------------|-----------------------------------------------------------|-----------------------------------|
| `DN42_SSH_HOST_KEY`       | Path to SSH host key file                                 | `files/ssh-keys/ssh_host_rsa_key` |
| `DN42_SSH_LISTEN_ADDRESS` | Listen address                                            | `::1`                             |
| `DN42_SSH_PORT`           | SSH port                                                  | `4242`                            |
| `DN42_SERVER`             | Public domain name of the server                          | `nl-ams2.flap42.eu`               |
| `DN42_SSH_MOTD_PATH`      | Path to custom MOTD file                                  | `files/motd/$DN42_SERVER`         |
| `DN42_DB_PATH`            | Path to SQLite database file                              | `files/db/$DN42_SERVER`           |
| `DN42_REGISTRY_DIRECTORY` | Path to dn42 registry clone                               | `files/registry`                  |
| `DN42_ASN`                | Your dn42 Autonomous System Number                        | `4242420263`                      |
| `DN42_WG_PUB_KEY`         | WireGuard public key for tunnels                          | `rj0SORruOE/hGV...`               |
| `DN42_WG_PRIV_KEY`        | WireGuard private key used in `--genconfig`               | `**REPLACEME**    `               |
| `DN42_WG_LINK_LOCAL`      | IPv6 link-local base address (without last 4 bytes)       | `fe80:0263::`                     |
| `DN42_WG_BASE_PORT`       | Base WireGuard port                                       | `52000`                           |
| `DN42_RESERVED_NETWORK`   | Network where peering is restricted                       | None                              |
| `DN42_BIRD_CONFIG_DIR`    | Place to generate the bird config files in  `--genconfig` | `files/bird`                      |
| `DN42_WG_CONFIG_DIR`      | Place to generate the wg config files in  `--genconfig`   | `files/wireguard`                 |

## Installation

I deploy this service on Debian using [my own ansible role](https://github.com/hcartiaux/ansible/tree/main/roles/dn42_autopeer).

This is an example of a systemd service unit (`/etc/systemd/system/dn42-sshd.service`).

```
[Unit]
Description=DN42 SSHD Service
After=network.target

[Service]
Type=simple
User=dn42-sshd
Group=dn42-sshd
WorkingDirectory=/home/dn42-sshd/dn42-sshd
ExecStart=python3 dn42-sshd.py --peering
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal
Environment="DN42_SSH_HOST_KEY=/home/dn42-sshd/.ssh/id_rsa"
Environment="DN42_SSH_LISTEN_ADDRESS=::"
Environment="DN42_SSH_PORT=4242"
Environment="DN42_DB_PATH=/home/dn42-sshd/peering.db"
Environment="DN42_REGISTRY_DIRECTORY=/home/dn42-sshd/dn42-registry"
Environment="DN42_ASN=4242420263"
Environment="DN42_WG_PUB_KEY=C3Wlu6y+v84FN/vreuTqL6r5wEtGTMXX5rKgHkxDaTI="
Environment="DN42_WG_LINK_LOCAL=fe80:0263::"
Environment="DN42_WG_BASE_PORT=52000"
Environment="DN42_RESERVED_NETWORK=2001:0bc8:3feb::/48"

# Security hardening
ProtectSystem=full
PrivateTmp=true
NoNewPrivileges=true
ProtectControlGroups=true
ProtectKernelModules=true
ProtectKernelTunables=true
RestrictNamespaces=true

[Install]
WantedBy=multi-user.target
```

It assumes that:

* a local user `dn42-sshd` exists
* the present git repository is cloned in `/home/dn42-sshd/dn42-sshd`
* the dn42 registry is cloned in `/home/dn42-sshd/dn42-registry`
* the SQLite database file is `/home/dn42-sshd/peering.db` and is writeable

It can be enabled and started using the `systemctl` command:

```
$ systemctl enable --now dn42-sshd
```

The logs are readable using the `journalctl` command:

```
$ journalctl -n 100 -f -u dn42-sshd.service
...
Apr 06 21:57:24 nl-ams2 systemd[1]: Started dn42-sshd.service - DN42 SSHD Service.
Apr 06 21:57:31 nl-ams2 python3[9780]: 2025-04-06 21:57:31,576:INFO:[SSHServerBase] Listening thread started
Apr 06 22:12:28 nl-ams2 python3[9780]: 2025-04-06 22:12:28,505:INFO:[SSHServerBase] Accepted connection from ('2a01:...', 48396, 0, 0)
Apr 06 22:12:28 nl-ams2 python3[9780]: 2025-04-06 22:12:28,509:INFO:Connected (version 2.0, client OpenSSH_9.9)
Apr 06 22:12:28 nl-ams2 python3[9780]: 2025-04-06 22:12:28,777:INFO:Auth rejected (none).
Apr 06 22:12:28 nl-ams2 python3[9780]: 2025-04-06 22:12:28,877:INFO:[AuthDn42] Authentication successful for hcartiaux
Apr 06 22:12:28 nl-ams2 python3[9780]: 2025-04-06 22:12:28,910:INFO:[AuthDn42] Authentication successful for hcartiaux
Apr 06 22:12:28 nl-ams2 python3[9780]: 2025-04-06 22:12:28,911:INFO:Auth granted (publickey).
Apr 06 22:12:28 nl-ams2 python3[9780]: 2025-04-06 22:12:28,942:INFO:[SSHServerBase] Started thread 139777270654656 for hcartiaux@('2a01:...', 48396, 0, 0)
Apr 06 22:14:51 nl-ams2 python3[9780]: 2025-04-06 22:14:51,924:INFO:[139777270654656][SSHServerShell] User hcartiaux disconnected
```

## Internals

### Authentication methods

#### Anonymous, class [`SSHServerAuthNone`](https://github.com/hcartiaux/dn42-sshd-autopeer/blob/main/src/ssh_server_auth_none.py)

Accept all connections

#### dn42 registry, class [`SSHServerAuthDn42`](https://github.com/hcartiaux/dn42-sshd-autopeer/blob/main/src/ssh_server_auth_dn42.py)

Accept connections based on the [dn42 maintainer objects](https://dn42.eu/howto/Registry-Authentication#how-authentication-works_authentication-using-an-ssh-key_auth-attribute-format-when-using-an-ssh-key), using the defined public key(s)

* username: lowercase maintainer name, without the `-MNT` suffix
* public keys: supports `ssh-rsa` and `ssh-ed25519` keys defined in the `auth` field

### Specialized SSH servers

Common constructor parameters:

* `server_interface` - can be set to `SSHServerAuthNone` or `SSHServerAuthDn42`
* `host_key_file` - path of the ssh host key file

#### Piping, class [`SSHServerPipe(server_interface, cmd, host_key_file)`](https://github.com/hcartiaux/dn42-sshd-autopeer/blob/main/src/ssh_server_pipe.py)

* `cmd` - command to be executed and piped to the user

#### Shell, class [`SSHServerShell(server_interface, shell_class, host_key_file)`](https://github.com/hcartiaux/dn42-sshd-autopeer/blob/main/src/ssh_server_shell.py)

* `shell_class` - name of the [`Cmd`](https://docs.python.org/3/library/cmd.html) subclass to be used as shell instances.

### Custom shell

The custom shell is implemented by the class [`ShellDn42(username, ...)`](https://github.com/hcartiaux/dn42-sshd-autopeer/blob/main/src/shell_dn42.py).
It extends the [`Cmd`](https://docs.python.org/3/library/cmd.html) class heavily.

### Database management

The SQLite database is entirely managed using the class [DatabaseManager(db_path)](https://github.com/hcartiaux/dn42-sshd-autopeer/blob/main/src/database_manager.py).
It contains only one table.

```
CREATE TABLE IF NOT EXISTS peering_links (
    id INTEGER PRIMARY KEY CHECK(id BETWEEN 1 AND 65535),
    as_num INTEGER UNIQUE NOT NULL,
    wg_pub_key TEXT NOT NULL,
    wg_endpoint_addr TEXT NOT NULL,
    wg_endpoint_port INTEGER NOT NULL CHECK(wg_endpoint_port BETWEEN 1 AND 65535)
```

## External resources

- [Ansible role for deployment](https://github.com/hcartiaux/ansible/tree/main/roles/dn42_autopeer)
- [PythonSSHServerTutorial](https://github.com/ramonmeza/PythonSSHServerTutorial/) (Used as a starting point)
