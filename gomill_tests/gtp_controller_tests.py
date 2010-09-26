"""Tests for gtp_controller.py"""

from gomill_tests import gomill_test_support
from gomill_tests import gtp_controller_test_support
from gomill_tests.gtp_controller_test_support import Preprogrammed_gtp_channel

from gomill import gtp_controller
from gomill.gtp_controller import (
    GtpChannelError, GtpProtocolError, GtpTransportError, GtpChannelClosed,
    BadGtpResponse, Gtp_controller)

def make_tests(suite):
    suite.addTests(gomill_test_support.make_simple_tests(globals()))



### Channel-level

def test_linebased_channel(tc):
    channel = Preprogrammed_gtp_channel("=\n\n=\n\n")
    tc.assertEqual(channel.get_command_stream(), "")
    channel.send_command("play", ["b", "a3"])
    tc.assertEqual(channel.get_command_stream(), "play b a3\n")
    tc.assertEqual(channel.get_response(), (False, ""))
    channel.send_command("quit", [])
    tc.assertEqual(channel.get_command_stream(), "play b a3\nquit\n")
    tc.assertEqual(channel.get_response(), (False, ""))
    tc.assertRaisesRegexp(
        GtpChannelClosed, "engine has closed the response channel",
        channel.get_response)
    channel.close()

def test_linebased_channel_responses(tc):
    channel = Preprogrammed_gtp_channel(
        "= 2\n\n"
        # failure response
        "? unknown command\n\n"
        # final response with no newlines
        "= ok")
    channel.send_command("protocol_version", [])
    tc.assertEqual(channel.get_response(), (False, "2"))
    channel.send_command("xyzzy", ["1", "2"])
    tc.assertEqual(channel.get_response(), (True, "unknown command"))
    channel.send_command("quit", ["1", "2"])
    tc.assertEqual(channel.get_response(), (False, "ok"))

def test_linebased_channel_response_cleaning(tc):
    channel = Preprogrammed_gtp_channel(
        # empty response
        "=\n\n"
        # whitespace-only response
        "= \n\n"
        # ignores CRs (GTP spec)
        "= 1abc\rde\r\n\r\n"
        # ignores extra blank lines (GTP spec)
        "= 2abcde\n\n\n\n"
        # strips control characters (GTP spec)
        "= 3a\x7fbc\x00d\x07e\n\x01\n"
        # converts tabs to spaces (GTP spec)
        "= 4abc\tde\n\n"
        # strips leading whitespace (channel docs)
        "=  \t   5abcde\n\n"
        # strips trailing whitepace (channel docs)
        "= 6abcde  \t  \n\n"
        # doesn't strip whitespace in the middle of a multiline response
        "= 7aaa  \n  bbb\tccc\nddd  \t  \n\n"
        # passes high characters through
        "= 8ab\xc3\xa7de\n\n"
        # all this at once, in a failure response
        "?    a\raa  \r\n  b\rbb\tcc\x01c\nddd  \t  \n\n"
        )
    tc.assertEqual(channel.get_response(), (False, ""))
    tc.assertEqual(channel.get_response(), (False, ""))
    tc.assertEqual(channel.get_response(), (False, "1abcde"))
    tc.assertEqual(channel.get_response(), (False, "2abcde"))
    tc.assertEqual(channel.get_response(), (False, "3abcde"))
    tc.assertEqual(channel.get_response(), (False, "4abc de"))
    tc.assertEqual(channel.get_response(), (False, "5abcde"))
    tc.assertEqual(channel.get_response(), (False, "6abcde"))
    tc.assertEqual(channel.get_response(), (False, "7aaa  \n  bbb ccc\nddd"))
    tc.assertEqual(channel.get_response(), (False, "8ab\xc3\xa7de"))
    tc.assertEqual(channel.get_response(), (True, "aaa  \n  bbb ccc\nddd"))

def test_linebased_channel_invalid_responses(tc):
    channel = Preprogrammed_gtp_channel(
        # good response first, to get past the "isn't speaking GTP" checking
        "=\n\n"
        "ERROR\n\n"
        "# comments not allowed in responses\n\n"
        )
    tc.assertEqual(channel.get_response(), (False, ""))
    tc.assertRaisesRegexp(
        GtpProtocolError, "^no success/failure indication from engine: "
                          "first line is `ERROR`$",
        channel.get_response)
    tc.assertRaisesRegexp(
        GtpProtocolError, "^no success/failure indication from engine: "
                          "first line is `#",
        channel.get_response)

def test_linebased_channel_without_response(tc):
    channel = Preprogrammed_gtp_channel("")
    channel.send_command("protocol_version", [])
    tc.assertRaisesRegexp(
        GtpChannelClosed, "^engine has closed the response channel$",
        channel.get_response)
    channel.close()

