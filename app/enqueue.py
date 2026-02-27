from .jobs import process_document                

async def enqueue_document_processing(document_id: int) -> None:  
    await process_document(document_id)               
