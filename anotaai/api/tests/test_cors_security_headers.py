from fastapi.testclient import TestClient


def test_cors_permite_origem_configurada(client: TestClient):
    response = client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_cors_bloqueia_origem_nao_configurada(client: TestClient):
    response = client.get("/health", headers={"Origin": "http://evil.example.com"})
    assert "access-control-allow-origin" not in response.headers


def test_cors_preflight_permite_metodo_e_headers(client: TestClient):
    response = client.options(
        "/auth/login",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_security_headers_presentes(client: TestClient):
    response = client.get("/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert "geolocation=()" in response.headers["permissions-policy"]
    assert "max-age=63072000" in response.headers["strict-transport-security"]
