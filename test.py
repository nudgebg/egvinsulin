import pytest

if __name__ == "__main__":
    pytest.main(["tests/test_tdd.py", "-vv", "--continue-on-collection-errors",  "--tb=short"])  # "--disable-warnings",