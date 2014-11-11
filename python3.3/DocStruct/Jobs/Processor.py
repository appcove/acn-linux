# vim:encoding=utf-8:ts=2:sw=2:expandtab
import os
import time
import json

# If we've reached here, it means all the config items we need to make this work are available
from glob import glob
from importlib import import_module
from DocStruct.Base import GetSession, SQS
from . import ProcessMessage, NoMoreRetriesException


def Run(*, Config, Logger, SleepAmount=20):
  # Import all the other modules in this package
  # This way, we make sure that all the jobs are registered and ready to use while processing
  # Loop over the list of files in the DocStruct.Jobs package and import each one
  for modname in glob(os.path.join(os.path.dirname(__file__), "*.py")):
    bn = os.path.basename(modname)
    # Ignore current package (__main__) and __init__
    if bn not in ('__main__.py', '__init__.py'):
      import_module("DocStruct.Jobs.{0}".format(bn.replace('.py', '')))

  QueueUrl = Config['SQS']['QueueUrl']
  AccessKey = Config['User']['AccessKey']
  SecretKey = Config['User']['SecretKey']

  # Log a starting message
  Logger.debug("Starting process {0}".format(os.getpid()))

  # Start an infinite loop to start polling for messages
  while True:
    m = None
    session = GetSession(AccessKey=AccessKey, SecretKey=SecretKey)
    try:
      m, receipt_handle = SQS.GetMessageFromQueue(session, QueueUrl, delete_after_receive=True)
      ProcessMessage(Session=session, Message=m, Config=Config, Logger=Logger)
    except NoMoreRetriesException:
      pass
    except (KeyboardInterrupt, SystemExit):
      # TODO: remove file added previously
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
