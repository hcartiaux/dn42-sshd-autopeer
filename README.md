# dn42 as4242420263 custom SSHD service

This is my custom SSH server implementation using [Paramiko](https://github.com/paramiko/paramiko/).

## Prerequisites

* Python 3
* Paramiko

## Usage

```
usage: dn42-sshd [-h] (--gaming | --peering)

options:
  -h, --help  show this help message and exit
  --gaming    Start the gaming server
  --peering   Start the auto peering server
```

## Environment variables

* `SSH_PORT`: default is 8022
* `SSH_MOTD_PATH`: custom `motd` file
* `DN42_REGISTRY_DIRECTORY`: path of a local git clone of [the dn42 registry repository](https://git.dn42.dev/dn42/registry), used for the peering service authentication

## Internals

### Authentication methods

#### Anonymous, class `SSHServerAuthNone`

Accept all connections

#### Dn42, class `SSHServerAuthDn42`

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

## Resources

* [ramonmeza/PythonSSHServerTutorial](https://github.com/ramonmeza/PythonSSHServerTutorial/)