def test_linebased_channel_with_usage_message_response(tc):
    channel = Preprogrammed_gtp_channel(
        "Usage: randomprogram [options]\n\nOptions:\n"
        "--help   show this help message and exit\n")
    channel.send_command("protocol_version", [])
    tc.assertRaisesRegexp(
        GtpProtocolError, "^engine isn't speaking GTP: first byte is 'U'$",
        channel.get_response)
    channel.close()

def test_linebased_channel_with_interactive_response(tc):
    channel = Preprogrammed_gtp_channel("prompt> \n", hangs_before_eof=True)
    channel.send_command("protocol_version", [])
    tc.assertRaisesRegexp(
        GtpProtocolError, "^engine isn't speaking GTP", channel.get_response)
    channel.close()

def test_linebased_channel_hang(tc):
    # Correct behaviour for a GTP controller here is to wait for a newline.
    # (Would be nice to have a timeout.)
    # This serves as a check that the hangs_before_eof modelling is working.
    channel = Preprogrammed_gtp_channel("=prompt> ", hangs_before_eof=True)
    channel.send_command("protocol_version", [])
    tc.assertRaisesRegexp(
        StandardError, "this would hang", channel.get_response)
    channel.close()

def test_linebased_channel_with_gmp_response(tc):
    channel = Preprogrammed_gtp_channel("\x01\xa1\xa0\x80",
                                        hangs_before_eof=True)
    channel.send_command("protocol_version", [])
    tc.assertRaisesRegexp(
        GtpProtocolError, "appears to be speaking GMP", channel.get_response)
    channel.close()

def test_linebased_channel_with_broken_command_pipe(tc):
    channel = Preprogrammed_gtp_channel(
        "Usage: randomprogram [options]\n\nOptions:\n"
        "--help   show this help message and exit\n")
    channel.break_command_stream()
    tc.assertRaisesRegexp(
        GtpChannelClosed, "^engine has closed the command channel$",
        channel.send_command, "protocol_version", [])
    channel.close()

def test_linebased_channel_with_broken_response_pipe(tc):
    channel = Preprogrammed_gtp_channel("= 2\n\n? unreached\n\n")
    channel.send_command("protocol_version", [])
    tc.assertEqual(channel.get_response(), (False, "2"))
    channel.break_response_stream()
    channel.send_command("list_commands", [])
    tc.assertRaisesRegexp(
        GtpChannelClosed, "^engine has closed the response channel$",
        channel.get_response)
    channel.close()

def test_channel_command_validation(tc):
    channel = Preprogrammed_gtp_channel("\n\n")
    # empty command
    tc.assertRaises(ValueError, channel.send_command, "", [])
    # space in command
    tc.assertRaises(ValueError, channel.send_command, "play b a3", [])
    # space after command
    tc.assertRaises(ValueError, channel.send_command, "play ", ["b", "a3"])
    # control character in command
    tc.assertRaises(ValueError, channel.send_command, "pla\x01y", ["b", "a3"])
    # unicode command
    tc.assertRaises(ValueError, channel.send_command, u"protocol_version", [])
    # space in argument
    tc.assertRaises(ValueError, channel.send_command, "play", ["b a3"])
    # unicode argument
    tc.assertRaises(ValueError, channel.send_command, "play ", [u"b", "a3"])
    # high characters
    channel.send_command("pl\xc3\xa1y", ["b", "\xc3\xa13"])
    tc.assertEqual(channel.get_command_stream(), "pl\xc3\xa1y b \xc3\xa13\n")


### Validating Testing_gtp_channel

def test_testing_gtp_channel(tc):
    engine = gtp_controller_test_support.get_test_engine()
    channel = gtp_controller_test_support.Testing_gtp_channel(engine)
    channel.send_command("play", ["b", "a3"])
    tc.assertEqual(channel.get_response(), (True, "unknown command"))
    channel.send_command("test", [])
    tc.assertEqual(channel.get_response(), (False, "test response"))
    channel.send_command("multiline", [])
    tc.assertEqual(channel.get_response(),
                   (False, "first line  \n  second line\nthird line"))
    channel.send_command("quit", [])
    tc.assertEqual(channel.get_response(), (False, ""))
    tc.assertRaisesRegexp(
        GtpChannelClosed, "engine has closed the command channel",
        channel.send_command, "quit", [])
    channel.close()

def test_testing_gtp_channel_alt(tc):
    engine = gtp_controller_test_support.get_test_engine()
    channel = gtp_controller_test_support.Testing_gtp_channel(
        engine, engine_exit_breaks_commands=False)
    channel.send_command("test", [])
    tc.assertEqual(channel.get_response(), (False, "test response"))
    channel.send_command("quit", [])
    tc.assertEqual(channel.get_response(), (False, ""))
    channel.send_command("test", [])
    tc.assertRaisesRegexp(
        GtpChannelClosed, "engine has closed the response channel",
        channel.get_response)
    channel.close()

