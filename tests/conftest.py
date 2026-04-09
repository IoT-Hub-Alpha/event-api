import sys
from pathlib import Path

import pytest
from django.test import Client

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


@pytest.fixture
def client():
    return Client(HTTP_X_INTERNAL_SERVICE="test-suite")


@pytest.fixture
def raw_client():
    return Client()
