import os, json, tempfile, pytest
os.environ["SHARED_PASSWORD"] = "testpass"
os.environ["SECRET_KEY"] = "testsecret"

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def _login():
    client.post("/auth/login", json={"password": "testpass"})

def test_get_settings_no_key(tmp_path, monkeypatch):
    monkeypatch.setattr("config.CONFIG_PATH", str(tmp_path / "config.json"))
    _login()
    res = client.get("/settings")
    assert res.status_code == 200
    assert res.json() == {"api_key_set": False}

def test_put_api_key(tmp_path, monkeypatch):
    monkeypatch.setattr("config.CONFIG_PATH", str(tmp_path / "config.json"))
    _login()
    res = client.put("/settings/api-key", json={"api_key": "AIza-test-key"})
    assert res.status_code == 200
    res2 = client.get("/settings")
    assert res2.json() == {"api_key_set": True}

def test_put_empty_key_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr("config.CONFIG_PATH", str(tmp_path / "config.json"))
    _login()
    res = client.put("/settings/api-key", json={"api_key": ""})
    assert res.status_code == 400