def test_testing_gtp_channel_fatal_errors(tc):
    engine = gtp_controller_test_support.get_test_engine()
    channel = gtp_controller_test_support.Testing_gtp_channel(engine)
    channel.send_command("fatal", [])
    tc.assertEqual(channel.get_response(), (True, "fatal error"))
    tc.assertRaisesRegexp(
        GtpChannelClosed, "engine has closed the response channel",
        channel.get_response)
    channel.close()

def test_testing_gtp_channel_sequencing(tc):
    engine = gtp_controller_test_support.get_test_engine()
    channel = gtp_controller_test_support.Testing_gtp_channel(engine)
    tc.assertRaisesRegexp(
        StandardError, "response request without command",
        channel.get_response)
    channel.send_command("test", [])
    tc.assertRaisesRegexp(
        StandardError, "two commands in a row",
        channel.send_command, "test", [])


### Controller-level

def test_controller(tc):
    channel = gtp_controller_test_support.get_test_channel()
    controller = Gtp_controller(channel, 'player test')
    tc.assertEqual(controller.name, 'player test')
    tc.assertIs(controller.channel, channel)
    tc.assertFalse(controller.channel_is_bad)

    tc.assertEqual(controller.do_command("test"), "test response")
    with tc.assertRaises(BadGtpResponse) as ar:
        controller.do_command("error")
    tc.assertEqual(ar.exception.gtp_error_message, "normal error")
    tc.assertEqual(ar.exception.gtp_command, "error")
    tc.assertSequenceEqual(ar.exception.gtp_arguments, [])
    tc.assertEqual(str(ar.exception),
                   "failure response from 'error' to player test:\n"
                   "normal error")
    with tc.assertRaises(BadGtpResponse) as ar:
        controller.do_command("fatal")
    tc.assertFalse(controller.channel_is_bad)

    with tc.assertRaises(GtpChannelClosed) as ar:
        controller.do_command("test")
    tc.assertEqual(str(ar.exception),
                   "error sending 'test' to player test:\n"
                   "engine has closed the command channel")
    tc.assertTrue(controller.channel_is_bad)
    controller.close()

def test_controller_first_command_error(tc):
    channel = gtp_controller_test_support.get_test_channel()
    controller = Gtp_controller(channel, 'player test')
    with tc.assertRaises(BadGtpResponse) as ar:
        controller.do_command("error")
    tc.assertEqual(
        str(ar.exception),
        "failure response from first command (error) to player test:\n"
        "normal error")

def test_describe_engine(tc):
    channel = gtp_controller_test_support.get_test_channel()
    controller = Gtp_controller(channel, 'player test')
    short_s, long_s = gtp_controller.describe_engine(controller)
    tc.assertEqual(short_s, "unknown")
    tc.assertEqual(long_s, "unknown")

    channel = gtp_controller_test_support.get_test_channel()
    channel.engine.add_command('name', lambda args:"test engine")
    controller = Gtp_controller(channel, 'player test')
    short_s, long_s = gtp_controller.describe_engine(controller)
    tc.assertEqual(short_s, "test engine")
    tc.assertEqual(long_s, "test engine")

    channel = gtp_controller_test_support.get_test_channel()
    channel.engine.add_command('name', lambda args:"test engine")
    channel.engine.add_command('version', lambda args:"1.2.3")
    controller = Gtp_controller(channel, 'player test')
    short_s, long_s = gtp_controller.describe_engine(controller)
    tc.assertEqual(short_s, "test engine:1.2.3")
    tc.assertEqual(long_s, "test engine:1.2.3")

    channel = gtp_controller_test_support.get_test_channel()
    channel.engine.add_command('name', lambda args:"test engine")
    channel.engine.add_command('version', lambda args:"1.2.3")
    channel.engine.add_command(
        'gomill-describe_engine',
        lambda args:"test engine (v1.2.3):\n  pl\xc3\xa1yer \xa3")
    controller = Gtp_controller(channel, 'player test')
    short_s, long_s = gtp_controller.describe_engine(controller)
    tc.assertEqual(short_s, "test engine:1.2.3")
    tc.assertEqual(long_s, "test engine (v1.2.3):\n  pl\xc3\xa1yer ?")

    channel = gtp_controller_test_support.get_test_channel()
    channel.engine.add_command('name', lambda args:"test engine")
    channel.engine.add_command('version', lambda args:"test engine v1.2.3")
    controller = Gtp_controller(channel, 'player test')
    short_s, long_s = gtp_controller.describe_engine(controller)
    tc.assertEqual(short_s, "test engine:v1.2.3")
    tc.assertEqual(long_s, "test engine:v1.2.3")

