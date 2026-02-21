# tests/test_documents.py


class TestAddDocument:

    async def test_happy_path(self, client, auth_headers):
        """A valid document upload is accepted. The bureaucracy begins."""
        create = await client.post(
            "/intakes",
            json={"full_name": "Gerald Witherspoon III", "narrative": "I have paperwork. So much paperwork."},
            headers=auth_headers,
        )
        case_id = create.json()["case_id"]

        response = await client.post(
            f"/cases/{case_id}/documents",
            json={"filename": "denial_letter.pdf", "content_type": "application/pdf"},
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["case_id"] == case_id
        assert data["status"] == "UPLOADED"
        assert "document_id" in data

    async def test_case_not_found_returns_404(self, client, auth_headers):
        """Cannot upload documents to a case that doesn't exist. Obviously."""
        response = await client.post(
            "/cases/99999/documents",
            json={"filename": "proof_of_hammock.pdf", "content_type": "application/pdf"},
            headers=auth_headers,
        )
        assert response.status_code == 404

    async def test_missing_filename_returns_422(self, client, auth_headers):
        """A document without a filename is just vibes."""
        create = await client.post(
            "/intakes",
            json={"full_name": "Gerald Witherspoon III", "narrative": "More paperwork."},
            headers=auth_headers,
        )
        case_id = create.json()["case_id"]

        response = await client.post(
            f"/cases/{case_id}/documents",
            json={"content_type": "application/pdf"},
            headers=auth_headers,
        )
        assert response.status_code == 422

    async def test_content_type_is_optional(self, client, auth_headers):
        """content_type is optional — mystery files are welcome."""
        create = await client.post(
            "/intakes",
            json={"full_name": "Gerald Witherspoon III", "narrative": "Unknown file type, unknown destiny."},
            headers=auth_headers,
        )
        case_id = create.json()["case_id"]

        response = await client.post(
            f"/cases/{case_id}/documents",
            json={"filename": "mystery_file.???"},
            headers=auth_headers,
        )
        assert response.status_code == 201

    async def test_no_auth_returns_401(self, client):
        """Documents require authentication. The hammock is not public domain."""
        response = await client.post(
            "/cases/1/documents",
            json={"filename": "denial_letter.pdf", "content_type": "application/pdf"},
        )
        assert response.status_code == 401


class TestListDocuments:

    async def test_happy_path(self, client, auth_headers):
        """Documents are listed newest first. Eventually PROCESSED."""
        create = await client.post(
            "/intakes",
            json={"full_name": "Gerald Witherspoon III", "narrative": "Final chapter of the hammock saga."},
            headers=auth_headers,
        )
        case_id = create.json()["case_id"]

        await client.post(
            f"/cases/{case_id}/documents",
            json={"filename": "appeal_letter.pdf", "content_type": "application/pdf"},
            headers=auth_headers,
        )
        await client.post(
            f"/cases/{case_id}/documents",
            json={"filename": "doctors_note.pdf", "content_type": "application/pdf"},
            headers=auth_headers,
        )

        response = await client.get(f"/cases/{case_id}/documents", headers=auth_headers)
        assert response.status_code == 200
        items = response.json()
        assert len(items) == 2
        assert items[0]["filename"] == "doctors_note.pdf"  # most recent first

    async def test_case_not_found_returns_404(self, client, auth_headers):
        """No case, no documents, no resolution. Gerald waits."""
        response = await client.get("/cases/99999/documents", headers=auth_headers)
        assert response.status_code == 404

    async def test_no_auth_returns_401(self, client):
        """Still not a public forum. Gerald understands."""
        response = await client.get("/cases/1/documents")
        assert response.status_code == 401