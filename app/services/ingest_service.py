import uuid
from pathlib import Path

from app.models.files import create_file, get_all_files


async def save_file_to_db(file_size: int, file_name: str) -> str:
    file_id = str(uuid.uuid4())
    file_data = {
        "id": file_id,
        "filename": file_name,
        "user_id": None,
        "size_bytes": file_size,
        "status": "NOT STARTED",
    }
    result = await create_file(file_data)
    if not result:
        raise RuntimeError("Failed to create file record")
    return file_id


async def get_all_existing_files_metadata(user_id=None, target_dir: Path = Path(".")):
    result = await get_all_files(user_id)

    exists_local = []
    for file_doc in result:
        file_name = f"{file_doc.get('file_id', '')}{file_doc.get('filename', '')}"
        file_path = target_dir / file_name
        if file_path.is_file():
            exists_local.append(file_doc)

    return exists_local
