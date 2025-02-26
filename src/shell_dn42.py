from cmd import Cmd
from io import StringIO
from rich.console import Console
from rich.table import Table

class ShellDn42(Cmd):

    #############
    # Cmd class properties
    #############

    username = ""

    # Message to be output when cmdloop() is called.
    intro='AS4242420263 SSH Shell. Type help or ? to list commands.\r\n'

    # The prompt property can be overridden, allowing us to use a custom
    # string to be displayed at the beginning of each line. This will not
    # be included in any input that we get.
    prompt='\r\nAS4242420263> '
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
    def __init__(self, username, stdin=None, stdout=None):
        # call the base constructor of cmd.Cmd, with our own stdin and stdout
        self.username = username
        super(ShellDn42, self).__init__(stdin=stdin, stdout=stdout)

    def default(self, line):
        self.sanitized_print('*** Unknown syntax: ' + line)

    def cmdloop(self, intro=None):
       """Repeatedly issue a prompt, accept input, parse an initial prefix
       off the received input, and dispatch to action methods, passing them
       the remainder of the line as argument.

       """

       self.preloop()
       if intro is not None:
           self.intro = intro
       if self.intro:
           self.stdout.write(str(self.intro)+"\n")
       stop = None
       while not stop:
           if self.cmdqueue:
               line = self.cmdqueue.pop(0)
           else:
              self.stdout.write(self.prompt)
              self.stdout.flush()

              line=''
              while True:
                  ch = self.stdin.read(1).decode('utf-8')
                  if ch == '\t':
                      pass
                  elif ch == '\r' or ch == '\n':  # Enter key
                      self.stdout.write('\r\n')  # Move to the next line
                      break
                  elif ch == '\x7f' and len(line) > 0:  # Backspace key
                      self.stdout.write('\b \b')  # Erase the last character
                      line = line[:-1]
                  elif ch == '\x7f' and len(line) == 0:  # Backspace key
                      pass
                  else:
                      line += ch
                      self.stdout.write(ch)  # Echo character
                  self.stdout.flush()


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

    def rich_print(self, rich_object):
        console = Console(force_terminal=True)
        output = StringIO()
        console.file = output
        console.print(rich_object)
        self.sanitized_print(output.getvalue())

    def sanitized_print(self, output):
        clean_output = '\r\n'.join(line.strip() for line in output.splitlines())
        self.print(clean_output + '\r\n')


    #############
    # Custom shell commands
    #############

    # even if you don't use the arg parameter, it must be included.
    def do_bye(self, arg):
        "Quit the current shell"
        self.sanitized_print('See You, Space Cowboy!')

        # if a command returns True, the cmdloop() will stop.
        # this acts like disconnecting from the shell.
        return True

    def do_peer_create(self, arg):
        "Create a new peering session"

        table.add_column("Released", style="cyan", no_wrap=True)
        table.add_column("Title", style="magenta")
        table.add_column("Box Office", justify="right", style="green")

        table.add_row("Dec 20, 2019", "Star Wars: The Rise of Skywalker", "$952,110,690")
        table.add_row("May 25, 2018", "Solo: A Star Wars Story", "$393,151,347")
        table.add_row("Dec 15, 2017", "Star Wars Ep. V111: The Last Jedi", "$1,332,539,889")
        table.add_row("Dec 16, 2016", "Rogue One: A Star Wars Story", "$1,332,439,889")

        self.rich_print(table)

    def do_peer_list(self, arg):
        "List your existing peering sessions"
        self.sanitized_print('Hello there!')

    def do_peer_remove(self, arg):
        "Remove a peering sessions"
        self.sanitized_print('Hello there!')

    def do_peer_status(self, arg):
        "Print the state of a peering sessions"
        self.sanitized_print('Hello there!')
