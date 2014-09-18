# vim:encoding=utf-8:ts=2:sw=2:expandtab
from urllib.parse import urlparse
from boto3.core.exceptions import ServerError


def CreateQueue(session, queuename, message_retention_period=1209600, visibility_timeout=60):
    """Creates a queue with name
    
    :param session: The session to use for AWS requests
    :type session: boto3.session.Session
    :param queuename: Name of the queue being created
    :type queuename: str
    :param message_retention_period: Number of seconds the message will be retained for (DEFAULT: 14 days - AWS max)
    :type message_retention_period: int
    :param visibility_timeout: Timeout in seconds for which a received message will be invisible to other receivers in the queue
    :type visibility_timeout: int
    :return: URL for the new queue
    :rtype: str
    """
    sqsconn = session.connect_to("sqs")
    Queue = session.get_resource("sqs", "Queue")
    queue = Queue(connection=sqsconn)
    try:
        qmeta = queue.get(queue_name=queuename)
    except ServerError:
        Queues = session.get_collection("sqs", "QueueCollection")
        queues = Queues(connection=sqsconn)
        q = queues.create(queue_name=queuename, attributes={
            "MessageRetentionPeriod": "%d" % message_retention_period,
            "VisibilityTimeout": "%d" % visibility_timeout,
        })
        qmeta = q.get(queue_name=queuename)
    return qmeta['QueueUrl']


def PostMessage(session, queueurl, message):
    """Post a message to the given queue
    
    :param session: Session to use for AWS access
    :type session: boto3.session.Session
    :param queueurl: URL of the queue to which we will post messages
    :type queueurl: str
    :param message: Body of message to post
    :type message: str
    :return: The created message
    :rtype: object
    """
    sqsconn = session.connect_to("sqs")
    Messages = session.get_collection("sqs", "MessageCollection")
    messages = Messages(connection=sqsconn, queue_url=queueurl)
    m = messages.create(message_body=message)
    return m


def GetMessageFromQueue(session, queueurl, processfunc):
    """Get message from the queue to process
    
    :param session: Session to use for AWS access
    :type session: boto3.session.Session
    :param queueurl: URL of the queue from which to receive messages
    :type queueurl: str
    :param processfunc: A callable that will process the message. The callable must accept the message body as parameter
    :type processfunc: callable
    :return: True if the message was retrieved and handled successfully
    :rtype: bool
    """
    sqsconn = session.connect_to("sqs")
    Messages = session.get_collection("sqs", "MessageCollection")
    messages = Messages(connection=sqsconn, queue_url=queueurl)
    ok = False
    # Try to get 5 messages at a time by waiting atmost 20 seconds
    for m in messages.each(wait_time_seconds=20, max_number_of_messages=1):
        try:
            ok = processfunc(m.body)
        except Exception:
            # TODO: we can elevate this message to the error queue to figure out what is happening
            pass
        else:
            # If processing was successful, we can delete the message
            if ok:
                m.delete(queue_url=queueurl, receipt_handle=m.receipt_handle)
    return ok


def ConvertURLToArn(url):
    parsed = urlparse(url)
    # regionstr = parsed.netloc.replace(".amazonaws.com", "").replace(".", ":")
    regionstr = "us-east-1"
    specificstr = parsed.path.replace("/", ":")
    return "arn:aws:sqs:" + regionstr + specificstr
