# vim:encoding=utf-8:ts=2:sw=2:expandtab
# -*- coding: utf-8 -*-
import json

from collections import namedtuple
from base64 import b64encode
from .Base import GetSession, S3, ElasticTranscoder, SNS, SQS, EC2, IAM, CloudFront
from .Config import ApplicationConfig, EnvironmentConfig


AC_AWSAMSID = "ami-c653e2ae"
AC_AWSPEMFILENAME = "awstest"


# Config = namedtuple("Config", [
#     "userarn",
#     "username",
#     "accesskey",
#     "secretkey",
#     "rolearn",
#     "pipelinearn",
#     "topicarn",
#     "queueurl",
#     "inputbucketname",
#     "outputbucketname",
#     "webpresetarn",
#     "webmpresetarn",
#     "keyprefix",
# ])


# def _GetConfigFilename(localprefix=""):
#     if localprefix and not localprefix.endswith("/"):
#         localprefix += "/"
#     return "{0}DocStruct/{1}.json".format(localprefix, "application" if localprefix else "environment")


# def GetGlobalConfig(session, envname, credsfilename, raw=False):
#     conffilename = _GetConfigFilename()
#     if not session:
#         session = GetSession(credsfilename)
#     confjson = S3.GetObject(session=session, bucket=envname, key=conffilename)
#     if not confjson:
#         return None
#     if raw:
#         return confjson
#     confdict = json.loads(confjson.decode('utf-8'))
#     return Config(
#         userarn=confdict["User"]["Arn"],
#         username=confdict["User"]["Username"],
#         accesskey=confdict["User"]["AccessKey"],
#         secretkey=confdict["User"]["SecretKey"],
#         rolearn=confdict["ElasticTranscoder"]["RoleArn"],
#         pipelinearn=confdict["ElasticTranscoder"]["PipelineArn"],
#         topicarn=confdict["ElasticTranscoder"]["TopicArn"],
#         webpresetarn=confdict["ElasticTranscoder"]["WebPresetArn"],
#         webmpresetarn=confdict["ElasticTranscoder"]["WebmPresetArn"],
#         inputbucketname=confdict["S3"]["InputBucket"],
#         outputbucketname=confdict["S3"]["OutputBucket"],
#         queueurl=confdict["SQS"]["QueueUrl"],
#         keyprefix="",
#         )


# def SaveGlobalConfig(session, envname, conf):
#     conffilename = _GetConfigFilename()
#     conf = {
#         "User": {
#             "Arn": conf.userarn,
#             "Username": conf.username,
#             "AccessKey": conf.accesskey,
#             "SecretKey": conf.secretkey,
#             },
#         "ElasticTranscoder": {
#             "RoleArn": conf.rolearn,
#             "PipelineArn": conf.pipelinearn,
#             "TopicArn": conf.topicarn,
#             "WebPresetArn": conf.webpresetarn,
#             "WebmPresetArn": conf.webmpresetarn,
#             },
#         "S3": {
#             "InputBucket": conf.inputbucketname,
#             "OutputBucket": conf.outputbucketname,
#             },
#         "SQS": {
#             "QueueUrl": conf.queueurl,
#             }
#         }
#     S3.PutJSON(session=session, bucket=envname, key=conffilename, content=conf)
#     return conf


# def GetLocalConfig(session, envname, localprefix, credsfilename, globalconfig=None, raw=False):
#     conffilename = _GetConfigFilename(localprefix=localprefix)
#     if not session:
#         session = GetSession(credsfilename)
#     confjson = S3.GetObject(session=session, bucket=envname, key=conffilename)
#     if not confjson:
#         return None
#     if raw:
#         return confjson
#     confdict = json.loads(confjson.decode('utf-8'))
#     return Config(
#         userarn=confdict["User"]["Arn"],
#         username=confdict["User"]["Username"],
#         accesskey=confdict["User"]["AccessKey"],
#         secretkey=confdict["User"]["SecretKey"],
#         rolearn=globalconfig.rolearn if globalconfig else "",
#         pipelinearn=globalconfig.pipelinearn if globalconfig else "",
#         topicarn=globalconfig.topicarn if globalconfig else "",
#         webpresetarn=globalconfig.webpresetarn if globalconfig else "",
#         webmpresetarn=globalconfig.webmpresetarn if globalconfig else "",
#         inputbucketname=globalconfig.inputbucketname if globalconfig else "",
#         outputbucketname=globalconfig.outputbucketname if globalconfig else "",
#         queueurl=globalconfig.queueurl if globalconfig else "",
#         keyprefix=confdict["S3"]["KeyPrefix"],
#         )


