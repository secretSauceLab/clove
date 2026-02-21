# tests/test_intakes.py
import pytest


class TestCreateIntake:

    async def test_happy_path(self, client, auth_headers):
        """A valid intake creates a case with status NEW."""
        response = await client.post(
            "/intakes",
            json={
                "full_name": "Test Patient",
                "email": "test@example.com",
                "narrative": "I need help with my insurance denial.",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "NEW"
        assert "case_id" in data

    async def test_no_api_key_returns_401(self, client):
        """Requests without an API key are rejected."""
        response = await client.post(
            "/intakes",
            json={
                "full_name": "Test Patient",
                "narrative": "Some narrative.",
            },
        )
        assert response.status_code == 401

    async def test_wrong_api_key_returns_401(self, client):
        """Requests with a wrong API key are rejected."""
        response = await client.post(
            "/intakes",
            json={
                "full_name": "Test Patient",
                "narrative": "Some narrative.",
            },
            headers={"X-API-Key": "wrong-key"},
        )
        assert response.status_code == 401

    async def test_missing_full_name_returns_422(self, client, auth_headers):
        """full_name is required — missing it returns a validation error."""
        response = await client.post(
            "/intakes",
            json={"narrative": "Some narrative."},
            headers=auth_headers,
        )
        assert response.status_code == 422

    async def test_missing_narrative_returns_422(self, client, auth_headers):
        """narrative is required — missing it returns a validation error."""
        response = await client.post(
            "/intakes",
            json={"full_name": "Test Patient"},
            headers=auth_headers,
        )
        assert response.status_code == 422

    async def test_narrative_too_long_returns_422(self, client, auth_headers):
        """narrative over 20,000 chars is rejected."""
        response = await client.post(
            "/intakes",
            json={
                "full_name": "Test Patient",
                "narrative": "x" * 20_001,
            },
            headers=auth_headers,
        )
        assert response.status_code == 422

    async def test_invalid_email_returns_422(self, client, auth_headers):
        """An invalid email format is rejected by Pydantic."""
        response = await client.post(
            "/intakes",
            json={
                "full_name": "Test Patient",
                "email": "not-an-email",
                "narrative": "Some narrative.",
            },
            headers=auth_headers,
        )
        assert response.status_code == 422

    async def test_email_is_optional(self, client, auth_headers):
        """Email is optional — omitting it should still create a case."""
        response = await client.post(
            "/intakes",
            json={
                "full_name": "Test Patient",
                "narrative": "Some narrative.",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201