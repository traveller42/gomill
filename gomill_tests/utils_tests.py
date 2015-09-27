"""Tests for utils.py."""

from __future__ import with_statement

import errno
import os

from gomill_tests import gomill_test_support

from gomill import utils

def make_tests(suite):
    suite.addTests(gomill_test_support.make_simple_tests(globals()))


def test_format_float(tc):
    ff = utils.format_float
    tc.assertEqual(ff(1), "1")
    tc.assertEqual(ff(1.0), "1")
    tc.assertEqual(ff(1.5), "1.5")

def test_format_percent(tc):
    pct = utils.format_percent
    tc.assertEqual(pct(1, 1), "100.00%")
    tc.assertEqual(pct(1, 2), "50.00%")
    tc.assertEqual(pct(1.0, 2.0), "50.00%")
    tc.assertEqual(pct(1, 3), "33.33%")
    tc.assertEqual(pct(0, 3), "0.00%")
    tc.assertEqual(pct(2, 0), "??")
    tc.assertEqual(pct(0, 0), "--")

def test_sanitise_utf8(tc):
    su = utils.sanitise_utf8
    tc.assertIsNone(su(None))
    tc.assertEqual(su(b""), u"")
    tc.assertEqual(su(u""), u"")
    tc.assertEqual(su(b"hello world"), u"hello world")
    tc.assertEqual(su(u"hello world"), u"hello world")
    s = u"test \N{POUND SIGN}"
    b = s.encode("utf-8")
    tc.assertEqual(su(b), u"test \N{POUND SIGN}")
    tc.assertIs(su(s), s)
    tc.assertEqual(su(u"test \N{POUND SIGN}".encode("latin1")), u"test ?")

def test_isinf(tc):
    tc.assertIs(utils.isinf(0), False)
    tc.assertIs(utils.isinf(0.0), False)
    tc.assertIs(utils.isinf(3), False)
    tc.assertIs(utils.isinf(3.0), False)
    tc.assertIs(utils.isinf(1e300), False)
    tc.assertIs(utils.isinf(1e400), True)
    tc.assertIs(utils.isinf(-1e300), False)
    tc.assertIs(utils.isinf(-1e400), True)
    tc.assertIs(utils.isinf(1e-300), False)
    tc.assertIs(utils.isinf(1e-400), False)
    tc.assertIs(utils.isinf(float("inf")), True)
    tc.assertIs(utils.isinf(float("-inf")), True)
    tc.assertIs(utils.isinf(float("NaN")), False)

def test_nan(tc):
    tc.assertIs(utils.isnan(0), False)
    tc.assertIs(utils.isnan(0.0), False)
    tc.assertIs(utils.isnan(1e300), False)
    tc.assertIs(utils.isnan(1e400), False)
    tc.assertIs(utils.isnan(-1e300), False)
    tc.assertIs(utils.isnan(-1e400), False)
    tc.assertIs(utils.isnan(1e-300), False)
    tc.assertIs(utils.isnan(1e-400), False)
    tc.assertIs(utils.isnan(float("inf")), False)
    tc.assertIs(utils.isnan(float("-inf")), False)
    tc.assertIs(utils.isnan(float("NaN")), True)

def test_ensure_dir(tc):
    dirname = os.path.join(tc.sandbox(), "sub")
    tc.assertFalse(os.path.exists(dirname))
    utils.ensure_dir(dirname)
    tc.assertTrue(os.path.isdir(dirname))
    utils.ensure_dir(dirname)
    tc.assertTrue(os.path.isdir(dirname))
    with tc.assertRaises(EnvironmentError) as ar:
        utils.ensure_dir(os.path.join(tc.sandbox(), "nonex", "sub"))
    tc.assertEqual(ar.exception.errno, errno.ENOENT)

