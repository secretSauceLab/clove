from datetime import datetime
from sqlalchemy.orm import Session

from .models import Document, DocumentStatus

def process_document(db: Session, document_id: int):
    """
    Local dev 'background job':
    - marks doc PROCESSING
    - simulates processing
    - marks doc PROCESSED (or FAILED)
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        return

    doc.status = DocumentStatus.PROCESSING.value
    doc.updated_at = datetime.utcnow()
    db.commit()

    try:
        # TODO: real processing later (OCR, parsing, etc.)
        # For now: simulate success instantly.
        doc.status = DocumentStatus.PROCESSED.value
        doc.error_message = None
        doc.updated_at = datetime.utcnow()
        db.commit()
    except Exception as e:
        db.rollback()
        doc.status = DocumentStatus.FAILED.value
        doc.error_message = str(e)
        doc.updated_at = datetime.utcnow()
        db.commit()