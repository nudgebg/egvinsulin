# File: conftest.py
# Author Jan Wrede
# Copyright (c) 2025 nudgebg
# Licensed under the MIT License. See LICENSE file for details.
# tests/conftest.py
import sys
import os

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))