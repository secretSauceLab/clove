import os
import requests
from .config import API_KEY

def enqueue_document_processing(document_id: int) -> None:
    base_url = os.getenv("SERVICE_BASE_URL", "http://127.0.0.1:8000")
    url = f"{base_url}/internal/documents/{document_id}/process"
    r = requests.post(url, headers={"X-API-Key": API_KEY}, timeout=10)
    r.raise_for_status()


