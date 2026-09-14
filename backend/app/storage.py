import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from .config import settings

def client():
    s = settings()
    return boto3.client('s3', endpoint_url=s.s3_endpoint, region_name=s.aws_region,
                        config=Config(signature_version='s3v4', s3={'addressing_style': 'path'}))
def put(key, data, content_type='image/png'):
    client().put_object(Bucket=settings().s3_bucket, Key=key, Body=data, ContentType=content_type)
def get(key):
    return client().get_object(Bucket=settings().s3_bucket, Key=key)['Body'].read()

def get_optional(key):
    try:
        return get(key)
    except ClientError as error:
        if error.response['Error']['Code'] in ('NoSuchKey', '404'):
            return None
        raise
def signed(key):
    return client().generate_presigned_url('get_object', Params={'Bucket':settings().s3_bucket,'Key':key}, ExpiresIn=600)
