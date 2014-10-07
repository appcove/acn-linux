# vim:encoding=utf-8:ts=2:sw=2:expandtab

def StartInstance(*, session, imageid, pemfilename, instancetype="t1.micro", userdata=""):
    """Starts an instance of specified imageid

    NOTE: when this function returns, the instance is still NOT fully started. We may need to
    wait a few minutes before we can access the instance via public IP.
    
    :param session: Session to use for AWS access
    :type session: boto3.session.Session
    :param imageid: ID of the image to use for spawning instances
    :type imageid: str
    :param pemfilename: Name of the AWS access key that will be used to SSH into the instances
    :type pemfilename: str
    :param instancetype: Type of instance to start
    :type instancetype: str
    :param userdata: User data to send to the instance
    :type userdata: str
    :return: ID of instance that was started
    :rtype: str
    """
    ec2conn = session.connect_to("ec2")
    ret = ec2conn.run_instances(image_id=imageid, min_count=1, max_count=1, keyname=pemfilename, instance_type=instancetype, user_data=userdata)
    return ret["Instances"][0]


def StopInstance(*, session, instanceid):
    """Stops an instance identified by instance id.

    :param session: Session to use for AWS access
    :type session: boto3.session.Session
    :param instanceid: ID of instance to stop
    :type instanceid: str
    :return: True if all was successful (NOTE: for now this function always returns True)
    :rtype: bool
    """
    ec2conn = session.connect_to("ec2")
    ret = ec2.stop_instances(instance_ids=[instanceid,])
    return True


def ListInstances(*, session, environmentid, instanceid=None):
    # TODO: look at ec2.describe_instances()
    ec2conn = session.connect_to("ec2")
    ret = ec2conn.describe_instances() or {}
    return ret.get('Reservations', [{'Instances': []}])[0]['Instances']


def TerminateInstance(*, session, instanceid):
    """Terminates an instance identified by instance id.

    :param session: Session to use for AWS access
    :type session: boto3.session.Session
    :param instanceid: ID of instance to terminate
    :type instanceid: str
    :return: True if all was successful (NOTE: for now this function always returns True)
    :rtype: bool
    """
    ec2conn = session.connect_to("ec2")
    return ec2conn.terminate_instances(instance_ids=[instanceid,])
