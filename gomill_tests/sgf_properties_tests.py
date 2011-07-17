"""Tests for sgf_properties.py."""

from textwrap import dedent

from gomill_tests import gomill_test_support

from gomill import sgf_properties

def make_tests(suite):
    suite.addTests(gomill_test_support.make_simple_tests(globals()))

def test_interpret_simpletext(tc):
    interpret = sgf_properties.interpret_simpletext
    tc.assertEqual(interpret("a\nb\\\\c", "utf-8"), "a b\\c")
    u = u"test \N{POUND SIGN}"
    tc.assertEqual(interpret(u.encode("utf-8"), "utf-8"),
                   u.encode("utf-8"))
    tc.assertEqual(interpret(u.encode("iso-8859-1"), "iso-8859-1"),
                   u.encode("utf-8"))

def test_serialise_simpletext(tc):
    serialise = sgf_properties.serialise_simpletext
    tc.assertEqual(serialise("ab\\c", "utf-8"), "ab\\\\c")
    u = u"test \N{POUND SIGN}"
    tc.assertEqual(serialise(u.encode("utf-8"), "utf-8"),
                   u.encode("utf-8"))
    tc.assertEqual(serialise(u.encode("utf-8"), "iso-8859-1"),
                   u.encode("iso-8859-1"))
    tc.assertRaises(UnicodeEncodeError, serialise,
                    u"\N{EN DASH}".encode("utf-8"), "iso-8859-1")

def test_interpret_text(tc):
    interpret = sgf_properties.interpret_text
    tc.assertEqual(interpret("a\nb\\\\c", "utf-8"), "a\nb\\c")
    u = u"test \N{POUND SIGN}"
    tc.assertEqual(interpret(u.encode("utf-8"), "utf-8"),
                   u.encode("utf-8"))
    tc.assertEqual(interpret(u.encode("iso-8859-1"), "iso-8859-1"),
                   u.encode("utf-8"))

def test_serialise_text(tc):
    serialise = sgf_properties.serialise_text
    tc.assertEqual(serialise("ab\\c", "utf-8"), "ab\\\\c")
    u = u"test \N{POUND SIGN}"
    tc.assertEqual(serialise(u.encode("utf-8"), "utf-8"),
                   u.encode("utf-8"))
    tc.assertEqual(serialise(u.encode("utf-8"), "iso-8859-1"),
                   u.encode("iso-8859-1"))
    tc.assertRaises(UnicodeEncodeError, serialise,
                    u"\N{EN DASH}".encode("utf-8"), "iso-8859-1")


def test_interpret_number(tc):
    interpret_number = sgf_properties.interpret_number
    tc.assertEqual(interpret_number("1"), 1)
    tc.assertIs(type(interpret_number("1")), int)
    tc.assertEqual(interpret_number("0"), 0)
    tc.assertEqual(interpret_number("-1"), -1)
    tc.assertEqual(interpret_number("+1"), 1)
    tc.assertRaises(ValueError, interpret_number, "1.5")
    tc.assertRaises(ValueError, interpret_number, "0xaf")
    tc.assertRaises(TypeError, interpret_number, 1)


def test_interpret_real(tc):
    interpret_real = sgf_properties.interpret_real
    tc.assertEqual(interpret_real("1"), 1.0)
    tc.assertIs(type(interpret_real("1")), float)
    tc.assertEqual(interpret_real("0"), 0.0)
    tc.assertEqual(interpret_real("1.0"), 1.0)
    tc.assertEqual(interpret_real("1.5"), 1.5)
    tc.assertEqual(interpret_real("-1.5"), -1.5)
    tc.assertEqual(interpret_real("+0.5"), 0.5)
    tc.assertRaises(ValueError, interpret_real, "+")
    tc.assertRaises(ValueError, interpret_real, "0xaf")
    #tc.assertRaises(TypeError, interpret_real, 1.0)

def test_serialise_real(tc):
    serialise_real = sgf_properties.serialise_real
    tc.assertEqual(serialise_real(1), "1")
    tc.assertEqual(serialise_real(-1), "-1")
    tc.assertEqual(serialise_real(1.0), "1")
    tc.assertEqual(serialise_real(-1.0), "-1")
    tc.assertEqual(serialise_real(1.5), "1.5")
    tc.assertEqual(serialise_real(-1.5), "-1.5")
    tc.assertEqual(serialise_real(0.001), "0.001")
    tc.assertEqual(serialise_real(0.0001), "0.0001")
    tc.assertEqual(serialise_real(0.00001), "0")
    tc.assertEqual(serialise_real(1e15), "1000000000000000")
    tc.assertEqual(serialise_real(1e16), "10000000000000000")
    tc.assertEqual(serialise_real(1e17), "100000000000000000")
    tc.assertEqual(serialise_real(1e18), "1000000000000000000")
    tc.assertEqual(serialise_real(-1e18), "-1000000000000000000")
    tc.assertRaises(ValueError, serialise_real, float(1e400))
    # Python 2.5 returns 0
    #tc.assertRaises(ValueError, serialise_real, float("NaN"))


