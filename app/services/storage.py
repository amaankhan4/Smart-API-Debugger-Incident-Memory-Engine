"""Storage abstraction.

Local disk is the development implementation. The interface is intentionally
narrow (save / open / delete / exists) so an object-store backend can replace it
without touching ingestion or the API layer.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import AsyncIterator, Protocol

import aiofiles

from app.core.config import settings
from app.utils.paths import resolve_within, sanitize_filename


class UploadStream(Protocol):
    async def read(self, size: int) -> bytes: ...


class FileTooLargeError(Exception):
    pass


class LogStorage(ABC):
    @abstractmethod
    async def save(self, *, file_id: str, filename: str, stream: UploadStream) -> tuple[str, int]: ...

    @abstractmethod
    def open_text(self, stored_name: str): ...

    @abstractmethod
    async def delete(self, stored_name: str) -> None: ...

    @abstractmethod
    def exists(self, stored_name: str) -> bool: ...


class LocalLogStorage(LogStorage):
    def __init__(self, base_dir: str | Path) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve(self, stored_name: str) -> Path:
        return resolve_within(self.base_dir, stored_name)

    def build_stored_name(self, file_id: str, filename: str) -> str:
        # file_id prefix guarantees uniqueness; the sanitized name is only for humans.
        return f"{file_id}__{sanitize_filename(filename)}"

    async def save(self, *, file_id: str, filename: str, stream: UploadStream) -> tuple[str, int]:
        stored_name = self.build_stored_name(file_id, filename)
        target = self._resolve(stored_name)
        written = 0

        try:
            async with aiofiles.open(target, "wb") as out_file:
                while True:
                    chunk = await stream.read(settings.READ_CHUNK_BYTES)
                    if not chunk:
                        break
                    written += len(chunk)
                    if written > settings.MAX_UPLOAD_BYTES:
                        raise FileTooLargeError(
                            f"Upload exceeds the {settings.MAX_UPLOAD_BYTES} byte limit"
                        )
                    await out_file.write(chunk)
        except BaseException:
            target.unlink(missing_ok=True)
            raise

        return stored_name, written

    def open_text(self, stored_name: str):
        return aiofiles.open(self._resolve(stored_name), "r", encoding="utf-8", errors="replace")

    async def delete(self, stored_name: str) -> None:
        self._resolve(stored_name).unlink(missing_ok=True)

    def exists(self, stored_name: str) -> bool:
        try:
            return self._resolve(stored_name).is_file()
        except ValueError:
            return False

    async def iter_lines(self, stored_name: str) -> AsyncIterator[str]:
        async with self.open_text(stored_name) as handle:
            async for line in handle:
                yield line


storage: LogStorage = LocalLogStorage(settings.UPLOAD_DIR)
