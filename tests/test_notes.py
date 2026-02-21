class TestAddNote:

    async def test_happy_path(self, client, auth_headers):
        """A valid note gets added. The system works. We're all fine."""
        create = await client.post(
            "/intakes",
            json={"full_name": "Gerald Witherspoon III", "narrative": "My insurer denied my claim for a medically necessary hammock."},
            headers=auth_headers,
        )
        case_id = create.json()["case_id"]

        response = await client.post(
            f"/cases/{case_id}/notes",
            json={"author": "Jeremy", "body": "Called insurer. They said hammocks are 'lifestyle items'. I said Gerald has a bad back. They said hold please. I held."},
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["case_id"] == case_id
        assert "note_id" in data

    async def test_case_not_found_returns_404(self, client, auth_headers):
        """Cannot add a note to a case that does not exist. Philosophy aside."""
        response = await client.post(
            "/cases/99999/notes",
            json={"author": "Jeremy", "body": "Note to nobody."},
            headers=auth_headers,
        )
        assert response.status_code == 404

    async def test_missing_author_returns_422(self, client, auth_headers):
        """Anonymous notes are not allowed. Own your opinions, coward."""
        create = await client.post(
            "/intakes",
            json={"full_name": "Gerald Witherspoon III", "narrative": "Hammock denied again."},
            headers=auth_headers,
        )
        case_id = create.json()["case_id"]

        response = await client.post(
            f"/cases/{case_id}/notes",
            json={"body": "I have thoughts but refuse to say who I am."},
            headers=auth_headers,
        )
        assert response.status_code == 422

    async def test_body_too_long_returns_422(self, client, auth_headers):
        """10,001 x's is apparently too many x's. Who knew."""
        create = await client.post(
            "/intakes",
            json={"full_name": "Gerald Witherspoon III", "narrative": "Still the hammock thing."},
            headers=auth_headers,
        )
        case_id = create.json()["case_id"]

        response = await client.post(
            f"/cases/{case_id}/notes",
            json={"author": "Jeremy", "body": "x" * 10_001},
            headers=auth_headers,
        )
        assert response.status_code == 422

    async def test_no_auth_returns_401(self, client):
        """No API key, no notes. This is not a public forum."""
        response = await client.post(
            "/cases/1/notes",
            json={"author": "Anonymous Stranger", "body": "Let me in."},
        )
        assert response.status_code == 401


class TestListNotes:

    async def test_happy_path(self, client, auth_headers):
        """Notes come back newest first. Like a timeline, but useful."""
        create = await client.post(
            "/intakes",
            json={"full_name": "Gerald Witherspoon III", "narrative": "The hammock saga continues."},
            headers=auth_headers,
        )
        case_id = create.json()["case_id"]

        await client.post(
            f"/cases/{case_id}/notes",
            json={"author": "Jeremy", "body": "Called insurer. Was put on hold for 47 minutes."},
            headers=auth_headers,
        )
        await client.post(
            f"/cases/{case_id}/notes",
            json={"author": "Jeremy", "body": "They approved it. Gerald wept. I also wept a little."},
            headers=auth_headers,
        )

        response = await client.get(f"/cases/{case_id}/notes", headers=auth_headers)
        assert response.status_code == 200
        items = response.json()["items"]
        assert len(items) == 2
        assert items[0]["body"] == "They approved it. Gerald wept. I also wept a little."  # most recent first

    async def test_case_not_found_returns_404(self, client, auth_headers):
        """No case, no notes, no closure."""
        response = await client.get("/cases/99999/notes", headers=auth_headers)
        assert response.status_code == 404

    async def test_no_auth_returns_401(self, client):
        """Still not a public forum."""
        response = await client.get("/cases/1/notes")
        assert response.status_code == 401