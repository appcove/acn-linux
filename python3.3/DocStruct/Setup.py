# vim:encoding=utf-8:ts=2:sw=2:expandtab
# -*- coding: utf-8 -*-
import json

from collections import namedtuple
from base64 import b64encode
from .Base import GetSession, S3, ElasticTranscoder, SNS, SQS, EC2, IAM, CloudFront


AC_AWSAMSID = "ami-c653e2ae"
AC_AWSPEMFILENAME = "awstest"


Config = namedtuple("Config", [
    "userarn",
    "username",
    "accesskey",
    "secretkey",
    "rolearn",
    "pipelinearn",
    "topicarn",
    "queueurl",
    "inputbucketname",
    "outputbucketname",
    "webpresetarn",
    "webmpresetarn",
    "keyprefix",
])


def _GetConfigFilename(envname, localprefix=""):
    if localprefix:
        return "{0}/.config.json".format(localprefix, envname)
    return "{0}-config.json".format(envname)


def GetGlobalConfig(session, envname, credsfilename):
    conffilename = _GetConfigFilename(envname)
    if not session:
        session = GetSession(credsfilename)
    confjson = S3.GetObject(session=session, bucket=".configs", key=conffilename)
    if not confjson:
        return None
    confdict = json.loads(confjson.decode('utf-8'))
    return Config(
        userarn=confdict["User"]["Arn"],
        username=confdict["User"]["Username"],
        accesskey=confdict["User"]["AccessKey"],
        secretkey=confdict["User"]["SecretKey"],
        rolearn=confdict["ElasticTranscoder"]["RoleArn"],
        pipelinearn=confdict["ElasticTranscoder"]["PipelineArn"],
        topicarn=confdict["ElasticTranscoder"]["TopicArn"],
        webpresetarn=confdict["ElasticTranscoder"]["WebPresetArn"],
        webmpresetarn=confdict["ElasticTranscoder"]["WebmPresetArn"],
        inputbucketname=confdict["S3"]["InputBucket"],
        outputbucketname=confdict["S3"]["OutputBucket"],
        queueurl=confdict["SQS"]["QueueUrl"],
        keyprefix="",
        )


def SaveGlobalConfig(session, envname, conf):
    conffilename = _GetConfigFilename(envname)
    confjson = json.dumps({
        "User": {
            "Arn": conf.userarn,
            "Username": conf.username,
            "AccessKey": conf.accesskey,
            "SecretKey": conf.secretkey,
            },
        "ElasticTranscoder": {
            "RoleArn": conf.rolearn,
            "PipelineArn": conf.pipelinearn,
            "TopicArn": conf.topicarn,
            "WebPresetArn": conf.webpresetarn,
            "WebmPresetArn": conf.webmpresetarn,
            },
        "S3": {
            "InputBucket": conf.inputbucketname,
            "OutputBucket": conf.outputbucketname,
            },
        "SQS": {
            "QueueUrl": conf.queueurl,
            }
        })
    S3.PutObject(session=session, bucket=".configs", key=conffilename, content=confjson)
    return confjson


def GetLocalConfig(session, envname, localprefix, credsfilename, globalconfig=None):
    conffilename = _GetConfigFilename(envname, localprefix=localprefix)
    if not session:
        session = GetSession(credsfilename)
    confjson = S3.GetObject(session=session, bucket=envname, key=conffilename)
    if not confjson:
        return None
    confdict = json.loads(confjson.decode('utf-8'))
    return Config(
        userarn=confdict["User"]["Arn"],
        username=confdict["User"]["Username"],
        accesskey=confdict["User"]["AccessKey"],
        secretkey=confdict["User"]["SecretKey"],
        rolearn=globalconfig.rolearn if globalconfig else "",
        pipelinearn=globalconfig.pipelinearn if globalconfig else "",
        topicarn=globalconfig.topicarn if globalconfig else "",
        webpresetarn=globalconfig.webpresetarn if globalconfig else "",
        webmpresetarn=globalconfig.webmpresetarn if globalconfig else "",
        inputbucketname=globalconfig.inputbucketname if globalconfig else "",
        outputbucketname=globalconfig.outputbucketname if globalconfig else "",
        queueurl=globalconfig.queueurl if globalconfig else "",
        keyprefix=confdict["S3"]["KeyPrefix"],
        )


