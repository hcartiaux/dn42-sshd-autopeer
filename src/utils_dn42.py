import os

# Interrogate the dn42 registry


def load_authorized_keys(user):
    """
    Return a list of SSH keys for a user from the dn42 registry.

    Parameters:
        user (str): The user name (without -MNT) for which to load authorized keys,
                    from the corresponding maintainer object.

    Returns:
        list: A list of authorized SSH keys.
    """
    import paramiko
    import base64
    authorized_keys = []
    try:
        with open(os.environ['DN42_REGISTRY_DIRECTORY'] + "/data/mntner/" + user.upper() + "-MNT", 'r') as file:
            for line in file:
                split_line = line.strip().split()
                if len(split_line) >= 3 and split_line[0] == 'auth:':
                    key_type = split_line[1]
                    key_data = split_line[2]
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
