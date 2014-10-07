# vim:encoding=utf-8:ts=2:sw=2:expandtab
from .Base import S3
from . import Setup

class Config(object):
  """Wraps around a config file to provide easy access and read/write capabilities"""

  __slots__ = [
    "Session",
    "User_UserArn",
    "User_Username",
    "User_AccessKey",
    "User_SecretKey",
    "SQS_QueueUrl",
    "InputBucketName",
    "OutputBucketName",
    ]
  
  def __init__(self, *, Session):
    self.Session = Session
  
  def _build_config_file_key(self):
    raise NotImplementedError()
    
  def _get_bucket_name(self):
    raise NotImplementedError()
  
  def _get_from_s3(self):
    key = self._build_config_file_key()
    # Get the file from S3
    json = S3.GetJSON(session=self.Session, bucket=self._get_bucket_name(), key=key)
    # Convert data to a dict
    # Set it to the data field
  

class EnvironmentConfig(Config):
  """Wraps around an environment's config file"""

  __slots__ = [
    "EnvironmentID",
    "ElasticTranscoder_RoleArn",
    "ElasticTranscoder_PipelineArn",
    "ElasticTranscoder_TopicArn",
    "ElasticTranscoder_WebPresetArn",
    "ElasticTranscoder_WebmPresetArn",
    ]
  
  def __init__(self, *, EnvironmentID, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.EnvironmentID = EnvironmentID
    
  def _build_config_file_key(self):
    return "{0}/DocStruct/environment.json".format(self.EnvironmentID)
  

class ApplicationConfig(Config):
  """Wraps around an application's config file"""

  __slots__ = [
    "EnvironmentID",
    "ApplicationID",
    "KeyPrefix",
    ]
  
  def __init__(self, *, EnvironmentID, ApplicationID, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.EnvironmentID = EnvironmentID
    self.ApplicationID = ApplicationID

  def _build_config_file_key(self):
    return "{0}/{1}/DocStruct/application.json".format(self.EnvironmentID, self.ApplicationID)
