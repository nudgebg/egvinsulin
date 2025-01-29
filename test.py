import pytest

if __name__ == "__main__":
    pytest.main(["tests", "-vv", "--continue-on-collection-errors",  "--tb=short"])  # "--disable-warnings",