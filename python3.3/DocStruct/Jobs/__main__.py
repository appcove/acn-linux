# vim:encoding=utf-8:ts=2:sw=2:expandtab
import time
import json
import base64
import urllib.request

from DocStruct.Base import GetSession, SQS
from . import ProcessMessage, NoMoreRetriesException


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

# Start an infinite loop to start polling for messages
while True:
    m = None
    session = GetSession(access_key=ACCESS_KEY, secret_key=SECRET_KEY)
    try:
        m, receipt_handle = SQS.GetMessageFromQueue(session, QUEUE_URL, delete_after_receive=True)
        ProcessMessage(session, m, CONFIG)
    except NoMoreRetriesException:
        pass
    except (KeyboardInterrupt, SystemExit):
        pass
    except Exception as e:
        if m:
            if 'NumRetries' not in m:
                m['NumRetries'] = 1
            else:
                m['NumRetries'] += 1
            SQS.PostMessage(session, QUEUE_URL, json.dumps(m))
    # Sleep for some time before trying again
    time.sleep(SLEEP_AMOUNT)