def test_interpret_point(tc):
    interpret_point = sgf_properties.interpret_point
    tc.assertEqual(interpret_point("aa", 19), (18, 0))
    tc.assertEqual(interpret_point("ai", 19), (10, 0))
    tc.assertEqual(interpret_point("ba",  9), (8, 1))
    tc.assertEqual(interpret_point("tt", 21), (1, 19))
    tc.assertIs(interpret_point("tt", 19), None)
    tc.assertIs(interpret_point("", 19), None)
    tc.assertIs(interpret_point("", 21), None)
    tc.assertRaises(ValueError, interpret_point, "Aa", 19)
    tc.assertRaises(ValueError, interpret_point, "aA", 19)
    tc.assertRaises(ValueError, interpret_point, "aaa", 19)
    tc.assertRaises(ValueError, interpret_point, "a", 19)
    tc.assertRaises(ValueError, interpret_point, "au", 19)
    tc.assertRaises(ValueError, interpret_point, "ua", 19)
    tc.assertRaises(ValueError, interpret_point, "a`", 19)
    tc.assertRaises(ValueError, interpret_point, "`a", 19)
    tc.assertRaises(ValueError, interpret_point, "11", 19)
    tc.assertRaises(ValueError, interpret_point, " aa", 19)
    tc.assertRaises(ValueError, interpret_point, "aa\x00", 19)
    tc.assertRaises(TypeError, interpret_point, None, 19)
    #tc.assertRaises(TypeError, interpret_point, ('a', 'a'), 19)

def test_serialise_point(tc):
    serialise_point = sgf_properties.serialise_point
    tc.assertEqual(serialise_point((18, 0), 19), "aa")
    tc.assertEqual(serialise_point((10, 0), 19), "ai")
    tc.assertEqual(serialise_point((8, 1), 19), "bk")
    tc.assertEqual(serialise_point((8, 1), 9), "ba")
    tc.assertEqual(serialise_point((1, 19), 21), "tt")
    tc.assertEqual(serialise_point(None, 19), "tt")
    tc.assertEqual(serialise_point(None, 20), "")
    tc.assertRaises(ValueError, serialise_point, (3, 3), 0)
    tc.assertRaises(ValueError, serialise_point, (3, 3), 27)
    tc.assertRaises(ValueError, serialise_point, (9, 0), 9)
    tc.assertRaises(ValueError, serialise_point, (-1, 0), 9)
    tc.assertRaises(ValueError, serialise_point, (0, 9), 9)
    tc.assertRaises(ValueError, serialise_point, (0, -1), 9)
    tc.assertRaises(TypeError, serialise_point, (1, 1.5), 9)


def test_interpret_point_list(tc):
    ipl = sgf_properties.interpret_point_list
    tc.assertEqual(ipl([], 19),
                   set())
    tc.assertEqual(ipl(["aa"], 19),
                   set([(18, 0)]))
    tc.assertEqual(ipl(["aa", "ai"], 19),
                   set([(18, 0), (10, 0)]))
    tc.assertEqual(ipl(["ab:bc"], 19),
                   set([(16, 0), (16, 1), (17, 0), (17, 1)]))
    tc.assertEqual(ipl(["ab:bc", "aa"], 19),
                   set([(18, 0), (16, 0), (16, 1), (17, 0), (17, 1)]))
    # overlap is forbidden by the spec, but we accept it
    tc.assertEqual(ipl(["aa", "aa"], 19),
                   set([(18, 0)]))
    tc.assertEqual(ipl(["ab:bc", "bb:bc"], 19),
                   set([(16, 0), (16, 1), (17, 0), (17, 1)]))
    # 1x1 rectangles are forbidden by the spec, but we accept them
    tc.assertEqual(ipl(["aa", "bb:bb"], 19),
                   set([(18, 0), (17, 1)]))
    # 'backwards' rectangles are forbidden by the spec, and we reject them
    tc.assertRaises(ValueError, ipl, ["ab:aa"], 19)
    tc.assertRaises(ValueError, ipl, ["ba:aa"], 19)
    tc.assertRaises(ValueError, ipl, ["bb:aa"], 19)

    tc.assertRaises(ValueError, ipl, ["aa", "tt"], 19)
    tc.assertRaises(ValueError, ipl, ["aa", ""], 19)
    tc.assertRaises(ValueError, ipl, ["aa:", "aa"], 19)
    tc.assertRaises(ValueError, ipl, ["aa:tt", "aa"], 19)
    tc.assertRaises(ValueError, ipl, ["tt:aa", "aa"], 19)