def SaveLocalConfig(session, envname, keyprefix, conf):
    conffilename = _GetConfigFilename(envname, localprefix=keyprefix)
    confjson = json.dumps({
        "User": {
            "Arn": conf.userarn,
            "Username": conf.username,
            "AccessKey": conf.accesskey,
            "SecretKey": conf.secretkey,
            },
        "S3": {
            "KeyPrefix": keyprefix,
            }
        })
    S3.PutObject(session=session, bucket=envname, key=conffilename, content=confjson)
    return confjson


def LaunchInstances(*, Session, UserData, NumInstances=1):
    """Launches <NumInstances> number of instances
    
    :param Session: Session to use for communication
    :type Session: boto3.session.Session
    :param UserData: User data to pass to the instance
    :type UserData: str
    :param NumInstances: Number of instances to start
    :type NumInstances: int
    :return: The IDs of the instances started
    :rtype: list
    """
    return [EC2.StartInstance(session=Session, imageid=AC_AWSAMSID, pemfilename=AC_AWSPEMFILENAME, userdata=UserData) for i in range(NumInstances)]


def MakeGlobalEnvironment(credsfilename, envname, withdistribution=False):
    """Sets up the environment per the new specs.
    
    NOTE: this environment is for global usage.
    """
    # Get a session to use for AWS API access
    session = GetSession(credsfilename=credsfilename)
    # Get bucket class
    inputbucket = S3.GetOrCreateBuckets(session, envname)
    S3.SetBucketCorsPolicy(inputbucket)
    # upload the crossdomain.xml and clientaccesspolicy.xml files into the bucket
    S3.SetupBucketForFlashAndSilverlight(session, inputbucket.bucket)
    # Create a CloudFront distribution for serving files from inputbucket
    if withdistribution:
        distresp = CloudFront.CreateDistributionForBucket(session, inputbucket.bucket)
    # Create SQS queue for environment
    qurl = SQS.CreateQueue(session, envname)
    # NOTE: since we only return the qurl, we need a way to convert the URL to an ARN
    # TODO: at some point we need to look at getting the ARN directly from the API
    qarn = SQS.ConvertURLToArn(qurl)
    # Create SNS topic so that the pipeline can publish notifications
    topic = SNS.CreateTopic(session, envname)
    # Create a pipeline for transcoding videos
    policyname = "Transcoder-Policy-{0}".format(envname)
    transcodername = "Transcoder-{0}".format(envname)
    role = IAM.SetupRoleWithPolicy(
        session,
        transcodername,
        policyname,
        IAM.GetPolicyStmtForTranscoders(envname, topic.topic_arn, qarn)
        )
    roledict = role.get(role_name=role.role_name)
    role_arn = roledict["Role"]["Arn"]
    # Create a pipeline to handle input from <inputbucket> and leave output in <inputbucket>
    pipeline = ElasticTranscoder.CreatePipeline(
        session,
        "{0}-Transcoding".format(envname),
        role_arn,
        inputbucket.bucket,
        inputbucket.bucket,
        topic.topic_arn
        )
    pipelinedict = pipeline.get()
    pipeline_arn = pipelinedict["Pipeline"]["Arn"]
    # While we're at it, lets get the web preset and save it as in our config
    web_presetarn = ElasticTranscoder.GetPresetWithName(session, "System preset: Web")
    # Create a preset to convert files to webm format
    webm_presetarn = ElasticTranscoder.GetPresetWithName(session, "User preset: Webm")
    if not webm_presetarn:
        webm_presetarn = ElasticTranscoder.CreatePreset(session, ElasticTranscoder.WEBM_PRESET_DATA)
    # We can subscribe to the SNS topic using the SQS queue so that elastic transcoder
    # notifications are handled by the same jobs processing server
    SNS.CreateSQSQueueSubscription(session, qarn, topic.topic_arn)
    # # We also need to add a permission for the queue so that SNS is able to send messages to this queue
    # SQS.AddPermissionForSNSTopic(session, topic.topic_arn, qurl)
    # Create a user that EC2 will use
    user, credentials = IAM.GetOrCreateUser(
        session,
        envname,
        "User-Policy-{0}".format(envname),
        IAM.GetPolicyStmtForUser(inputbucket.bucket, inputbucket.bucket),
        )
    usermeta = user.get()
    # Save the environment config so that when we start instances, we can pass the config to it as well
    conftuple = Config(
        userarn=usermeta["User"]["Arn"],
        username=credentials.user_name,
        accesskey=credentials.access_key_id,
        secretkey=credentials.secret_access_key,
        rolearn=role_arn,
        pipelinearn=pipeline_arn,
        topicarn=topic.topic_arn,
        queueurl=qurl,
        inputbucketname=inputbucket.bucket,
        outputbucketname=inputbucket.bucket,
        webpresetarn=web_presetarn,
        webmpresetarn=webm_presetarn,
        keyprefix="",
        )
    confjson = SaveGlobalConfig(session, envname, conftuple)
    # We can also start instances to handle queue
    instances = LaunchInstances(Session=session, UserData=b64encode(confjson.encode("utf-8")).decode("utf-8"))
    # Print out results
    return conftuple


