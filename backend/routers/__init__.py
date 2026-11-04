"""Shared router helpers."""
from fastapi import HTTPException, UploadFile

from config import settings


def read_upload_capped(file: UploadFile) -> bytes:
    """Read an uploaded file, rejecting anything over MAX_UPLOAD_MB."""
    cap = settings.MAX_UPLOAD_MB * 1024 * 1024
    data = file.file.read(cap + 1)
    if len(data) > cap:
        raise HTTPException(
            413, f"File exceeds the {settings.MAX_UPLOAD_MB} MB upload limit")
    return data
