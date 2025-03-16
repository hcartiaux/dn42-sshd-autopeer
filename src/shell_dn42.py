from cmd import Cmd
from io import StringIO
from re import match
from rich.console import Console
from rich.table import Table
from rich.text import Text
from src.utils_dn42 import *

class ShellDn42(Cmd):

    #############
    # Cmd class properties
    #############

    # The prompt property can be overridden, allowing us to use a custom
    # string to be displayed at the beginning of each line. This will not
    # be included in any input that we get.
    doc_header='Documented commands (type help <topic>):'
    undoc_header='Undocumented commands:'
    misc_header='Misc help sections:'
    ruler='='
    file = None
    # Instead of using input(), this will use stdout.write() and stdin.readline(),
    # this means we can use any TextIO instead of just sys.stdin and sys.stdout.
    use_rawinput=False


    #############
    # Cmd class methods override, with a sanitized output
    #############

    # Constructor that will allow us to set out own stdin and stdout.
    # If stdin or stdout is None, sys.stdin or sys.stdout will be used
    def __init__(self, username, stdin=None, stdout=None, asn="4242420263", server="nl-ams2.flap42.eu"):
        self.username = username
        self.asn      = asn
        self.server   = server
        self.prompt='\r\nAS' + asn + '> '

        # Allowed chars
        self._allowed_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789=:?[]_-.+/ ")
        self._allowed_chars.update({'\x1b', '\x7f', '\r', '\n'})

        # call the base constructor of cmd.Cmd, with our own stdin and stdout
        super(ShellDn42, self).__init__(stdin=stdin, stdout=stdout)

    def default(self, line):
        if line != 'EOF':
            self.sanitized_print('*** Unknown syntax: ' + line)

    def prompt_line(self):
        """Reads an input until Enter is pressed"""
        line=''
        max_line_length=80
        while len(line) < max_line_length:
            ch = self.stdin.read(1).decode("utf-8", "ignore")
            if ch not in self._allowed_chars:
                pass
            elif ch == '\r' or ch == '\n':  # Enter key
                self.stdout.write('\r\n')  # Move to the next line
                break
            elif ch == '\x7f' and len(line) > 0:  # Backspace key
                line = line[:-1]
                self.stdout.write('\b \b')  # Erase the last character
            elif ch == '\t':
                pass
            elif ch == '\x7f' and len(line) == 0:  # Backspace key
                pass
            else:
                self.stdout.write(ch)  # Echo character
                line += ch
        self.stdout.flush()
        return line


    def cmdloop(self, intro=True):
       """Repeatedly issue a prompt, accept input, parse an initial prefix
       off the received input, and dispatch to action methods, passing them
       the remainder of the line as argument.

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
        if cmds:
            self.stdout.write("%s\r\n"%str(header))
            if self.ruler:
                self.stdout.write("%s\r\n"%str(self.ruler * len(header)))
            self.columnize(cmds, maxcol-1)
            self.stdout.write("\r\n")

    # If an empty line is given as input, we just print out a newline.
    # This fixes a display issue when spamming enter.
    def emptyline(self):
        self.sanitized_print('')


    #############
    # Sanitized print methods
    #############

    # These are custom print() functions that will let us utilize the given stdout.
    def print(self, value):
        # make sure the stdout is set.
        # we could add an else which uses the default print(), but I will not
        if self.stdout and not self.stdout.closed:
            self.stdout.write(value)
            self.stdout.flush()

    def sanitized_print(self, output):
        clean_output = '\r\n'.join(line.strip() for line in output.splitlines())
        self.print(clean_output + '\r\n')

    def rich_print(self, rich_object, newline=True):
        console = Console(force_terminal=True)
        output = StringIO()
        console.file = output
        if newline:
            console.print(rich_object, overflow='fold')
            self.sanitized_print(output.getvalue())
        else:
            console.print(rich_object, overflow='fold', end='')
            self.print(output.getvalue())

    def rich_prompt(self, text):
        self.rich_print(text, newline=False)
        return self.prompt_line()

    #############
    # Custom shell commands
    #############

    def do_intro(self, arg=None):
        "Print the introduction message"
        # Message to be output when cmdloop() is called.
        self.emptyline()
        as_nums = as_maintained_by(self.username)
        text = "You are connected as [bold blue]" + self.username.upper() + "-MNT[/] to [bold yellow]" + self.server + " @ AS" + self.asn
        self.rich_print(text)
        self.emptyline()
        table = Table(style="blue")
        table.add_column("Your AS number(s)", no_wrap=True)
        for as_num in as_nums:
            table.add_row(as_num)
        self.rich_print(table)
        self.emptyline()
        text = "Use this shell to configure your BGP peering session."
        self.rich_print(text)
        self.emptyline()
        self.rich_print('Type help or ? to list commands.')

    # even if you don't use the arg parameter, it must be included.
    def do_bye(self, arg):
        "Quit the current shell"
        self.sanitized_print('See You, Space Cowboy!')

        # if a command returns True, the cmdloop() will stop.
        # this acts like disconnecting from the shell.
        return True

    def do_peer_create(self, arg):
        "Create a new peering session"

        peer_list = get_peer_list().keys()
        as_nums = as_maintained_by(self.username)
        as_num           = self.rich_prompt("[bold blue]AS Number                 :[/] ")
        if not match('^[0-9]+$', str(as_num)):
            self.rich_print('[red] :warning: Malformed AS Number (^[0-9]+$)')
            return
        elif as_num not in as_nums:
            self.rich_print('[red] :warning: AS' + as_num + ' is not managed by you')
            return
        elif as_num in peer_list:
            self.rich_print('[red] :warning: Peering session for AS' + as_num + ' already exists.')
            self.rich_print('[red] :warning: List your peering sessions with [italic]peer_list[/italic], remove with [italic]peer_remove[/italic]')
            return

        wg_pub_key       = self.rich_prompt("[bold blue]Wireguard public key      :[/] ")
        if not match('^[0-9a-zA-Z+/]{43}=$', str(wg_pub_key)):
            self.rich_print('[red] :warning: Malformed WireGuard public key (^[0-9a-zA-Z+/]{43}=$)')
            return

        wg_endpoint_addr = self.rich_prompt("[bold blue]Wireguard endpoint address:[/] ")
        if len(get_ipv6(wg_endpoint_addr)) == 0:
            self.rich_print('[red] :warning: The endpoint address should be either an IPv6 address or a domain name with an AAAA record')
            return

        wg_endpoint_port = self.rich_prompt("[bold blue]Wireguard endpoint port   :[/] ")
        if not match('^[0-9]+$', str(wg_endpoint_port)):
            self.rich_print('[red] :warning:  Malformed port number (^[0-9]+$)')
            return

        if peer_create(as_num, wg_pub_key, wg_endpoint_addr, wg_endpoint_port):
            self.rich_print('[green]The peering session has been created for AS' + as_num)
            self.do_peer_config(arg)
        else:
            self.rich_print('[red] :warning:  The peering session could not be created for AS' + as_num)

    def do_peer_config(self, arg):
        "Show your peering session configuration"
        self.sanitized_print('Hello there!')

    def do_peer_list(self, arg):
        "List your existing peering sessions"
        self.emptyline()
        table = Table(title="Your existing peering sessions", style="blue")
        table.add_column("AS number", no_wrap=True)
        table.add_column("Wireguard public key", no_wrap=True)
        table.add_column("Endpoint address", no_wrap=True)
        table.add_column("Endpoint port", no_wrap=True)
        for as_num, peer_info in get_peer_list().items():
            table.add_row(as_num, peer_info['wg_pub_key'], Text(peer_info['wg_endpoint_addr']), peer_info['wg_endpoint_port'])
        self.rich_print(table)

    def do_peer_remove(self, arg):
        "Remove an already configured peering session"
        peer_list = get_peer_list().keys()
        as_num    = self.rich_prompt("[bold blue]AS Number:[/] ")
        if as_num not in peer_list:
            self.rich_print('[red] :warning: There is no peering session for this AS')
            return
        else:
            confirm = self.rich_prompt("[bold blue]Do you really want to remove the peering session of AS " + as_num + "? (YES/NO): ")
            if confirm != 'YES':
                self.rich_print('[red] :warning: Abort peering session removal')
            elif peer_remove(as_num):
                self.rich_print('[bold orange] Peering session of AS' + as_num + ' succesfully removed')
            else:
                self.rich_print('[red] :warning: The peering session could not be removed for AS' + as_num)


    def do_peer_status(self, arg):
        "Print the state of a peering sessions"
        self.sanitized_print('Hello there!')
