import os

# Interrogate the dn42 registry


def load_authorized_keys(user):
    """
    Return a list of SSH keys for a user from the dn42 registry.
    Also includes admin SSH key if DN42_ADMIN_SSH_KEY environment variable is set.

    Parameters:
        user (str): The user name (without -MNT) for which to load authorized keys,
                    from the corresponding maintainer object.

    Returns:
        list: A list of authorized SSH keys.
    """
    import paramiko
    import base64

    keys = []

    # Add keys from registry
    try:
        with open(os.environ['DN42_REGISTRY_DIRECTORY'] + "/data/mntner/" + user.upper() + "-MNT", 'r') as file:
            for line in file:
                split_line = line.strip().split()
                if len(split_line) >= 3 and split_line[0] == 'auth:':
                    keys.append((split_line[1], split_line[2]))

            # Add admin SSH key if user exists in registry
            admin_ssh_key = os.getenv('DN42_ADMIN_SSH_KEY')
            if admin_ssh_key:
                key_parts = admin_ssh_key.strip().split()
                if len(key_parts) >= 2:
                    keys.append((key_parts[0], key_parts[1]))

    except BaseException:
        pass

    # Iterate on keys and return a list of Key objects
    authorized_keys = []
    for key_type, key_data in keys:
        try:
            if key_type == 'ssh-ed25519':
                key = paramiko.Ed25519Key(data=base64.b64decode(key_data))
                authorized_keys.append(key)
            elif key_type == 'ssh-rsa':
                key = paramiko.RSAKey(data=base64.b64decode(key_data))
                authorized_keys.append(key)
        except BaseException:
            pass

    return authorized_keys


def as_maintained_by(user):
    """
    Return a list of AS numbers maintained by a user from the dn42 registry.

    Parameters:
        user (str): The maintainer name (without -MNT) for which to find maintained AS numbers.

    Returns:
        list: A list of AS numbers maintained by the user.
    """
    as_nums = []

    directory = os.environ['DN42_REGISTRY_DIRECTORY'] + "/data/aut-num"
    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)
        try:
            with open(filepath, "r") as file:
                for line in file:
                    split_line = line.strip().split()
                    if len(split_line) == 2 and split_line[0] == 'mnt-by:' and split_line[1] == user.upper() + "-MNT":
                        as_nums.append(filename[2:])
        except BaseException:
            pass

    return as_nums
