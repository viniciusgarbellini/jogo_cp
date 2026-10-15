"""Testes da API. O provider e substituido por dublê, entao nao gasta cota do Gemini.

Rodar (dentro de backend/): pytest -v
"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config  # noqa: E402
from main import app  # noqa: E402
from providers import ia_provider  # noqa: E402

CHAVE = "chave-de-teste"
URL = "/v1/ia-generativa/texto"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(config, "API_KEY", CHAVE)
    return TestClient(app)


def test_health_nao_exige_chave(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_sem_header_devolve_401(client):
    r = client.post(URL, json={"prompt": "oi"})
    assert r.status_code == 401


def test_chave_errada_devolve_401(client):
    r = client.post(URL, json={"prompt": "oi"}, headers={"X-API-Key": "errada"})
    assert r.status_code == 401


def test_servidor_sem_api_key_configurada_devolve_503(monkeypatch):
    monkeypatch.setattr(config, "API_KEY", "")
    r = TestClient(app).post(URL, json={"prompt": "oi"}, headers={"X-API-Key": "qualquer"})
    assert r.status_code == 503


def test_rota_repassa_parametros_ao_provider(client, monkeypatch):
    recebido = {}

    def falso(prompt, json_mode=False, pensar=True):
        recebido.update(prompt=prompt, json_mode=json_mode, pensar=pensar)
        return "Eu estava em casa."

    monkeypatch.setattr(ia_provider, "gerar_texto", falso)
    r = client.post(
        URL,
        json={"prompt": "Onde voce estava?", "json_mode": True, "pensar": False},
        headers={"X-API-Key": CHAVE},
    )
    assert r.status_code == 200
    assert r.json()["texto"] == "Eu estava em casa."
    assert recebido == {"prompt": "Onde voce estava?", "json_mode": True, "pensar": False}


def test_prompt_vazio_devolve_422(client):
    r = client.post(URL, json={"prompt": ""}, headers={"X-API-Key": CHAVE})
    assert r.status_code == 422


def test_falha_do_gemini_vira_502(client, monkeypatch):
    def falha(*a, **k):
        raise ia_provider.ErroProvider("503 UNAVAILABLE")

    monkeypatch.setattr(ia_provider, "gerar_texto", falha)
    r = client.post(URL, json={"prompt": "oi"}, headers={"X-API-Key": CHAVE})
    assert r.status_code == 502


def test_backend_sem_chave_do_gemini_vira_503(client, monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "")
    monkeypatch.setattr(ia_provider, "_cliente", None)
    r = client.post(URL, json={"prompt": "oi"}, headers={"X-API-Key": CHAVE})
    assert r.status_code == 503
    assert "GEMINI_API_KEY" in r.json()["detail"]


def test_cors_libera_o_streamlit(client):
    r = client.options(
        URL,
        headers={
            "Origin": "http://localhost:8501",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "X-API-Key",
        },
    )
    assert r.headers.get("access-control-allow-origin") == "http://localhost:8501"
