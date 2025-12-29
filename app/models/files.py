from app.schemas.files import FileCreate
from datetime import datetime
from app.core.mongo import file_col

async def create_file(data: FileCreate):
    try:
        doc = {
            "id": data.get("id"),
            "filename": data.get("filename"),
            "user_id": data.get("user_id"),
            "size_bytes": data.get("size_bytes"),
            "status": data.get("status"),
            "total_chunks": data.get("total_chunks", 1),
            "last_raw_log_chunk_id": data.get("last_raw_log_chunk_id", None),
            "created_at": datetime.now()
        }
        result = await file_col.insert_one(doc)
        return result.inserted_id
    except Exception as e:
        print(f"Error creating file: {e}")
        raise Exception("Error creating file")

async def update_total_chunks(file_id: str, total_chunks: int):
    try:
        await file_col.update_one({"id": file_id}, {"$set": {"total_chunks": total_chunks}})
    except Exception as e:
        print(f"Error updating total chunks: {e}")