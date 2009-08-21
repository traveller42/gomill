"""Go Text Protocol support (engine side).

Based on GTP 'draft version 2' (see <http://www.lysator.liu.se/~gunnar/gtp/>),
and gnugo 3.7 as 'reference implementation'.

"""

import re
import sys
import os

from gomill_common import *
from gomill import compact_tracebacks


class GtpError(StandardError):
    """Error reported by a command handler."""

class GtpFatalError(GtpError):
    """Fatal error reported by a command handler."""

class GtpQuit(Exception):
    """Request to end session from a command handler."""




### Handler support

def interpret_boolean(arg):
    """Interpret a string representing a boolean, as specified by GTP.

    Returns a Python bool.

    Raises GtpError with an appropriate message if 'arg' isn't a valid GTP
    boolean specification.

    """
    try:
        return {'true': True, 'false': False}[arg]
    except KeyError:
        raise GtpError("invalid boolean: '%s'" % arg)

def interpret_colour(arg):
    """Interpret a string representing a colour, as specified by GTP.

    Returns 'b' or 'w'.

    Raises GtpError with an appropriate message if 'arg' isn't a valid GTP
    colour specification.

    """
    try:
        return {'w': 'w', 'white': 'w', 'b': 'b', 'black': 'b'}[arg.lower()]
    except KeyError:
        raise GtpError("invalid colour: '%s'" % arg)

def interpret_vertex(arg, board_size):
    """Interpret a string representing a vertex, as specified by GTP.

    Returns a pair of coordinates (row, col) in range(0, board_size),
    or None for a pass.

    Raises GtpError with an appropriate message if 'arg' isn't a valid GTP
    vertex specification for a board of size 'board_size'.

    """
    assert 0 < board_size <= 25
    s = arg.lower()
    if s == "pass":
        return None
    try:
        col_c = s[0]
        if (not "a" <= col_c <= "z") or col_c == "i":
            raise ValueError
        if col_c > "i":
            col = ord(col_c) - ord("b")
        else:
            col = ord(col_c) - ord("a")
        row = int(s[1:]) - 1
        if row < 0:
            raise ValueError
    except (IndexError, ValueError):
        raise GtpError("invalid vertex: '%s'" % s)
    if not (col < board_size and row < board_size):
        raise GtpError("vertex is off board: '%s'" % s)
    return row, col

_gtp_int_max = 2**31-1

def interpret_int(arg):
    """Interpret a string representing an int, as specified by GTP.

    Returns a Python int.

    Raises GtpError with an appropriate message if 'arg' isn't a valid GTP
    int specification.

    Negative numbers are returned as -1. Numbers above 2**31-1 are returned as
    2**31-1.

    """
    # I can't tell how gnugo treats negative numbers, except that it counts them
    # as integers not in a suitable range for boardsize. The clipping of high
    # integers is what it does for command ids.
    try:
        result = int(arg)
    except ValueError:
        raise GtpError("invalid int: '%s'" % arg)
    if result < 0:
        result = -1
    elif result > _gtp_int_max:
        result = _gtp_int_max
    return result

def interpret_float(arg):
    """Interpret a string representing a float, as specified by GTP.

    Returns a Python float.

    Raises GtpError with an appropriate message if 'arg' isn't a valid GTP
    float specification.

    Accepts strings accepted as a float by the platform libc. The result might
    be a special value such as NaN or inf.

    """
    # Gnugo accepts 'NaN', so we will too.
    try:
        result = float(arg)
    except ValueError:
        raise GtpError("invalid float: '%s'" % arg)
    return result

def format_gtp_boolean(b):
    """Format a Python bool in GTP format."""
    if b:
        return "true"
    else:
        return "false"

column_letters = "ABCDEFGHJKLMNOPQRSTUVWXZ"
def format_vertex_from_coords(row, col):
    """Format coordinates as a GTP vertex string."""
    return column_letters[col] + str(row+1)

def report_bad_arguments():
    """Raise GtpError with a suitable message for invalid arguments.

    Note that gnugo (3.7) seems to ignore extra arguments in practice; it's
    supposed to be the reference implementation, so perhaps you should do the
    same.

    """
    raise GtpError("invalid arguments")



### Parsing

_remove_controls_re = re.compile(r"[\x00-\x08\x0a-\x1f\x7f]")
_remove_response_controls_re = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
_normalise_whitespace_re = re.compile(r"[\x09\x20]+")
_command_id_re = re.compile(r"^-?[0-9]+")

def _preprocess_line(s):
    """Clean up an input line and normalise whitespace."""
    s = s.partition("#")[0]
    s = _remove_controls_re.sub("", s)
    s = _normalise_whitespace_re.sub(" ", s)
    return s

