from app.models.raw_log_chunk import create_raw_log_chunk
from app.models.files import create_file, get_all_files
import uuid
from pathlib import Path

def parse_logs(chunk):
    pass

async def process_uploaded_file_chunk(chunk,file_id,sequence_number):

    raw_log_chunk_data = {
        "file_id": file_id,
        "user_id": None,
        "sequence_number": sequence_number,
        "content": chunk.decode("utf-8", errors="ignore")
    }

    await create_raw_log_chunk(raw_log_chunk_data)

async def save_file_to_db(file_size, fileName):
    try:
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

        file_id = str(uuid.uuid4())

        file_data = {
            "id": file_id,
            "filename": fileName,
            "user_id": None,
            "size_bytes": file_size,
            "status": "NOT STARTED"
        }

        result = await create_file(file_data)
        if result:
            return str(file_id + fileName)
        else:
            raise Exception("Failed to create file record")
    except Exception as e:
        print(f"Error saving file to DB: {e}")
        raise Exception("Error saving file to DB")

async def get_all_existing_files_metadata(userId=None,target_dir=""): # No user for now.
    try:
        result = await get_all_files(userId)
        
        exists_local = []
        for files in result:
            fileName = files.get("file_id","") + files.get("filename","")
            file = Path(target_dir / fileName)
            
            if file.is_file():
                exists_local.append(files)
        
        return exists_local
        
    except Exception as e:
        print("Error while fetching file data")
        raise Exception("Error while fetching file data")