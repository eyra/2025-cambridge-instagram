"""Pytest configuration for port package tests.

This conftest mocks the Pyodide 'js' module so tests can run outside the browser.
"""
import sys
from unittest.mock import MagicMock

# Mock the 'js' module that is only available in Pyodide (browser environment)
sys.modules['js'] = MagicMock()