def _clean_response(response):
    """Clean up a proposed response."""
    if response is None:
        return ""
    s = str(response).rstrip()
    s = s.replace("\n\n", "\n.\n")
    s = _remove_response_controls_re.sub("", s)
    s = s.replace("\t", " ")
    return s

def _parse_line(line):
    """Parse a nonempty input line.

    Returns a tuple (command_id, command, arguments)
    command_id -- string
    command    -- string
    arguments  -- list of strings

    Returns command None if the line is to be treated as empty after all.

    Behaviour in error cases is copied from gnugo 3.7.

    """
    tokens = line.split()
    s = tokens[0]
    command_id = None
    id_match = _command_id_re.match(s)
    if id_match:
        command = s[id_match.end():]
        if command == "":
            try:
                command = tokens[1]
            except IndexError:
                command = None
            args = tokens[2:]
        else:
            args = tokens[1:]
        command_id = id_match.group()
        int_command_id = int(command_id)
        if int_command_id < 0:
            command_id = None
        elif int_command_id > _gtp_int_max:
            command_id = str(_gtp_int_max)
    else:
        command_id = None
        command = s
        args = tokens[1:]
    return command_id, command, args


class Gtp_engine_protocol(object):
    """Implementation of the engine side of the GTP protocol.

    Sample use:
      e = Gtp_engine_protocol()
      e.add_protocol_commands()
      e.add_command('foo', foo_handler)
      response, end_session = e.handle_line('foo w d5')


    GTP commands are dispatched to _handler functions_. These can by any Python
    callable. The handler function is passed a single parameter, which is a list
    of strings representing the command's arguments (nonempty strings of
    printable non-whitespace characters).

    The handler should return the response to sent to the controller. You can
    use either None or the empty string for an empty response. If the returned
    value isn't suitable to be used directly as a GTP response, it will be
    'cleaned up' so that it can be.

    To report an error, they should raise GtpError with an appropriate message.

    To end the session, they should raise GtpQuit or GtpFatalError. Any
    exception message will be reported, as a success or failure response
    respectively.

    If they raise another exception (instance of StandardError), this will be
    reported as 'internal error', followed by the exception description and
    traceback.

    """

    def __init__(self):
        self.handlers = {}

    def add_command(self, command, handler):
        """Register the handler function for a command."""
        self.handlers[command] = handler

    def add_commands(self, handlers):
        """Register multiple handler functions.

        handlers -- dict command name -> handler

        """
        self.handlers.update(handlers)

    def list_commands(self):
        """Return a list of known commands."""
        return sorted(self.handlers)

    def _do_command(self, command, args):
        try:
            handler = self.handlers[command]
        except KeyError:
            raise GtpError("unknown command")
        try:
            return handler(args)
        except GtpError:
            raise
        except StandardError:
            raise GtpError("internal error\n%s" %
                           compact_tracebacks.format_traceback(skip=1))

    def run_command(self, command, args):
        """Run the handler for a command directly.

        You can use this from Python code to interact with a GTP engine without
        going via the GTP line-based syntax.

        command    -- string (command name)
        arguments  -- list of strings (or None)

        Returns a tuple (is_error, response, end_session)

        is_error    -- bool
        response    -- the GTP response
        end_session -- bool

        The response is a string, not ending with a newline (or any other
        whitespace).

        If end_session is true, the engine doesn't want to receive any more
        commands.

        """
        try:
            response = self._do_command(command, args)
        except GtpQuit, e:
            is_error = False
            response = e
            end_session = True
        except GtpFatalError, e:
            is_error = True
            response = str(e)
            if response == "":
                response = "unspecified fatal error"
            end_session = True
        except GtpError, e:
            is_error = True
            response = str(e)
            if response == "":
                response = "unspecified error"
            end_session = False
        else:
            is_error = False
            end_session = False
        return is_error, _clean_response(response), end_session

    def handle_line(self, line):
        """Handle a line of input.

        line -- 8-bit string containing one line of input.

        The line may or may not contain the terminating newline. Any internal
        newline is discarded.

        Returns a pair (response, end_session)

        response    -- the GTP response to be sent to the controller
        end_session -- bool

        response is normally a string containing a well-formed GTP response
        (ending with '\n\n'). It may also be None, in which case nothing at all
        should be sent to the controller.

        If end_session is true, the GTP session should be terminated.

        """
        normalised = _preprocess_line(line)
        if normalised == "" or normalised == " ":
            return None, False
        command_id, command, args = _parse_line(normalised)
        if command is None:
            # Line with only a command id
            return None, False
        is_error, cleaned_response, end_session = \
            self.run_command(command, args)
        if is_error:
            response_code = "?"
        else:
            response_code = "="
        if command_id is not None:
            response_prefix = response_code + command_id
        else:
            response_prefix = response_code
        if cleaned_response == "":
            response_sep = ""
        else:
            response_sep = " "
        response = "%s%s%s\n\n" % (
            response_prefix, response_sep, cleaned_response)
        return response, end_session

    def handle_known_command(self, args):
        # Imitating gnugo's behaviour for bad args
        try:
            result = (args[0] in self.handlers)
        except IndexError:
            result = False
        return format_gtp_boolean(result)

    def handle_list_commands(self, args):
        # Gnugo ignores any arguments
        return "\n".join(self.list_commands())

    def handle_protocol_version(self, args):
        # Gnugo ignores any arguments
        return "2"

    def handle_quit(self, args):
        # Gnugo ignores any arguments
        raise GtpQuit

    def add_protocol_commands(self):
        """Add the standard protocol-level commands.

        These are the commands which can be handled without reference to the
        underlying engine:
          known_command
          list_commands
          protocol_version
          quit

        """
        self.add_command("known_command", self.handle_known_command)
        self.add_command("list_commands", self.handle_list_commands)
        self.add_command("protocol_version", self.handle_protocol_version)
        self.add_command("quit", self.handle_quit)