def test_compressed_point_list_spec_example(tc):
    # Checks the examples at http://www.red-bean.com/sgf/DD_VW.html
    def sgf_point(move, size):
        row, col = move
        row = size - row - 1
        col_s = "abcdefghijklmnopqrstuvwxy"[col]
        row_s = "abcdefghijklmnopqrstuvwxy"[row]
        return col_s + row_s

    ipl = sgf_properties.interpret_point_list
    tc.assertEqual(
        set(sgf_point(move, 9) for move in ipl(["ac:ic"], 9)),
        set(["ac", "bc", "cc", "dc", "ec", "fc", "gc", "hc", "ic"]))
    tc.assertEqual(
        set(sgf_point(move, 9) for move in ipl(["ae:ie"], 9)),
        set(["ae", "be", "ce", "de", "ee", "fe", "ge", "he", "ie"]))
    tc.assertEqual(
        set(sgf_point(move, 9) for move in ipl(["aa:bi", "ca:ce"], 9)),
        set(["aa", "ab", "ac", "ad", "ae", "af", "ag", "ah", "ai",
             "bi", "bh", "bg", "bf", "be", "bd", "bc", "bb", "ba",
             "ca", "cb", "cc", "cd", "ce"]))

def test_serialise_point_list(tc):
    ipl = sgf_properties.interpret_point_list
    spl = sgf_properties.serialise_point_list

    tc.assertEqual(spl([(18, 0), (17, 1)], 19), ['aa', 'bb'])
    tc.assertEqual(spl([(17, 1), (18, 0)], 19), ['aa', 'bb'])
    tc.assertEqual(spl([], 9), [])
    tc.assertEqual(ipl(spl([(1,2), (3,4), (4,5)], 19), 19),
                   set([(1,2), (3,4), (4,5)]))


def test_AP(tc):
    def serialise(arg):
        return sgf_properties.serialise_AP(arg, "utf-8")
    def interpret(arg):
        return sgf_properties.interpret_AP(arg, "utf-8")

    tc.assertEqual(serialise(("foo:bar", "2\n3")), "foo\\:bar:2\n3")
    tc.assertEqual(interpret("foo\\:bar:2 3"), ("foo:bar", "2 3"))
    tc.assertEqual(interpret("foo bar"), ("foo bar", ""))

def test_ARLN(tc):
    tc.assertEqual(sgf_properties.serialise_ARLN([], 19), [])
    tc.assertEqual(sgf_properties.interpret_ARLN([], 19), [])
    tc.assertEqual(
        sgf_properties.serialise_ARLN([((7, 0), (5, 2)), ((4, 3), (2, 5))], 9),
        ['ab:cd', 'de:fg'])
    tc.assertEqual(
        sgf_properties.interpret_ARLN(['ab:cd', 'de:fg'], 9),
        [((7, 0), (5, 2)), ((4, 3), (2, 5))])

def test_FG(tc):
    def serialise(arg):
        return sgf_properties.serialise_FG(arg, "utf-8")
    def interpret(arg):
        return sgf_properties.interpret_FG(arg, "utf-8")
    tc.assertEqual(serialise(None), "")
    tc.assertEqual(interpret(""), None)
    tc.assertEqual(serialise((515, "th]is")), "515:th\\]is")
    tc.assertEqual(interpret("515:th\\]is"), (515, "th]is"))

def test_LB(tc):
    def serialise(arg, size):
        return sgf_properties.serialise_LB(arg, size, "utf-8")
    def interpret(arg, size):
        return sgf_properties.interpret_LB(arg, size, "utf-8")
    tc.assertEqual(serialise([], 19), [])
    tc.assertEqual(interpret([], 19), [])
    tc.assertEqual(
        serialise([((6, 0), "lbl"), ((6, 1), "lb]l2")], 9),
        ["ac:lbl", "bc:lb\\]l2"])
    tc.assertEqual(
        interpret(["ac:lbl", "bc:lb\\]l2"], 9),
        [((6, 0), "lbl"), ((6, 1), "lb]l2")])


def test_serialise_value(tc):
    sv = sgf_properties.serialise_value
    tc.assertEqual(sv('KO', True, 9, "utf-8"), [""])
    tc.assertEqual(sv('SZ', 9, 9, "utf-8"), ["9"])
    tc.assertEqual(sv('KM', 3.5, 9, "utf-8"), ["3.5"])
    tc.assertEqual(sv('C', "foo\\:b]ar\n", 9, "utf-8"), ["foo\\\\:b\\]ar\n"])
    tc.assertEqual(sv('B', (1, 2), 19, "utf-8"), ["cr"])
    tc.assertEqual(sv('B', None, 9, "utf-8"), ["tt"])
    tc.assertEqual(sv('AW', set([(17, 1), (18, 0)]), 19, "utf-8"), ["aa", "bb"])
    tc.assertEqual(sv('DD', [(1, 2), (3, 4)], 9, "utf-8"), ["ch", "ef"])
    tc.assertEqual(sv('DD', [], 9, "utf-8"), [""])
    tc.assertRaisesRegexp(ValueError, "empty list", sv, 'CR', [], 9, "utf-8")
    tc.assertEqual(sv('AP', ("na:me", "2.3"), 9, "utf-8"), ["na\\:me:2.3"])
    tc.assertEqual(sv('FG', (515, "th]is"), 9, "utf-8"), ["515:th\\]is"])
    tc.assertEqual(sv('XX', "foo\\bar", 9, "utf-8"), ["foo\\\\bar"])

    tc.assertRaises(ValueError, sv, 'B', (1, 9), 9, "utf-8")
