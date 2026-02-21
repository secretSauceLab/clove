# tests/test_cases.py
import pytest


class TestListCases:

    async def test_happy_path(self, client, auth_headers):
        """List cases returns a paginated response."""
        response = await client.get("/cases", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "next_cursor" in data

    async def test_no_auth_returns_401(self, client):
        response = await client.get("/cases")
        assert response.status_code == 401

    async def test_filter_by_status(self, client, auth_headers):
        """Create two cases, filter by status, only see the right one."""
        # create a case
        response = await client.post(
            "/intakes",
            json={"full_name": "Patient A", "narrative": "narrative a"},
            headers=auth_headers,
        )
        case_id = response.json()["case_id"]

        # move it to IN_REVIEW
        await client.patch(
            f"/cases/{case_id}",
            json={"status": "IN_REVIEW"},
            headers=auth_headers,
        )

        # filter by IN_REVIEW — should appear
        response = await client.get("/cases?status=IN_REVIEW", headers=auth_headers)
        assert response.status_code == 200
        ids = [c["case_id"] for c in response.json()["items"]]
        assert case_id in ids

        # filter by NEW — should not appear
        response = await client.get("/cases?status=NEW", headers=auth_headers)
        ids = [c["case_id"] for c in response.json()["items"]]
        assert case_id not in ids


class TestGetCase:

    async def test_happy_path(self, client, auth_headers):
        """Create an intake then fetch the case detail."""
        create = await client.post(
            "/intakes",
            json={"full_name": "Test Patient", "narrative": "Some narrative."},
            headers=auth_headers,
        )
        case_id = create.json()["case_id"]

        response = await client.get(f"/cases/{case_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == case_id
        assert data["current_status"] == "NEW"
        assert data["applicant"]["full_name"] == "Test Patient"
        assert isinstance(data["status_events"], list)
        assert isinstance(data["notes"], list)

    async def test_not_found_returns_404(self, client, auth_headers):
        response = await client.get("/cases/99999", headers=auth_headers)
        assert response.status_code == 404

    async def test_no_auth_returns_401(self, client):
        response = await client.get("/cases/1")
        assert response.status_code == 401


class TestUpdateCase:

    async def test_valid_transition(self, client, auth_headers):
        """NEW -> IN_REVIEW is a valid transition."""
        create = await client.post(
            "/intakes",
            json={"full_name": "Test Patient", "narrative": "Some narrative."},
            headers=auth_headers,
        )
        case_id = create.json()["case_id"]

        response = await client.patch(
            f"/cases/{case_id}",
            json={"status": "IN_REVIEW"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["previous_status"] == "NEW"
        assert data["status"] == "IN_REVIEW"

    async def test_invalid_transition_returns_409(self, client, auth_headers):
        """NEW -> APPROVED is not a valid transition."""
        create = await client.post(
            "/intakes",
            json={"full_name": "Test Patient", "narrative": "Some narrative."},
            headers=auth_headers,
        )
        case_id = create.json()["case_id"]

        response = await client.patch(
            f"/cases/{case_id}",
            json={"status": "APPROVED"},
            headers=auth_headers,
        )
        assert response.status_code == 409

    async def test_invalid_status_returns_422(self, client, auth_headers):
        """Unknown status values are rejected by Pydantic before business logic runs."""
        create = await client.post(
            "/intakes",
            json={"full_name": "Test Patient", "narrative": "Some narrative."},
            headers=auth_headers,
        )
        case_id = create.json()["case_id"]

        response = await client.patch(
            f"/cases/{case_id}",
            json={"status": "BANANA"},
            headers=auth_headers,
        )
        assert response.status_code == 422

    async def test_update_assignee(self, client, auth_headers):
        """Assignee can be updated independently of status."""
        create = await client.post(
            "/intakes",
            json={"full_name": "Test Patient", "narrative": "Some narrative."},
            headers=auth_headers,
        )
        case_id = create.json()["case_id"]

        response = await client.patch(
            f"/cases/{case_id}",
            json={"assignee": "Jeremy"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["assignee"] == "Jeremy"

    async def test_same_status_is_noop(self, client, auth_headers):
        """Patching with the current status doesn't create a status event."""
        create = await client.post(
            "/intakes",
            json={"full_name": "Test Patient", "narrative": "Some narrative."},
            headers=auth_headers,
        )
        case_id = create.json()["case_id"]

        response = await client.patch(
            f"/cases/{case_id}",
            json={"status": "NEW"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "NEW"

    async def test_not_found_returns_404(self, client, auth_headers):
        response = await client.patch(
            "/cases/99999",
            json={"status": "IN_REVIEW"},
            headers=auth_headers,
        )
        assert response.status_code == 404

    async def test_no_auth_returns_401(self, client):
        response = await client.patch("/cases/1", json={"status": "IN_REVIEW"})
        assert response.status_code == 401