### Session loop

def _run_gtp_session(engine, read, write):
    while True:
        try:
            line = read()
        except EOFError:
            break
        response, end_session = engine.handle_line(line)
        if response is not None:
            write(response)
        if end_session:
            break

def run_gtp_session(engine, src, dst):
    """Run a GTP engine session using 'src' and 'dst' for the controller.

    engine -- Gtp_engine_protocol object
    src    -- readable file-like object
    dst    -- writeable file-like object

    Returns either when EOF is seen on src, or when the engine signals end of
    session.

    """
    def read():
        line = src.readline()
        if line == "":
            raise EOFError
        return line
    def write(s):
        dst.write(s)
        dst.flush()
    _run_gtp_session(engine, read, write)

def make_readline_completer(engine):
    """Return a readline completer function for the specified engine."""
    commands = engine.list_commands()
    def completer(text, state):
        matches = [s for s in commands if s.startswith(text)]
        try:
            return matches[state] + " "
        except IndexError:
            return None
    return completer

def run_interactive_gtp_session(engine):
    """Run a GTP engine session on stdin and stdout, using readline.

    engine -- Gtp_engine_protocol object

    This enables readline tab-expansion, and command history in
    ~/.gomill-gtp-history .

    Returns either when EOF is seen on stdin, or when the engine signals end of
    session.

    If stdin isn't a terminal, this is equivalent to run_gtp_session.

    """
    # readline doesn't do anything if stdin isn't a tty, but it's simplest to
    # just not import it in that case.
    if not os.isatty(sys.stdin.fileno()):
        run_gtp_session(engine, sys.stdin, sys.stdout)
        return

    def write(s):
        sys.stdout.write(s)
        sys.stdout.flush()

    import readline
    history_pathname = os.path.expanduser("~/.gomill-gtp-history")
    readline.parse_and_bind("tab: complete")
    old_completer = readline.get_completer()
    old_delims = readline.get_completer_delims()
    readline.set_completer(make_readline_completer(engine))
    readline.set_completer_delims("")
    try:
        readline.read_history_file(history_pathname)
    except EnvironmentError:
        pass
    _run_gtp_session(engine, raw_input, write)
    try:
        readline.write_history_file(history_pathname)
    except EnvironmentError:
        pass
    readline.set_completer(old_completer)
    readline.set_completer_delims(old_delims)


### Testing

def test():
    def handle_error(args):
        raise GtpError("normal error")

    def handle_fatal_error(args):
        raise GtpFatalError("fatal error")

    def handle_internal_error(args):
        os.path.join("foo", None)

    def handle_test(args):
        return "this respo\x7fnse\n\nne\x00eds\ncleanup\xa3"

    def handle_play(args):
        try:
            colour_s, vertex_s = args[:2]
        except ValueError:
            report_bad_arguments()
        colour = interpret_colour(colour_s)
        vertex = interpret_vertex(vertex_s, board_size=9)
        return str(vertex)

    def handle_komi(args):
        try:
            komi = interpret_float(args[0])
        except IndexError:
            report_bad_arguments()
        return komi

    engine = Gtp_engine_protocol()
    engine.add_protocol_commands()
    engine.add_command('help', engine.handle_list_commands)
    engine.add_command('test', handle_test)
    engine.add_command('error', handle_error)
    engine.add_command('fatal', handle_fatal_error)
    engine.add_command('internal_error', handle_internal_error)
    engine.add_command('play', handle_play)
    engine.add_command('komi', handle_komi)
    run_interactive_gtp_session(engine)
    #run_gtp_session(engine, sys.stdin, sys.stdout)

if __name__ == "__main__":
    test()