# def SaveLocalConfig(session, envname, keyprefix, conf):
#     conffilename = _GetConfigFilename(localprefix=keyprefix)
#     conf = {
#         "User": {
#             "Arn": conf.userarn,
#             "Username": conf.username,
#             "AccessKey": conf.accesskey,
#             "SecretKey": conf.secretkey,
#             },
#         "S3": {
#             "KeyPrefix": keyprefix,
#             }
#         }
#     S3.PutJSON(session=session, bucket=envname, key=conffilename, content=conf)
#     return conf


def LaunchInstances(*, Session, UserData, AMI, NumInstances=1):
    """Launches <NumInstances> number of instances
    
    :param Session: Session to use for communication
    :type Session: boto3.session.Session
    :param UserData: User data to pass to the instance
    :type UserData: str
    :param AMI: The AMI to use for launching instances
    :type AMI: str
    :param NumInstances: Number of instances to start
    :type NumInstances: int
    :return: The IDs of the instances started
    :rtype: list
    """
    return [EC2.StartInstance(session=Session, imageid=AMI, pemfilename=AC_AWSPEMFILENAME, userdata=UserData) for i in range(NumInstances)]


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
    config = EnvironmentConfig(Session=session, EnvironmentID=envname)
    # Set the user credentials
    config.User_Arn = usermeta["User"]["Arn"]
    config.User_Username = credentials.user_name
    config.User_AccessKey = credentials.access_key_id
    config.User_SecretKey = credentials.secret_access_key
    # Set the elastic transcoder config
    config.ElasticTranscoder_RoleArn = role_arn
    config.ElasticTranscoder_PipelineArn = pipeline_arn
    config.ElasticTranscoder_TopicArn = topic.topic_arn
    config.ElasticTranscoder_WebPresetArn = web_presetarn
    config.ElasticTranscoder_WebmPresetArn = webm_presetarn
    # Set the S3 config
    config.S3_InputBucket = inputbucket.bucket
    config.S3_OutputBucket = inputbucket.bucket
    # Set SQS config
    config.SQS_QueueUrl = qurl
    # Now we can save the config file
    return config.Save()


def MakeLocalEnvironment(credsfilename, envname, keyprefix, globalconfig=None):
    """Sets up the local environment to hook up to the global environment.
    
    NOTE: this is what an app would like to use.
    """
    # Get a session to use for AWS API access
    session = GetSession(credsfilename=credsfilename)
    # If global config was not passed in, we can fetch it.
    if not globalconfig:
        globalconfig = EnvironmentConfig(Session=session, EnvironmentID=envname)
        if not globalconfig.S3_InputBucket:
            raise Exception("Global environment with name {0} is not available".format(envname))
    # Now we can create a user for this project with just the right permissions
    # NOTE: http://blogs.aws.amazon.com/security/post/Tx1P2T3LFXXCNB5/Writing-IAM-policies-Grant-access-to-user-specific-folders-in-an-Amazon-S3-bucke
    user, credentials = IAM.GetOrCreateUser(
        session,
        "{0}-{1}".format(envname, keyprefix),
        "User-Policy-{0}-{1}".format(envname, keyprefix),
        IAM.GetPolicyStmtForAppUser(globalconfig.S3_InputBucket, keyprefix, SQS.ConvertURLToArn(globalconfig.SQS_QueueUrl)),
        )
    usermeta = user.get()
    # Save the application config
    config = ApplicationConfig(Session=session, EnvironmentID=envname, ApplicationID=keyprefix)
    # Set the user credentials
    config.User_Arn = usermeta["User"]["Arn"]
    config.User_Username = credentials.user_name
    config.User_AccessKey = credentials.access_key_id
    config.User_SecretKey = credentials.secret_access_key
    # Now we can save the config file
    return config.Save()
