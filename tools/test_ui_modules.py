#!/usr/bin/env python3
"""
Compatibility shim for test_ui_modules.py.
Delegates to tests/unit/test_ui_modules.py.
"""
import os
import sys
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from tests.unit.test_ui_modules import TestUIModules  # noqa: F401


def test_audio_assets():
    suite = unittest.TestSuite()
    suite.addTest(TestUIModules("test_audio_assets"))
    runner = unittest.TextTestRunner()
    res = runner.run(suite)
    assert res.wasSuccessful(), "test_audio_assets failed"


def test_texture_assets():
    suite = unittest.TestSuite()
    suite.addTest(TestUIModules("test_texture_assets"))
    runner = unittest.TextTestRunner()
    res = runner.run(suite)
    assert res.wasSuccessful(), "test_texture_assets failed"


def test_lua_module_contracts():
    suite = unittest.TestSuite()
    suite.addTest(TestUIModules("test_lua_module_contracts"))
    runner = unittest.TextTestRunner()
    res = runner.run(suite)
    assert res.wasSuccessful(), "test_lua_module_contracts failed"


if __name__ == "__main__":
    unittest.main()
