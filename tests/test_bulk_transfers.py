import json
import os

import pytest

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)  # https://fastapi.tiangolo.com/reference/testclient/, https://fastapi.tiangolo.com/tutorial/testing/


def _load_resource(resource_name):
    with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), f"resources/{resource_name}")) as resource:
        payload = json.load(resource)
        print(f"payload={payload}")
        return payload


# @pytest.fixture
# def sample_1():
#     return _load_resource(resource_name="sample1.json")


# @pytest.fixture
# def sample_2():
#     return _load_resource(resource_name="sample2.json")

@pytest.mark.parametrize("sample_file", ["sample1.json", "sample2.json"])
def test_transfers_bulk_parameterized(sample_file):
    sample_data = _load_resource(resource_name=sample_file)
    response = client.post(url="/transfers/bulk", json=sample_data)
    assert response.status_code == 201
    response_dict = response.json()
    assert "bulk_id" in response_dict
