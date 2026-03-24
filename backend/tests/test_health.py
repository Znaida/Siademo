"""Tests básicos de disponibilidad del sistema."""


def test_root_ok(client):
    res = client.get("/")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["sistema"] == "SIADE"


def test_captcha_genera_pregunta(client):
    res = client.get("/auth/captcha")
    assert res.status_code == 200
    data = res.json()
    assert "pregunta" in data
    assert "captcha_token" in data
    assert "+" in data["pregunta"]
