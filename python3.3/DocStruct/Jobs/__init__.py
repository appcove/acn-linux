# vim:encoding=utf-8:ts=2:sw=2:expandtab
import json
import importlib
import logging

from DocStruct.Base import S3


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


def ProcessMessage(*, Session, Message, Config, Logger):
  """Process a message
  
  :param Session: Session for AWS access
  :type Session: boto3.session.Session
  :param Message: JSON encoded job specification
  :type Message: str
  :param Config: The configurations passed to this instance
  :type Config: dict
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
    # We only have work to do if the job has completed
    if msg and msg['state'] == 'COMPLETED':
      # TODO: remove running.json file previously inserted
      # Log the notification
      Logger.debug("Handled notification for {0}".format(msg))
      # This message was sent by the transcoder
      return S3.PutJSON(
        session=Session,
        bucket=Config['S3']['OutputBucket'],
        key="{0}output.json".format(msg['outputKeyPrefix']),
        content=msg
        )
    return None
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
    # TODO: add running.json file
    return jobs_func(Session=Session, Config=Config, Logger=Logger, **m['Params'])
  else:
    Logger.error("Could not find a job handler for {0}".format(m['Job']))
  return None
