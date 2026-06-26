import os

import aiofiles

from api.config import settings


async def save_upload(job_id: str, filename: str, data: bytes) -> str:
    dest_dir = os.path.join(settings.storage_path, job_id)
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, filename)
    async with aiofiles.open(dest, "wb") as f:
        await f.write(data)
    return dest
