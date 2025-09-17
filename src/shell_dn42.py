import logging
import os
import threading
from cmd import Cmd
from io import StringIO
from re import match
from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich.markdown import Markdown
from src.database_manager import DatabaseManager
from src.utils_dn42 import as_maintained_by
from src.utils_config import get_local_config, gen_wireguard_peer_config, gen_bird_peer_config, peer_status
from src.utils_network import get_ipv6, validate_ipv6, validate_link_local_ipv6


class ShellDn42(Cmd):
    """
    A custom shell for managing DN42 network peering sessions.

    Provides an interactive command-line interface for creating,
    listing, configuring, and removing peer sessions.

    Attributes:
        username (str): User's maintenance handle.
        asn (str): Autonomous System Number.
        server (str): Peering server hostname.
        db_manager (DatabaseManager): Database management instance.
        _allowed_chars (set): Set of allowed input characters.
    """

    #############
    # Cmd class properties
    #############

    # The prompt property can be overridden, allowing us to use a custom
    # string to be displayed at the beginning of each line. This will not
    # be included in any input that we get.
    doc_header = 'Documented commands (type help <topic>):'
    undoc_header = 'Undocumented commands:'
    misc_header = 'Misc help sections:'
    ruler = '='
    file = None
    # Instead of using input(), this will use stdout.write() and stdin.readline(),
    # this means we can use any TextIO instead of just sys.stdin and sys.stdout.
    use_rawinput = False

    #############
    # Cmd class methods override, with a sanitized output
    #############

    # Constructor that will allow us to set out own stdin and stdout.
    # If stdin or stdout is None, sys.stdin or sys.stdout will be used

    def __init__(
            self,
            username,
            stdin=None,
            stdout=None,
            asn="4242420263",
            server="nl-ams2.flap42.eu"):
        """
        Initialize the shell with user and network details.

        Parameters:
            username (str): User's maintenance handle for DN42 network.
            stdin (file, optional): Input stream for shell operations.
                                    Defaults to sys.stdin.
            stdout (file, optional): Output stream for shell operations.
                                     Defaults to sys.stdout.
            asn (int, optional): Autonomous System Number associated with the user.
                                 Defaults to None.
            server (str, optional): Hostname of the peering server.
                                    Defaults to None.
        """
        self.username = username
        self.asn = asn
        self.server = server
        self.prompt = f'\r\nAS{asn}> '

        self.db_manager = DatabaseManager()

        # Allowed characters for input sanitization
        self._allowed_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789=:?[]_-.+/ ")
        self._allowed_chars.update({'\x7f', '\r', '\n'})

        # Call the base constructor of cmd.Cmd with our own stdin and stdout
        super(ShellDn42, self).__init__(stdin=stdin, stdout=stdout)

    def default(self, line):
        """
        Handle unknown commands.

        This method is called when an unrecognized command is entered
        in the shell interface, providing a way to manage unexpected input.

        Parameters:
            line (str): The complete input line that was not recognized
                        as a valid command by the shell.
        """
        if line != 'EOF':
            self.sanitized_print('*** Unknown syntax: ' + line)

    def prompt_line(self):
        """
        Reads an input until Enter is pressed.

        Returns:
            str: The complete input line read from the user before pressing Enter.
        """
        line, max_line_length = '', 80
        while len(line) < max_line_length:
            ch = self.stdin.read(1).decode("utf-8", "ignore")
            if not ch:
                break
            # Strip escape sequences
            if ord(ch) == int("1b", 16):
                self.stdin.read(2).decode("utf-8", "ignore")
                continue
            if ch not in self._allowed_chars:
                continue
            if ch in {'\r', '\n'}:  # Enter key
                self.stdout.write('\r\n')  # Move to the next line
                break
            if ch == '\x7f' and len(line) > 0:  # Backspace key
                line = line[:-1]
                self.stdout.write('\b \b')  # Erase the last character
            elif ch == '\x7f' and len(line) == 0:  # Backspace key and line is empty
                continue
            else:
                self.stdout.write(ch)  # Echo character
                line += ch
        self.stdout.flush()
        return line

    def cmdloop(self, intro=True):
        """
        Main command loop.

        Repeatedly issue a prompt, accept input, parse an initial prefix
        off the received input, and dispatch to action methods, passing them
        the remainder of the line as argument.

        Parameters:
            intro (bool, optional): Controls whether to display the introduction message.
                                    Defaults to True.
        """
        try:
            self.preloop()
            if intro:
                self.do_intro()
            stop = None
            while not stop:
                if self.cmdqueue:
                    line = self.cmdqueue.pop(0)
                else:
                    self.stdout.write(self.prompt)
                    self.stdout.flush()
                    line = self.prompt_line()
                    if not line:
                        line = 'EOF'
                    else:
                        line = line.rstrip('\r\n')
                line = self.precmd(line)
                stop = self.onecmd(line)
                stop = self.postcmd(stop, line)
            self.postloop()
        except OSError as e:
            if "Socket is closed" in str(e):
                logging.warning(f"[{threading.get_ident()}][ShellDn42] Socket is closed")
            else:
                logging.exception(f"[{threading.get_ident()}][ShellDn42] ")
        except BaseException:
            logging.exception(f"[{threading.get_ident()}][ShellDn42] ")
        finally:
            self.db_manager.close()

    def print_topics(self, header, cmds, cmdlen, maxcol):
        """
        Print command topics
        """
        if cmds:
            self.stdout.write("%s\r\n" % str(header))
            if self.ruler:
                self.stdout.write("%s\r\n" % str(self.ruler * len(header)))
            self.columnize(cmds, maxcol - 1)
            self.stdout.write("\r\n")

    def emptyline(self):
        """
        Handle empty line input.
        """
        self.sanitized_print('')

    #############
    # Sanitized print methods
    #############
    # These are custom print() functions that will let us utilize the given stdout.

    def print(self, value):
        """
        Custom print function that utilizes the given stdout.

        Parameters:
            value (str): The value to be printed to the output stream.
        """
        if self.stdout and not self.stdout.closed:
            self.stdout.write(value)
            self.stdout.flush()

    def sanitized_print(self, value):
        """
        Print sanitized output by cleaning and formatting the input.

        Strips whitespace from each line of the input and ensures
        consistent line ending format.

        Parameters:
            value (str): The string to sanitize and print.
        """
        clean_value = '\r\n'.join(line.strip() for line in value.splitlines())
        self.print(clean_value + '\r\n')

    def rich_print(self, rich_object, newline=True):
        """
        Print rich objects.

        Utilizes the Rich library to print objects with enhanced formatting,

        Parameters:
            rich_object: The rich object to print.
            newline (bool, optional): Whether to print a newline at the end.
                                      Defaults to True.
        """
        console = Console(force_terminal=True)
        output = StringIO()
        console.file = output
        console.print(rich_object, overflow='fold', end='\n' if newline else '')
        if newline:
            self.sanitized_print(output.getvalue())
        else:
            self.print(output.getvalue())

    def rich_prompt(self, rich_object):
        """
        Display a rich prompt and read user input.

        Prints the prompt using rich formatting and then
        reads the user's input line.

        Parameters:
            rich_object: The rich object to print before the prompt.

        Returns:
            str: The input line read from the user.
        """
        self.rich_print(rich_object, newline=False)
        return self.prompt_line()

    #############
    # Custom shell commands
    #############

    def do_intro(self, arg=None):
        """
        Display welcome message and user's AS information
        """

        as_nums = as_maintained_by(self.username)

        # Welcome and connection details
        self.emptyline()
        self.rich_print(f"Welcome to Flip Flap Network (AS{self.asn}) automated peering service")
        self.rich_print(f"You are connected as [bold blue]{self.username.upper()}-MNT[/] to [bold yellow]{self.server} @ AS{self.asn}")
        self.emptyline()

        # Display AS numbers
        table = Table(style="blue")
        table.add_column("Your AS number(s)", no_wrap=True)
        for as_num in as_nums:
            table.add_row(as_num)
        self.rich_print(table)

        # Additional guidance
        self.emptyline()
        self.rich_print("Use this shell to configure your BGP peering session.")
        self.emptyline()
        self.rich_print('Type help or ? to list commands.')

    def do_bye(self, arg):
        """
        Quit the current shell
        """
        self.sanitized_print('See You, Space Cowboy!')
        self.db_manager.close()
        # if a command returns True, the cmdloop() will stop.
        # this acts like disconnecting from the shell.
        return True

    def do_peer_create(self, arg):
        """
        Interactive process to create a new peering session.
        """
        """
        Steps:
        - Validating AS number
        - Collecting WireGuard public key
        - Gathering endpoint address and port
        - Attempting to create the peer in the database
        """
        peer_list = self.db_manager.get_peer_list(self.username).keys()
        as_nums = as_maintained_by(self.username)
        as_num           = self.rich_prompt("[bold blue]AS Number                 :[/] ")
        if not match('^[0-9]+$', str(as_num)):
            self.rich_print('[red] :exclamation: Malformed AS Number (^[0-9]+$)')
            return
        elif as_num not in as_nums:
            self.rich_print('[red] :exclamation: AS' + as_num + ' is not managed by you')
            return
        elif as_num in peer_list:
            self.rich_print('[red] :exclamation: Peering session for AS' + as_num + ' already exists.')
            self.rich_print('[green] :information: List your peering sessions with [italic]peer_list[/italic], remove with [italic]peer_remove[/italic]')
            return

        wg_pub_key       = self.rich_prompt("[bold blue]WireGuard public key      :[/] ")
        if not match('^[0-9a-zA-Z+/]{43}=$', wg_pub_key):
            self.rich_print('[red] :exclamation: Malformed WireGuard public key (^[0-9a-zA-Z+/]{43}=$)')
            return

        wg_endpoint_addr = self.rich_prompt("[bold blue]WireGuard endpoint address:[/] ")
        ipv6_list = get_ipv6(wg_endpoint_addr)
        if not ipv6_list:
            self.rich_print('[red] :exclamation: The endpoint address should be either an IPv6 address or a domain name with an AAAA record')
            return

        forbidden_net = os.environ['DN42_RESERVED_NETWORK']
        for ipv6 in ipv6_list:
            if not validate_ipv6(ipv6, [forbidden_net] if forbidden_net else []):
                self.rich_print(f'[red] :exclamation: The endpoint address {ipv6} is forbidden')
                return

        wg_endpoint_port = self.rich_prompt("[bold blue]WireGuard endpoint port   :[/] ")
        if not match('^[0-9]+$', wg_endpoint_port):
            self.rich_print('[red] :exclamation: Malformed port number (^[0-9]+$)')
            return
        if not (1 <= int(wg_endpoint_port) <= 65535):
            self.rich_print('[red] :exclamation: Malformed port number ([1;65535])')
            return

        user_link_local = None
        self.rich_print("[yellow]Optional: Provide your own link-local IPv6 address (fe80::/10 range)")
        self.rich_print("[yellow]Leave empty to use automatically generated address")
        user_input = self.rich_prompt("[bold blue]Link-local IPv6 (optional):[/] ")

        if user_input.strip():
            if not validate_link_local_ipv6(user_input.strip()):
                local_link_local = os.environ.get('DN42_WG_LOCAL_ADDRESS', 'fe80::263')
                self.rich_print(f'[red] :exclamation: Invalid link-local IPv6 address. Must be in fe80::/10 range and different from local address ({local_link_local})')
                return
            user_link_local = user_input.strip()

        if self.db_manager.peer_create(as_num, wg_pub_key, wg_endpoint_addr, wg_endpoint_port, user_link_local):
            self.emptyline()
            self.rich_print(f'[green]The peering session has been registered for AS{as_num}')
            self.rich_print('[green] :information: Peering sessions are created every 5 minutes')
            self.rich_print('[green] :information: Display the system configuration with the command [italic]peer_config[/italic]')
        else:
            self.rich_print(f'[red] :exclamation: The peering session could not be created for AS{as_num}')

    def do_peer_config(self, arg):
        """
        Show the configuration for an existing peering session.
        """
        """
        Displays detailed configuration information including:
        - Remote peer configuration
        - Local configuration
        - WireGuard configuration
        - Bird configuration
        """
        peer_list = self.db_manager.get_peer_list(self.username).keys()
        if len(peer_list) == 1:
            as_num = next(iter(peer_list))
        elif len(peer_list) == 0:
            self.rich_print('[red] :exclamation: There is no existing peering session')
            self.rich_print('[green] :information: Create a new peering session with [italic]peer_create[/italic]')
            return
        else:
            as_num = self.rich_prompt("[bold blue]AS Number:[/] ")
            if as_num not in peer_list:
                self.rich_print('[red] :exclamation: There is no peering session for this AS')
                self.rich_print('[green] :information: List your peering sessions with [italic]peer_list[/italic], create a new one with [italic]peer_create[/italic]')
                return

        peer_config = self.db_manager.get_peer_config(as_num)

        # Remote peer configuration table
        table_remote = Table(style='blue')
        table_remote.add_column("Link config.", no_wrap=True)
        table_remote.add_column(f"AS{as_num}", no_wrap=True)
        table_remote.add_row('WG pub key', peer_config['wg_pub_key'])
        table_remote.add_row('WG Endpoint addr.', Text(peer_config['wg_endpoint_addr']))
        table_remote.add_row('WG Endpoint port', peer_config['wg_endpoint_port'])
        table_remote.add_row('Link-local address', Text(peer_config['ll_address']))
        self.rich_print(table_remote)

        # Local configuration table
        as_id = peer_config['id']
        local_config = get_local_config(as_id, peer_config['ll_address'])
        table_local = Table(style='yellow')
        table_local.add_column("Link config.", no_wrap=True)
        table_local.add_column(f"AS{self.asn}", no_wrap=True)
        table_local.add_row('WG pub key', local_config['wg_pub_key'])
        table_local.add_row('WG Endpoint addr.', Text(local_config['wg_endpoint_addr']))
        table_local.add_row('WG Endpoint port', local_config['wg_endpoint_port'])
        table_local.add_row('Link-local address', Text(local_config['ll_address']))
        self.rich_print(table_local)

        self.emptyline()

        # WireGuard configuration table
        wg_config = f"**WireGuard configuration for AS{as_num}**\n"
        wg_config += "```INI" + gen_wireguard_peer_config(as_num) + "```"
        self.rich_print(Markdown(wg_config))

        self.emptyline()

        # Bird configuration table
        bird_config = f"  **Bird configuration for AS{as_num}**\n"
        bird_config += "```unixconfig" + gen_bird_peer_config(as_num) + "```"
        self.rich_print(Markdown(bird_config))

    def do_peer_list(self, arg):
        """
        List your existing peering sessions.
        """
        """
        Displays a table with details of all current peering sessions,
        including AS number, WireGuard public key, and endpoint information.
        """
        self.emptyline()
        table = Table(title="Your existing peering sessions", style="blue")
        table.add_column("AS Number", no_wrap=True)
        table.add_column("WireGuard Public Key")
        table.add_column("Endpoint Address", no_wrap=True)
        table.add_column("Port", no_wrap=True)
        for as_num, peer_info in self.db_manager.get_peer_list(self.username).items():
            table.add_row(
                as_num,
                peer_info['wg_pub_key'],
                Text(peer_info['wg_endpoint_addr']),
                peer_info['wg_endpoint_port']
            )
        self.rich_print(table)

    def do_peer_remove(self, arg):
        """
        Remove an existing peering session.
        """
        """
        Guides the user through the process of removing a peering session:
        - Selects the AS number to remove
        - Requests user confirmation
        - Attempts to remove the peering session from the database
        """
        peer_list = self.db_manager.get_peer_list(self.username).keys()
        if len(peer_list) == 1:
            as_num = next(iter(peer_list))
        elif len(peer_list) == 0:
            self.rich_print('[red] :exclamation: There is no existing peering session')
            self.rich_print('[green] :information: Create a new peering session with [italic]peer_create[/italic]')
            return
        else:
            as_num = self.rich_prompt("[bold blue]AS Number:[/] ")
            if as_num not in peer_list:
                self.rich_print('[red] :exclamation: There is no peering session for this AS')
                self.rich_print('[green] :information: List your peering sessions with [italic]peer_list[/italic], create a new one with [italic]peer_create[/italic]')
                return

        confirm = self.rich_prompt(f"[bold red]Do you really want to remove the peering session of AS{as_num}? (YES/NO): ")
        if confirm != 'YES':
            self.rich_print('[red] :exclamation: Abort peering session removal')
        elif self.db_manager.peer_remove(as_num):
            self.rich_print(f'Peering session of AS{as_num} successfully removed')
        else:
            self.rich_print(f'[red] :exclamation: The peering session could not be removed for AS{as_num}')

    def do_peer_status(self, arg):
        """
        Print the current status of a peering session.
        """
        """
        Retrieves and displays the status of a specific peering session:
        - Selects the AS number
        - Retrieves status information
        - Displays the status in a formatted table
        """
        peer_list = self.db_manager.get_peer_list(self.username).keys()
        if len(peer_list) == 1:
            as_num = next(iter(peer_list))
        elif len(peer_list) == 0:
            self.rich_print('[red] :exclamation: There is no existing peering session')
            self.rich_print('[green] :information: Create a new peering session with [italic]peer_create[/italic]')
            return
        else:
            as_num = self.rich_prompt("[bold blue]AS Number:[/] ")
            if as_num not in peer_list:
                self.rich_print('[red] :exclamation: There is no peering session for this AS')
                self.rich_print('[green] :information: List your peering sessions with [italic]peer_list[/italic], create a new one with [italic]peer_create[/italic]')
                return

        cmd_output = peer_status(as_num)
        self.rich_print(Markdown("````\n" + cmd_output))
