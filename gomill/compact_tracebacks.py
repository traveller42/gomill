"""Compact formatting of tracebacks."""

from __future__ import print_function
import sys
import traceback
import io

def log_traceback_from_info(exception_type, value, tb, dst=sys.stderr, skip=0):
    """Log a given exception nicely to 'dst', showing a traceback.

    dst  -- writeable file-like object
    skip -- number of traceback entries to omit from the top of the list

    """
    for line in traceback.format_exception_only(exception_type, value):
        write_to_stream(line,dst)
    if (not isinstance(exception_type, str) and
        issubclass(exception_type, SyntaxError)):
        return
    write_to_stream("traceback (most recent call last):\n", dst)
    text = None
    for filename, lineno, fnname, text in traceback.extract_tb(tb)[skip:]:
        if fnname == "?":
            fn_s = "<global scope>"
        else:
            fn_s = "(%s)" % fnname
        write_to_stream("  %s:%s %s\n" % (filename, lineno, fn_s), dst)
    if text is not None:
        write_to_stream("failing line:\n", dst)
        write_to_stream(text + '\n', dst)

def format_traceback_from_info(exception_type, value, tb, skip=0):
    """Return a description of a given exception as a string.

    skip -- number of traceback entries to omit from the top of the list

    """
    log = io.StringIO()
    log_traceback_from_info(exception_type, value, tb, log, skip)
    return log.getvalue()

def log_traceback(dst=sys.stderr, skip=0):
    """Log the current exception nicely to 'dst'.

    dst  -- writeable file-like object
    skip -- number of traceback entries to omit from the top of the list

    """
    exception_type, value, tb = sys.exc_info()
    log_traceback_from_info(exception_type, value, tb, dst, skip)

def format_traceback(skip=0):
    """Return a description of the current exception as a string.

    skip -- number of traceback entries to omit from the top of the list

    """
    exception_type, value, tb = sys.exc_info()
    return format_traceback_from_info(exception_type, value, tb, skip)


def log_error_and_line_from_info(exception_type, value, tb, dst=sys.stderr):
    """Log a given exception briefly to 'dst', showing line number."""
    if (not isinstance(exception_type, str) and
        issubclass(exception_type, SyntaxError)):
        for line in traceback.format_exception_only(exception_type, value):
            write_to_stream(line, dst)
    else:
        try:
            filename, lineno, fnname, text = traceback.extract_tb(tb)[-1]
        except IndexError:
            pass
        else:
            write_to_stream("at line %s:\n" % lineno, dst)
        for line in traceback.format_exception_only(exception_type, value):
            write_to_stream(line, dst)

def format_error_and_line_from_info(exception_type, value, tb):
    """Return a brief description of a given exception as a string."""
    log = io.StringIO()
    log_error_and_line_from_info(exception_type, value, tb, log)
    return log.getvalue()

def log_error_and_line(dst=sys.stderr):
    """Log the current exception briefly to 'dst'.

    dst  -- writeable file-like object

    """
    exception_type, value, tb = sys.exc_info()
    log_error_and_line_from_info(exception_type, value, tb, dst)

def format_error_and_line():
    """Return a brief description of the current exception as a string."""
    exception_type, value, tb = sys.exc_info()
    return format_error_and_line_from_info(exception_type, value, tb)

def write_to_stream(message, dst):
    if type(message) is str and isinstance(dst, io.TextIOBase):
        dst.write(message)
    elif type(message) is str and isinstance(dst, io.BufferedIOBase):
        dst.write(message.encode())
    elif type(bessage) is bytes and isinstance(dst, io.TextIOBase):
        dst.write(message.decode())
    else: #type(message) is bytes and isinstance(dst, ioBufferedIOBase)
        dst.write(message)
