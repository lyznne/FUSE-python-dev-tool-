#!/usr/bin/env python

"""
FUSE - Python Development Tool
================================================================================
This script serves as the entry point for the Python Development Tool's FUSE CLI.
It imports the main application from the `main` module and executes it.
It is designed to be run as a standalone script.
Usage:
    python fuse.py [options]
This will invoke the main application logic defined in `main.py`.

"""

import sys

from python_dev_tool.cli.main import app

if __name__ == "__main__":
    sys.exit(app())
