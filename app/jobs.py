import logging
from datetime import datetime, timezone                  

from .db import SessionLocal
from .models import Document, DocumentStatus
from sqlalchemy import select                           

log = logging.getLogger(__name__)                       

async def process_document(document_id: int) -> None:   
    async with SessionLocal() as db:                    
        try:
            result = await db.execute(                   
                select(Document).where(Document.id == document_id)
            )
            doc = result.scalar_one_or_none()
            if not doc:
                log.warning("process_document: document %s not found", document_id)
                return

            doc.status = DocumentStatus.PROCESSING.value
            await db.commit()                            

            # Todo : real work goes here (GCS upload, OCR, etc.)

            doc.status = DocumentStatus.PROCESSED.value
            doc.error_message = None

            await db.commit()                            

        except Exception as e:
            await db.rollback()                          
            log.exception(                               
                "process_document failed for document_id=%s", document_id
            )
           
            result = await db.execute(
                select(Document).where(Document.id == document_id)
            )
            doc = result.scalar_one_or_none()
            if doc:
                doc.status = DocumentStatus.FAILED.value
                doc.error_message = str(e)
                await db.commit()                        
            # NOTE: no re-raise — failure is recorded in DB
            # re-raising here goes into the background task runner which swallows it anyway