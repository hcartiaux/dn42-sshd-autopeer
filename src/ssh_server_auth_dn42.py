import paramiko

import os
import base64
from pathlib import Path

DN42_REGISTRY_DIRECTORY = '/home/hcartiaux/repos/perso/git.dn42.dev/dn42/registry/'

def load_authorized_keys(user):
    authorized_keys = []
    try:
        with open(DN42_REGISTRY_DIRECTORY + "/data/mntner/" + user.upper() + "-MNT", 'r') as file:
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
    except:
        pass
    return authorized_keys


# Custom server interface that accepts dn42 maintainers
class SSHServerAuthDn42(paramiko.ServerInterface):
    def check_auth_publickey(self, username, key):
        authorized_keys = load_authorized_keys(username)
        for authorized_key in authorized_keys:
            if authorized_key == key:
                print(f"Authentication successful for {username} with key {key}")
                return paramiko.AUTH_SUCCESSFUL
        print(f"Authentication failed for {username}")
        return paramiko.AUTH_FAILED

    def get_allowed_auths(self, username):
        return 'publickey'

    def check_channel_request(self, kind, chanid):
        if kind == 'session':
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_pty_request(self, channel, term, width, height, pixelwidth, pixelheight, modes):
        return True

    def check_channel_shell_request(self, channel):
        return True

    def get_banner(self):
        motd_path = os.getenv('SSH_MOTD_PATH', '/etc/motd')
        if Path(motd_path).is_file():
            return (Path(motd_path).read_text(), 'en-US')
        else:
            return (None, None)
