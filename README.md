# dn42 as4242420263 custom SSHD service

This is my custom SSH server implementation using `Python 3` and [`Paramiko`](https://github.com/paramiko/paramiko/).

## Usage

```
usage: dn42-sshd [-h] (--gaming | --peering)

options:
  -h, --help  show this help message and exit
  --gaming    Start the gaming server
  --peering   Start the auto peering server
```

## Environment variables

* `DN42_SSH_LISTEN_ADDRESS`: Default is `::1`
* `DN42_SSH_PORT`: default is `8022`
* `DN42_SERVER`: public domain name of the server
* `DN42_SSH_MOTD_PATH`: path of a custom `motd` file
* `DN42_DB_PATH`: path of the sqlite database file
* `DN42_REGISTRY_DIRECTORY`: path of a local git clone of [the dn42 registry repository](https://git.dn42.dev/dn42/registry), used for the peering service authentication
* `DN42_ASN`: Dn42 Autonomous System Number
* `DN42_WG_PUB_KEY`: Wireguard public key used for all the tunnels
* `DN42_WG_LINK_LOCAL`: link-local IPv6 base address used on the wireguard interfaces, without the last 4 bytes
* `DN42_WG_BASE_PORT`: Wireguard base port

## Internals

### Authentication methods

#### Anonymous, class `SSHServerAuthNone`

Accept all connections

#### Dn42 registry, class `SSHServerAuthDn42`

Accept connections based on the [dn42 maintainer objects](https://dn42.eu/howto/Registry-Authentication#how-authentication-works_authentication-using-an-ssh-key_auth-attribute-format-when-using-an-ssh-key), using the defined public key(s)

* username: lowercase maintainer name, without the `-MNT` suffix
* public keys: supports `ssh-rsa` and `ssh-ed25519` keys defined in the `auth` field

### Applications

#### Piping, class `SSHServerPipe(cmd, host_key_file)`

* `cmd` - command to be executed and piped to the user
* `host_key_file` - path of the ssh host key file

#### Shell, class `SSHServerShell(shell_class, host_key_file)`

* `shell_class` - name of the [Cmd](https://docs.python.org/3/library/cmd.html) subclass to be used as shell instances.
* `host_key_file` - path of the ssh host key file

## External resource

I've used [ramonmeza/PythonSSHServerTutorial](https://github.com/ramonmeza/PythonSSHServerTutorial/),
which describes how-to create a SSH server using Python 3 and Paramiko, as a starting point for this project.
