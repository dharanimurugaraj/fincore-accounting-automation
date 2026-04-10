import re
import boto3
from botocore.exceptions import ClientError
from datetime import datetime
from io import BytesIO
from typing import Optional
from botocore.config import Config
from app.core.config import settings

class StorageError(Exception):
    """Custom exception for R2 storage operations."""
    pass

def get_r2_client():
    """Returns a boto3 client for Cloudflare R2."""
    return boto3.client(
        "s3",
        endpoint_url=settings.R2_ENDPOINT_URL.rstrip("/"), # Ensure no trailing slash
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        region_name="auto",
        config=Config(signature_version="s3v4")
    )

def derive_org_folder(email: str) -> str:
    """
    Derive the org folder name from the user's email.
    Example: bharad.vyrenzo@gmail.com -> bharad-vyrenzo
    """
    local_part = email.split("@")[0]
    return re.sub(r"[^a-z0-9]+", "-", local_part.lower()).strip("-")

def generate_run_timestamp() -> str:
    """Returns a timestamp in YYYYMMDD_HHMMSS format."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def get_upload_key(org_folder: str, timestamp: str, filename: str) -> str:
    """Returns the S3 key for an uploaded PDF."""
    return f"{org_folder}/uploads/{timestamp}_{filename}"

def get_excel_key(org_folder: str, timestamp: str, file_type: str) -> str:
    """
    Returns the S3 key for Excel output files.
    file_type: "workingsheet" | "bankingreport"
    """
    return f"{org_folder}/{timestamp}/{timestamp}_excel/{timestamp}_{file_type}.xlsx"

def generate_presigned_put_url(key: str, expires: int = 600) -> str:
    """Generates a presigned PUT URL for browser uploads (10 min default)."""
    try:
        client = get_r2_client()
        return client.generate_presigned_url(
            "put_object",
            Params={"Bucket": settings.R2_BUCKET_NAME, "Key": key},
            ExpiresIn=expires
        )
    except ClientError as e:
        raise StorageError(f"Failed to generate presigned PUT URL: {str(e)}")

def generate_presigned_get_url(key: str, expires: int = 900) -> str:
    """Generates a presigned GET URL for downloads (15 min default)."""
    try:
        client = get_r2_client()
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.R2_BUCKET_NAME, "Key": key},
            ExpiresIn=expires
        )
    except ClientError as e:
        raise StorageError(f"Failed to generate presigned GET URL: {str(e)}")

def upload_file_object(file_obj: BytesIO, key: str, content_type: Optional[str] = None) -> str:
    """Uploads a file-like object to R2 and returns the key."""
    try:
        client = get_r2_client()
        extra_args = {}
        if content_type:
            extra_args["ContentType"] = content_type
        
        # Reset file pointer if needed
        if hasattr(file_obj, "seek"):
            file_obj.seek(0)
            
        client.upload_fileobj(file_obj, settings.R2_BUCKET_NAME, key, ExtraArgs=extra_args)
        return key
    except ClientError as e:
        raise StorageError(f"Failed to upload file object: {str(e)}")

def download_file_to_memory(key: str) -> BytesIO:
    """Downloads a file from R2 into a BytesIO object."""
    try:
        client = get_r2_client()
        file_obj = BytesIO()
        client.download_fileobj(settings.R2_BUCKET_NAME, key, file_obj)
        file_obj.seek(0)
        return file_obj
    except ClientError as e:
        raise StorageError(f"Failed to download file from R2: {str(e)}")
