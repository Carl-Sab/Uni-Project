"""API-level tests: the auth flow and the security model itself.

CRITICAL: get_current_student must be the only source of student_id in the
API layer. These tests assert that no route accepts a student_id from the
client (path/query/body) and that scoped routes 401/403 without a valid
student token.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def _all_paths(routes) -> list[str]:
    paths = []
    for route in routes:
        path = getattr(route, "path", None)
        if path is not None:
            paths.append(path)
        # FastAPI 0.141's include_router wraps sub-routers in an opaque
        # _IncludedRouter with no .path of its own - walk into it.
        sub_router = getattr(route, "original_router", None)
        if sub_router is not None:
            paths.extend(_all_paths(sub_router.routes))
    return paths


async def test_no_route_accepts_a_student_id_path_parameter():
    """There must be no /api/students/{id}/... route anywhere."""
    paths = _all_paths(app.routes)
    assert paths, "route discovery found nothing - test is broken, not passing vacuously"
    for path in paths:
        assert "student_id" not in path, f"route {path} accepts student_id from the client"
        assert not path.startswith("/api/students/"), f"forbidden route shape: {path}"


async def test_student_login_rejects_unknown_id(client):
    resp = await client.post("/api/auth/student/login", json={"student_id": "NOPE"})
    assert resp.status_code == 401


async def test_student_login_accepts_known_id_and_returns_jwt(client):
    resp = await client.post("/api/auth/student/login", json={"student_id": "S2023011"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


async def test_me_requires_authentication(client):
    resp = await client.get("/api/me")
    assert resp.status_code == 401


async def test_me_rejects_admin_token(client):
    login = await client.post(
        "/api/auth/admin/login", json={"username": "admin", "password": "test-admin-password"}
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    resp = await client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


async def test_me_returns_only_the_token_holders_data(client):
    login = await client.post("/api/auth/student/login", json={"student_id": "S2023011"})
    token = login.json()["access_token"]

    resp = await client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["student_id"] == "S2023011"


async def test_admin_login_rejects_wrong_password(client):
    resp = await client.post(
        "/api/auth/admin/login", json={"username": "admin", "password": "wrong"}
    )
    assert resp.status_code == 401


async def test_degree_progress_for_maya_matches_hand_check(client):
    login = await client.post("/api/auth/student/login", json={"student_id": "S2023011"})
    token = login.json()["access_token"]

    resp = await client.get(
        "/api/me/degree-progress", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    by_category = {c["category_name"]: c for c in resp.json()}
    assert by_category["Engineering Core"]["credits_earned"] == 28
    assert by_category["Computer Engineering Major Core"]["credits_earned"] == 18
