# vim:encoding=utf-8:ts=2:sw=2:expandtab
import os
import sys
import time
import json
import base64
import urllib.request

SLEEP_AMOUNT = 20
"""Seconds to sleep until next poll of SQS"""

USER_DATA_URL = "http://169.254.169.254/latest/user-data"
"""URL from where we can get user-data provided to the instance during launch"""

CONFIG = json.loads(base64.b64decode(urllib.request.urlopen(USER_DATA_URL).read()).decode('utf-8'))
"""Configuration data sent to this instance when it was launched"""

EXAMPLE_CONFIG = {
  'ElasticTranscoder': {
    'RoleArn': '',
    'WebmPresetArn': '',
    'PipelineArn': '',
    'WebPreset': '',
    'TopicArn': ''
  },
  'User': {
    'Arn': '',
    'Username': '',
    'AccessKey': '',
    'SecretKey': ''
  },
  'S3': {
    'OutputBucket': '',
    'InputBucket': ''
  },
  'SQS': {
    'QueueUrl': ''
  }
}

QUEUE_URL = CONFIG['SQS']['QueueUrl']
ACCESS_KEY = CONFIG['User']['AccessKey']
SECRET_KEY = CONFIG['User']['SecretKey']

# TODO: Add a file to S3 denoting that this instance/process is ready.

# Construct a logger for this process
import logging
import logging.handlers
# This should be part of configuration
LOGLEVEL = logging.DEBUG
# Setup the logger now
LOGGER = logging.getLogger('DocStruct')
LOGGER.setLevel(LOGLEVEL)

# We need to construct a handler
if len(sys.argv) > 1:
  lh = logging.handlers.TimedRotatingFileHandler(sys.argv[1], when='D', interval=1)
  lh.setLevel(LOGLEVEL)
else:
  # Create a logger that logs to stderr (default for StreamHandler)
  lh = logging.StreamHandler()
  lh.setLevel(LOGLEVEL)

# Setup formatter
f = logging.Formatter('%(asctime)s, %(levelname)s, %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
lh.setFormatter(f)
LOGGER.addHandler(lh)

# If we've reached here, it means all the config items we need to make this work are available
from DocStruct.Base import GetSession, SQS
from . import ProcessMessage, NoMoreRetriesException

# Now we import all the other modules in this package
# This way, we make sure that all the jobs are registered and ready to use while processing
from glob import glob
from importlib import import_module
# Loop over the list of files in the DocStruct.Jobs package and import each one
for modname in glob(os.path.join(os.path.dirname(__file__), "*.py")):
  bn = os.path.basename(modname)
  # Ignore current package (__main__) and __init__
  if bn not in ('__main__.py', '__init__.py'):
    import_module("DocStruct.Jobs.{0}".format(bn.replace('.py', '')))

# Log a starting message
LOGGER.debug("Starting process {0}".format(os.getpid()))

# Start an infinite loop to start polling for messages
while True:
  m = None
  session = GetSession(AccessKey=ACCESS_KEY, SecretKey=SECRET_KEY)
  try:
    m, receipt_handle = SQS.GetMessageFromQueue(session, QUEUE_URL, delete_after_receive=True)
    ProcessMessage(Session=session, Message=m, Config=CONFIG, Logger=LOGGER)
  except NoMoreRetriesException:
    pass
  except (KeyboardInterrupt, SystemExit):
    # TODO: remove file added previously
    break
  except Exception as e:
    LOGGER.exception("Exception while processing job {0}".format(m))
    if m:
      if 'NumRetries' not in m:
        m['NumRetries'] = 1
      else:
        m['NumRetries'] += 1
      SQS.PostMessage(session, QUEUE_URL, json.dumps(m))
    # Sleep for some time before trying again
    time.sleep(SLEEP_AMOUNT)

# Log a message about stopping
LOGGER.debug("Stopping process {0}".format(os.getpid()))
