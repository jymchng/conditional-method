# tests/conftest.py


def pytest_configure(config):
    config.addinivalue_line("markers", "benchmark: mark test as a benchmark.")
