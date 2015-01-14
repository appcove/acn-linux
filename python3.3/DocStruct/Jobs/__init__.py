# vim:encoding=utf-8:ts=2:sw=2:expandtab
import os
import json
import time
import logging

from abc import ABCMeta, abstractmethod
from glob import glob
from importlib import import_module
from DocStruct.Base import GetSession, S3, SQS


DATADIR_PATH = '/tmp'
NUM_MAX_RETRIES = 3
JOBS_MAP = {}


class NoMoreRetriesException(Exception):
  """This exception signifies that the job cannot be retried any more times"""
  pass


def JobWithName(jobname):
  assert isinstance(jobname, str)
  def Job(func):
    """Registers a callable to handle a job with given name"""
    assert callable(func)
    JOBS_MAP[jobname if len(jobname) else func.__name__] = func
    def Inner(*a, **kw):
      return func(*a, **kw)
    return Inner
  return Job


Job = JobWithName('')


class S3BackedFile(object):

  __metaclass__ = ABCMeta

  def __init__(self, *, InputKey, OutputKeyPrefix, Config, Logger):
    self.InputKey = InputKey
    self.OutputKeyPrefix = OutputKeyPrefix
    self.Config = Config
    self.Logger = Logger
    # Mainly populated by child class
    self.Output = {
      'InputKey': self.InputKey,
      'OutputKeyPrefix': self.OutputKeyPrefix,
      'Outputs': [],
      }
    self._LocalFilePath = None
    self._FilePathsToCleanup = []

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    # Write to output.json if there was no exception
    if not exc_type:
        S3.PutJSON(
          session=self.Config.Session,
          bucket=self.Config.S3_OutputBucket,
          key="{0}output.json".format(self.OutputKeyPrefix),
          content=self.Output
          )
        self.Logger.debug("Wrote output.json")
        self.Logger.debug(self.Output)
    # We're done with the temp file, delete it
    if len(self._FilePathsToCleanup):
      for fpath in self._FilePathsToCleanup:
        if os.path.exists(fpath):
          os.remove(fpath)
          self.Logger.debug("Removed {0}".format(fpath))

  @property
  def LocalFilePath(self):
    # Check if we've already downloaded the file from S3
    if not self._LocalFilePath or not os.path.exists(self._LocalFilePath):
      # Prepare path to which the file will be saved
      fpath = self.GetLocalFilePathFromS3Key(Key=self.InputKey)
      # Download and save to file
      if not os.path.exists(fpath):
        with open(fpath, 'wb') as fp:
          fp.write(S3.GetObject(session=self.Config.Session, bucket=self.Config.S3_InputBucket, key=self.InputKey))
      # Set _LocalFilePath
      self._LocalFilePath = fpath
      # Add the file to the cleanup array
      self.MarkFilePathForCleanup(fpath)
      # Log message and we're done
      self.Logger.debug("Download {0} from S3 and saved to {1}".format(self.InputKey, self._LocalFilePath))
    return self._LocalFilePath

  def MarkFilePathForCleanup(self, FilePath):
    self._FilePathsToCleanup.append(FilePath)

  @abstractmethod
  def Run(self):
    pass

  @classmethod
  def GetLocalFilePathFromS3Key(cls, *, Key, KeyPrefix=''):
    if KeyPrefix.endswith('/'):
      KeyPrefix = KeyPrefix[:-1]
    if Key.startswith('/'):
      Key = Key[1:]
    Key = os.path.join(KeyPrefix, Key)
    return os.path.join(DATADIR_PATH, Key.replace('/', '--'))


def ProcessMessage(*, Message, Config, Logger):
  """Process a message

  :param Message: JSON encoded job specification
  :type Message: str
  :param Config: The configurations passed to this instance
  :type Config: DocStruct.Config.Config
  :param Logger: A logger
  :type Logger: logging.Logger
  :return: Return value from job
  :rtype: any
  """
  if not Message:
    return None
  m = json.loads(Message)
  # Check if the message was sent by the transcoder
  if not isinstance(m, dict):
    raise NoMoreRetriesException('{0} could not be converted to dict'.format(Message))
  # Check to see who sent this message
  if m.get('Type', '') == 'Notification' and m.get('Message'):
    msg = json.loads(m['Message'])
    if not msg:
      return None
    # We only have work to do if the job has completed
    if msg and msg['state'] == 'COMPLETED':
      Logger.debug("Transcoder Job with ID = {0} has completed".format(msg['jobId']))
    elif msg['state'] == 'ERROR':
      Logger.info("ERROR: Transcoder Job with ID = {0} failed.".format(msg['jobId']))
    else:
      return None
    # Write the message to the relevant file in S3
    return S3.PutJSON(
      session=Config.Session,
      bucket=Config.S3_OutputBucket,
      key="{0}output.json".format(msg['outputKeyPrefix']),
      content=msg
      )
  elif m.get('Type', '') != 'Job' or 'Job' not in m or not isinstance(m.get('Params'), dict) or m.get('NumRetries', 0) >= NUM_MAX_RETRIES:
    # There are a few limitations for jobs specifications
    # 1. The format is a dict
    # 2. Name of the module that contains the job to call is available by accessing the 'Job' key
    # 3. Keyword arguments to the job are specified via the 'Params' key
    # 4. A field named NumRetries if specified contains an int
    raise NoMoreRetriesException('Invalid job specification')
  # It is assumed that every job is available as a module in the Jobs package.
  jobs_func = JOBS_MAP.get(m['Job'])
  if callable(jobs_func):
    return jobs_func(Config=Config, Logger=Logger, **m['Params'])
  else:
    Logger.error("Could not find a job handler for {0}".format(m['Job']))
  return None


def Run(*, DataDirPath, Config, Logger, SleepAmount=20):
  # Change data directory to that which is specified on the command line
  global DATADIR_PATH
  DATADIR_PATH = DataDirPath

  # Import all the other modules in this package
  # This way, we make sure that all the jobs are registered and ready to use while processing
  # Loop over the list of files in the DocStruct.Jobs package and import each one
  for modname in glob(os.path.join(os.path.dirname(__file__), "*.py")):
    bn = os.path.basename(modname)
    # Ignore current package, __main__ and __init__
    if bn not in (os.path.basename(__file__), '__main__.py', '__init__.py'):
      import_module("DocStruct.Jobs.{0}".format(bn.replace('.py', '')))

  QueueUrl = Config.SQS_QueueUrl

  # Log a starting message
  Logger.debug("Starting process {0}".format(os.getpid()))

  # Start an infinite loop to start polling for messages
  while True:
    Logger.debug('Listening to SQS')
    m = None
    session = Config.Session
    try:
      m, receipt_handle = SQS.GetMessageFromQueue(session, QueueUrl, delete_after_receive=True)
      Logger.debug("Message recieved {0}".format(str(m)))
      ProcessMessage(Message=m, Config=Config, Logger=Logger)
    except NoMoreRetriesException:
      pass
    except (KeyboardInterrupt, SystemExit):
      break
    except Exception:
      Logger.exception("Exception while processing job {0}".format(m))
      if m:
        mdict = json.loads(m)
        if 'NumRetries' not in mdict:
          mdict['NumRetries'] = 1
        else:
          mdict['NumRetries'] += 1
        SQS.PostMessage(session, QueueUrl, json.dumps(mdict))
      # Sleep for some time before trying again
      time.sleep(SleepAmount)

  # Log a message about stopping
  Logger.debug("Stopping process {0}".format(os.getpid()))
