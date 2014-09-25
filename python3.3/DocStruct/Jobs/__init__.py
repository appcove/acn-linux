# vim:encoding=utf-8:ts=2:sw=2:expandtab
import json
import importlib


NUM_MAX_RETRIES = 3


class NoMoreRetriesException(Exception):
    """This exception signifies that the job cannot be retried any more times"""
    pass


def ProcessMessage(session, message):
    """Process a message
    
    :param session: Session for AWS access
    :type session: boto3.session.Session
    :param message: JSON encoded job specification
    :type message: str
    :return: Return value from job
    :rtype: any
    """
    if not message:
        return None
    print("Handling: {0}".format(message))
    m = json.loads(message)
    # There are a few limitations for jobs specifications
    # 1. The format is a dict
    # 2. Name of the module that contains the job to call is available by accessing the 'Job' key
    # 3. Keyword arguments to the job are specified via the 'Params' key
    # 4. A field named NumRetries if specified contains an int
    if not isinstance(m, dict) or 'Job' not in m or not isinstance(m.get('Params'), dict) or m.get('NumRetries', 0) >= NUM_MAX_RETRIES:
        raise NoMoreRetriesException('Invalid job specification')
    # It is assumed that every job is available as a module in the Jobs package.
    jobs_module = importlib.import_module('DocStruct.Jobs.{0}'.format(m['Job']))
    return jobs_module.Main(Session=session, **m['Params'])
