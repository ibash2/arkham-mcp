import sys
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def installer_path():
    path = str(Path(__file__).parent.parent.parent / "installer")
    if path not in sys.path:
        sys.path.insert(0, path)


@pytest.fixture(scope="session")
def cp(installer_path):
    import config_paths
    return config_paths
