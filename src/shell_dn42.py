from cmd import Cmd
from io import StringIO
from re import match
from rich.console import Console
from rich.table import Table
from rich.text import Text
from src.database_manager import DatabaseManager
from src.utils_dn42 import *

class ShellDn42(Cmd):
    """
    A custom shell for managing DN42 network peering sessions.

    Provides an interactive command-line interface for creating,
    listing, configuring, and removing peer sessions.
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
        Initialize the DN42 shell with user and network details.

        :param username: User's maintenance handle
        :param stdin: Input stream (default: sys.stdin)
        :param stdout: Output stream (default: sys.stdout)
        :param asn: Autonomous System Number
        :param server: Peering server hostname
        """
        self.username = username
        self.asn = asn
        self.server = server
        self.prompt = f'\r\nAS{asn}> '

        self.db_manager = DatabaseManager()

        # Allowed characters for input sanitization
        self._allowed_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789=:?[]_-.+/ ")
        self._allowed_chars.update({'\x1b', '\x7f', '\r', '\n'})

        # Call the base constructor of cmd.Cmd with our own stdin and stdout
        super(ShellDn42, self).__init__(stdin=stdin, stdout=stdout)

    def default(self, line):
        """
        Handle unknown commands.

        :param line: The input line that was not recognized as a command.
        """
        if line != 'EOF':
            self.sanitized_print('*** Unknown syntax: ' + line)

    def prompt_line(self):
        """
        Reads an input until Enter is pressed.

        :return: The input line read from the user.
        """
        line, max_line_length = '', 80
        while len(line) < max_line_length:
            ch = self.stdin.read(1).decode("utf-8", "ignore")
            if not ch:
                break
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

        :param intro: If True, display the introductory message.
        """
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
                if not len(line):
                    line = 'EOF'
                else:
                    line = line.rstrip('\r\n')
            line = self.precmd(line)
            stop = self.onecmd(line)
            stop = self.postcmd(stop, line)
        self.postloop()

    def print_topics(self, header, cmds, cmdlen, maxcol):
        """Print command topics."""
        if cmds:
            self.stdout.write("%s\r\n" % str(header))
            if self.ruler:
                self.stdout.write("%s\r\n" % str(self.ruler * len(header)))
            self.columnize(cmds, maxcol - 1)
            self.stdout.write("\r\n")

    def emptyline(self):
        """Handle empty line input."""
        self.sanitized_print('')

    #############
    # Sanitized print methods
    #############
    # These are custom print() functions that will let us utilize the given stdout.

    def print(self, value):
        """
        Custom print function that utilizes the given stdout.

        :param value: The value to print.
        """
        if self.stdout and not self.stdout.closed:
            self.stdout.write(value)
            self.stdout.flush()

    def sanitized_print(self, output):
        """
        Print sanitized output.

        :param output: The output string to sanitize and print.
        """
        clean_output = '\r\n'.join(line.strip() for line in output.splitlines())
        self.print(clean_output + '\r\n')

    def rich_print(self, rich_object, newline=True):
        """
        Print rich objects.

        :param rich_object: The rich object to print.
        :param newline: Whether to print a newline at the end.
        """
        console = Console(force_terminal=True)
        output = StringIO()
        console.file = output
        console.print(rich_object, overflow='fold', end='\n' if newline else '')
        if newline:
            self.sanitized_print(output.getvalue())
        else:
            self.print(output.getvalue())

    def rich_prompt(self, text):
        """
        Display a rich prompt and read input.

        :param text: The prompt text to display.
        :return: The input line read from the user.
        """
        self.rich_print(text, newline=False)
        return self.prompt_line()

    #############
    # Custom shell commands
    #############

    def do_intro(self, arg=None):
        """Display welcome message and user's AS information"""
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
        "Quit the current shell"
        self.sanitized_print('See You, Space Cowboy!')
        self.db_manager.close()
        # if a command returns True, the cmdloop() will stop.
        # this acts like disconnecting from the shell.
        return True

    def do_peer_create(self, arg):
        """Interactive process to create a new peering session"""
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

        wg_pub_key       = self.rich_prompt("[bold blue]Wireguard public key      :[/] ")
        if not match('^[0-9a-zA-Z+/]{43}=$', wg_pub_key):
            self.rich_print('[red] :exclamation: Malformed WireGuard public key (^[0-9a-zA-Z+/]{43}=$)')
            return

        wg_endpoint_addr = self.rich_prompt("[bold blue]Wireguard endpoint address:[/] ")
        if not get_ipv6(wg_endpoint_addr):
            self.rich_print('[red] :exclamation: The endpoint address should be either an IPv6 address or a domain name with an AAAA record')
            return

        wg_endpoint_port = self.rich_prompt("[bold blue]Wireguard endpoint port   :[/] ")
        if not match('^[0-9]+$', wg_endpoint_port):
            self.rich_print('[red] :exclamation: Malformed port number (^[0-9]+$)')
            return

        if self.db_manager.peer_create(as_num, wg_pub_key, wg_endpoint_addr, wg_endpoint_port):
            self.rich_print(f'[green]The peering session has been created for AS{as_num}')
            self.rich_print('[green] :information: Display the configuration information with the command [italic]peer_config[/italic]')
        else:
            self.rich_print(f'[red] :exclamation: The peering session could not be created for AS{as_num}')

    def do_peer_config(self, arg):
        """Show your peering session configuration."""
        peer_list = self.db_manager.get_peer_list(self.username).keys()
        if len(peer_list) == 1:
            as_num = next(iter(peer_list))
        else:
            as_num = self.rich_prompt("[bold blue]AS Number:[/] ")
            if as_num not in peer_list:
                self.rich_print('[red] :exclamation: There is no peering session for this AS')
                self.rich_print('[green] :information: List your peering sessions with [italic]peer_list[/italic], create a new one with [italic]peer_create[/italic]')
                return

        peer_config = self.db_manager.get_peer_config(self.username, as_num)
        table_remote = Table(style='blue')
        table_remote.add_column("Link config.", no_wrap=True)
        table_remote.add_column(f"AS{as_num}", no_wrap=True)
        table_remote.add_row('Wg pub key', peer_config['wg_pub_key'])
        table_remote.add_row('Wg Endpoint addr.', Text(peer_config['wg_endpoint_addr']))
        table_remote.add_row('Wg Endpoint port', peer_config['wg_endpoint_port'])
        table_remote.add_row('Link-local address', Text(peer_config['link_local']))
        self.rich_print(table_remote)

        as_id = self.db_manager.get_asn_id(as_num)
        local_config = get_local_config(as_id)
        table_local = Table(style='yellow')
        table_local.add_column("Link config.", no_wrap=True)
        table_local.add_column(f"AS{self.asn}", no_wrap=True)
        table_local.add_row('Wg pub key', local_config['wg_pub_key'])
        table_local.add_row('Wg Endpoint addr.', Text(local_config['wg_endpoint_addr']))
        table_local.add_row('Wg Endpoint port', local_config['wg_endpoint_port'])
        table_local.add_row('Link-local address', Text(local_config['link_local']))
        self.rich_print(table_local)

        table_wg = Table(style='blue')
        table_wg.add_column(f"Wireguard configuration for AS{as_num}", no_wrap=True)
        table_wg.add_row(Text(gen_wireguard_config(self.username, as_id, peer_config['wg_endpoint_port'], peer_config['link_local'])))
        self.rich_print(table_wg)

        table_bird = Table(style='blue')
        table_bird.add_column(f"Bird configuration for AS{as_num}", no_wrap=True)
        table_bird.add_row(Text(gen_bird_config(self.username, as_num, as_id)))
        self.rich_print(table_bird)

    def do_peer_list(self, arg):
        """List your existing peering sessions."""
        self.emptyline()
        table = Table(title="Your existing peering sessions", style="blue")
        table.add_column("AS number", no_wrap=True)
        table.add_column("Wireguard public key", no_wrap=True)
        table.add_column("Endpoint address", no_wrap=True)
        table.add_column("Endpoint port", no_wrap=True)
        for as_num, peer_info in self.db_manager.get_peer_list(self.username).items():
            table.add_row(
                as_num,
                peer_info['wg_pub_key'],
                Text(peer_info['wg_endpoint_addr']),
                peer_info['wg_endpoint_port'])
        self.rich_print(table)

    def do_peer_remove(self, arg):
        """
        Remove an already configured peering session.

        :param arg: Optional argument (not used).
        """
        peer_list = self.db_manager.get_peer_list(self.username).keys()
        if len(peer_list) == 1:
            as_num = next(iter(peer_list))
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
        Print the state of a peering session.

        :param arg: Optional argument (not used).
        """
        peer_list = self.db_manager.get_peer_list(self.username).keys()
        if len(peer_list) == 1:
            as_num = next(iter(peer_list))
        else:
            as_num = self.rich_prompt("[bold blue]AS Number:[/] ")
            if as_num not in peer_list:
                self.rich_print('[red] :exclamation: There is no peering session for this AS')
                self.rich_print('[green] :information: List your peering sessions with [italic]peer_list[/italic], create a new one with [italic]peer_create[/italic]')
                return

        cmd_output = peer_status(as_num)
        table = Table(style="yellow")
        table.add_column(
            f"Peering session status on {self.server}",
            no_wrap=False)
        table.add_row(Text(cmd_output))
        self.rich_print(table)