def MakeLocalEnvironment(credsfilename, envname, keyprefix, globalconfig=None):
    """Sets up the local environment to hook up to the global environment.
    
    NOTE: this is what an app would like to use.
    """
    # Get a session to use for AWS API access
    session = GetSession(credsfilename=credsfilename)
    # If global config was not passed in, we can fetch it.
    if not globalconfig:
        globalconfig = GetGlobalConfig(session, envname, credsfilename)
        if not globalconfig:
            raise Exception("Global environment with name {0} is not available".format(envname))
    # Now we can create a user for this project with just the right permissions
    # NOTE: http://blogs.aws.amazon.com/security/post/Tx1P2T3LFXXCNB5/Writing-IAM-policies-Grant-access-to-user-specific-folders-in-an-Amazon-S3-bucke
    user, credentials = IAM.GetOrCreateUser(
        session,
        "{0}-{1}".format(envname, keyprefix),
        "User-Policy-{0}-{1}".format(envname, keyprefix),
        IAM.GetPolicyStmtForAppUser(globalconfig.inputbucketname, keyprefix, SQS.ConvertURLToArn(globalconfig.queueurl)),
        )
    usermeta = user.get()
    # Save the environment config so that when we start instances, we can pass the config to it as well
    conftuple = Config(
        userarn=usermeta["User"]["Arn"],
        username=credentials.user_name,
        accesskey=credentials.access_key_id,
        secretkey=credentials.secret_access_key,
        rolearn=globalconfig.rolearn,
        pipelinearn=globalconfig.pipelinearn,
        topicarn=globalconfig.topicarn,
        queueurl=globalconfig.queueurl,
        inputbucketname=globalconfig.inputbucketname,
        outputbucketname=globalconfig.outputbucketname,
        webpresetarn=globalconfig.webpresetarn,
        webmpresetarn=globalconfig.webmpresetarn,
        keyprefix=keyprefix,
        )
    confjson = SaveLocalConfig(session, envname, keyprefix, conftuple)
    # Print out results
    return conftuple


if __name__ == '__main__':
    import sys
    MakeGlobalEnvironment(sys.argv[1], sys.argv[2])

