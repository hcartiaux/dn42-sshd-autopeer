import logging
import os
import paramiko
import pty
import select
import subprocess
from src.ssh_server_base import SSHServerBase


class SSHServerPipe(SSHServerBase):
    """
    SSH server that pipes a specified command through an SSH channel.

    Provides a mechanism to execute a shell command and redirect its
    input and output through an SSH connection using a pseudo-terminal.

    Attributes:
        _cmd (str): The shell command to be executed.
        _host_key (paramiko.RSAKey): SSH host key for server authentication.
    """

    def __init__(self, server_interface, cmd, host_key_file, host_key_file_password=None):
        """
        Initialize the SSH pipe server with a command and host key.

        Parameters:
            server_interface: The paramiko server interface to handle SSH connections
                              and the authentication.
            cmd (str): The shell command to be executed for each connection.
            host_key_file (str): Path to the SSH host key private key file.
            host_key_file_password (str, optional): Password for the host key file.
                                                    Defaults to None.
        """
        super(SSHServerPipe, self).__init__(server_interface)
        self._cmd = cmd
        self._host_key = paramiko.RSAKey.from_private_key_file(host_key_file, host_key_file_password)

    def connection_function(self, client, session, channel, username):
        """
        Handle individual SSH connection by piping a command through a pseudo-terminal.

        Manages the lifecycle of a command execution for each incoming SSH connection:
        - Creates a pseudo-terminal
        - Launches the specified command as a subprocess
        - Facilitates bidirectional communication between the SSH channel
          and the command's input/output streams
        - Handles process termination and channel cleanup

        Parameters:
            client (socket.socket): The connected client socket.
            session (paramiko.Transport): The SSH transport session.
            channel (paramiko.Channel): The SSH communication channel.
            username (str): The SSH username.

        Notes:
            - Uses select to handle non-blocking I/O between SSH channel and subprocess
            - Terminates the process if the SSH channel is closed
            - Logs any exceptions during command execution
            - Ensures proper cleanup of channel, session, and file descriptors
        """
        try:
            # Use pty to create a pseudo-terminal for the subprocess
            master_fd, slave_fd = pty.openpty()
            proc = subprocess.Popen(
                self._cmd,
                shell=True,
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                close_fds=True)
            os.close(slave_fd)

            reads = [channel, master_fd]
            while True:
                ready_to_read, _, _ = select.select(reads, [], [], 0.1)

                # Exit the loop if the subprocess has ended
                if proc.poll() is not None:
                    break

                for fd in ready_to_read:
                    # If data is available from the SSH channel, write it to the pseudo-terminal
                    if fd == channel:
                        data = channel.recv(1024)
                        if data:
                            os.write(master_fd, data)
                        else:
                            # Close if no data (client disconnected)
                            channel.shutdown(2)
                            proc.terminate()
                            break

                    # If data is available from the pseudo-terminal, send it to the SSH channel
                    elif fd == master_fd:
                        data = os.read(master_fd, 1024)
                        if data:
                            channel.send(data)

        except BaseException:
            logging.exception(f"[{threading.get_ident()}][SSHServerPipe] Execution error")

        # Close the channel and transport after session ends
        channel.close()
        session.close()
