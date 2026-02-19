from datetime import datetime

from .db import SessionLocal
from .models import Document, DocumentStatus

def process_document(document_id: int) -> None:
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            return

        doc.status = DocumentStatus.PROCESSING.value
        doc.updated_at = datetime.utcnow()
        db.commit()

        # TODO: real work later
        doc.status = DocumentStatus.PROCESSED.value
        doc.error_message = None
        doc.updated_at = datetime.utcnow()
        db.commit()
    except Exception as e:
        db.rollback()
        doc = db.query(Document).filter(Document.id == document_id).first()
        if doc:
            doc.status = DocumentStatus.FAILED.value
            doc.error_message = str(e)
            doc.updated_at = datetime.utcnow()
            db.commit()
        raise
    finally:
        db.close()