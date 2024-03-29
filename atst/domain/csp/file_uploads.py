from datetime import datetime, timedelta
from uuid import uuid4


class Uploader:
    def generate_token(self):
        pass

    def generate_download_link(self, object_name, filename) -> (dict, str):
        pass

    def object_name(self) -> str:
        return str(uuid4())


class MockUploader(Uploader):
    def __init__(self, config):
        self.config = config

    def get_token(self):
        return ({}, self.object_name())

    def generate_download_link(self, object_name, filename):
        return ""


class AzureUploader(Uploader):
    def __init__(self, config):
        self.account_name = config["AZURE_ACCOUNT_NAME"]
        self.storage_key = config["AZURE_STORAGE_KEY"]
        self.container_name = config["AZURE_TO_BUCKET_NAME"]
        self.timeout = timedelta(seconds=config["PERMANENT_SESSION_LIFETIME"])

        from azure.storage.common import CloudStorageAccount
        from azure.storage.blob import BlobPermissions

        self.CloudStorageAccount = CloudStorageAccount
        self.BlobPermissions = BlobPermissions

    def get_token(self):
        """
        Generates an Azure SAS token for pre-authorizing a file upload.

        Returns a tuple in the following format: (token_dict, object_name), where
            - token_dict has a `token` key which contains the SAS token as a string
            - object_name is a string
        """
        account = self.CloudStorageAccount(
            account_name=self.account_name, account_key=self.storage_key
        )
        bbs = account.create_block_blob_service()
        object_name = self.object_name()
        sas_token = bbs.generate_blob_shared_access_signature(
            self.container_name,
            object_name,
            permission=self.BlobPermissions.CREATE,
            expiry=datetime.utcnow() + self.timeout,
            protocol="https",
        )
        return ({"token": sas_token}, object_name)

    def generate_download_link(self, object_name, filename):
        account = self.CloudStorageAccount(
            account_name=self.account_name, account_key=self.storage_key
        )
        bbs = account.create_block_blob_service()
        sas_token = bbs.generate_blob_shared_access_signature(
            self.container_name,
            object_name,
            permission=self.BlobPermissions.READ,
            expiry=datetime.utcnow() + self.timeout,
            content_disposition=f"attachment; filename={filename}",
            protocol="https",
        )
        return bbs.make_blob_url(
            self.container_name, object_name, protocol="https", sas_token=sas_token
        )


class AwsUploader(Uploader):
    def __init__(self, config):
        self.access_key_id = config["AWS_ACCESS_KEY_ID"]
        self.secret_key = config["AWS_SECRET_KEY"]
        self.region_name = config["AWS_REGION_NAME"]
        self.bucket_name = config["AWS_BUCKET_NAME"]
        self.timeout_secs = config["PERMANENT_SESSION_LIFETIME"]

        import boto3

        self.boto3 = boto3

    def get_token(self):
        """
        Generates an AWS presigned post for pre-authorizing a file upload.

        Returns a tuple in the following format: (token_dict, object_name), where
            - token_dict contains several fields that will be passed directly into the
              form before being sent to S3
            - object_name is a string
        """
        s3_client = self.boto3.client(
            "s3",
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_key,
            config=self.boto3.session.Config(
                signature_version="s3v4", region_name=self.region_name
            ),
        )
        object_name = self.object_name()
        presigned_post = s3_client.generate_presigned_post(
            self.bucket_name,
            object_name,
            ExpiresIn=self.timeout_secs,
            Conditions=[
                ("eq", "$Content-Type", "application/pdf"),
                ("starts-with", "$x-amz-meta-filename", ""),
            ],
            Fields={"Content-Type": "application/pdf", "x-amz-meta-filename": ""},
        )
        return (presigned_post, object_name)

    def generate_download_link(self, object_name, filename):
        s3_client = self.boto3.client(
            "s3",
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_key,
            config=self.boto3.session.Config(
                signature_version="s3v4", region_name=self.region_name
            ),
        )
        return s3_client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": self.bucket_name,
                "Key": object_name,
                "ResponseContentDisposition": f"attachment; filename={filename}",
            },
            ExpiresIn=self.timeout_secs,
        )
