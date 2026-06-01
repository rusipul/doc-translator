import pytest
from fastapi.testclient import TestClient
import os
os.environ["SHARED_PASSWORD"] = "testpass"
os.environ["SECRET_KEY"] = "testsecret"

from main import app

client = TestClient(app)

def test_login_success():
    res = client.post("/auth/login", json={"password": "testpass"})
    assert res.status_code == 200
    assert "access_token" in res.cookies

def test_login_wrong_password():
    res = client.post("/auth/login", json={"password": "wrong"})
    assert res.status_code == 401

def test_protected_route_without_token():
    fresh = TestClient(app)
    res = fresh.get("/settings")
    assert res.status_code == 401
