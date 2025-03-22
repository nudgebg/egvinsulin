# File: test.py
# Author Jan Wrede
# Copyright (c) 2025 nudgebg
# Licensed under the MIT License. See LICENSE file for details.
import pytest

if __name__ == "__main__":
    pytest.main(["tests", "-vv", "--continue-on-collection-errors",  "--tb=short"])  # "--disable-warnings",