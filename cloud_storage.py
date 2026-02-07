import os
from typing import Optional
import boto3


class S3Client:
    def __init__(self, bucket: Optional[str] = None, prefix: str = "faces/"):
        self.bucket = bucket or os.environ.get("S3_BUCKET")
        if not self.bucket:
            raise ValueError("S3 bucket not configured. Set S3_BUCKET env var or pass bucket.")
        self.prefix = prefix.rstrip("/") + "/"
        self.s3 = boto3.client(
            "s3",
            aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
            region_name=os.environ.get("AWS_REGION"),
        )

    def put_image(self, person_name: str, filename: str, data: bytes) -> str:
        key = f"{self.prefix}{person_name}/{filename}"
        self.s3.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType="image/jpeg")
        return key

    def presigned_url(self, key: str, expires_in: int = 3600) -> str:
        return self.s3.generate_presigned_url(
            "get_object", Params={"Bucket": self.bucket, "Key": key}, ExpiresIn=expires_in
        )


