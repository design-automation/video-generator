from boto3 import Session
from botocore.exceptions import BotoCoreError, ClientError
from aws_cred import __AWS__

def upload_s3(file_name, bucket, object_name=None):
    """Upload a file to an S3 bucket

    :param file_name: File to upload
    :param bucket: Bucket to upload to
    :param object_name: S3 object name. If not specified then file_name is used
    :return: True if file was uploaded, else False
    """
    # If S3 object_name was not specified, use file_name
    if object_name is None:
        object_name = file_name

    # Upload the file
    session = Session(
        aws_access_key_id=__AWS__.ID,
        aws_secret_access_key=__AWS__.KEY)
    s3_client = session.client('s3')
    try:
        print("Upload to S3")
        print("----- Filename:", file_name)
        print("----- s3 Bucket:", bucket)
        print("----- Object name:", object_name)
        response = s3_client.upload_file(file_name, bucket, object_name, ExtraArgs={'ACL': 'public-read'})
    except ClientError as e:
        return False
    return True
