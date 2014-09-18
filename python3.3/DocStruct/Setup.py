# vim:encoding=utf-8:ts=2:sw=2:expandtab
# -*- coding: utf-8 -*-
import json

from collections import namedtuple
from base64 import b64encode
from .Base import GetSession, S3, ElasticTranscoder, SNS, SQS, EC2, IAM, CloudFront


AC_AWSAMSID = "ami-ae66c6c6"
AC_AWSPEMFILENAME = "awstest"


ConfigTuple = namedtuple("ConfigTuple", [
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
])


def _GetConfigFilename(envname):
    return "{0}-config.json".format(envname)


def GetEnvironmentConfig(session, envname, credsfilename):
    conffilename = _GetConfigFilename(envname)
    if not session:
        session = GetSession(credsfilename)
    confjson = S3.GetObject(session=session, bucket=".configs", key=conffilename)
    if not confjson:
        return None
    confdict = json.loads(confjson)
    return ConfigTuple(
        userarn=confdict["User"]["Arn"],
        username=confdict["User"]["Username"],
        accesskey=confdict["User"]["AccessKey"],
        secretkey=confdict["User"]["SecretKey"],
        rolearn=confdict["ElasticTranscoder"]["RoleArn"],
        pipelinearn=confdict["ElasticTranscoder"]["PipelineArn"],
        topicarn=confdict["ElasticTranscoder"]["TopicArn"],
        queueurl=confdict["SQS"]["QueueUrl"],
        inputbucketname=confdict["S3"]["InputBucket"],
        outputbucketname=confdict["S3"]["OutputBucket"],
        webpresetarn=confdict["ElasticTranscoder"]["WebPresetArn"],
        webmpresetarn=confdict["ElasticTranscoder"]["WebmPresetArn"],
        )


def SaveEnvironmentConfig(session, envname, conf):
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
            "WebPreset": conf.webpresetarn,
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


def MakeEnvironment(envname, credsfilename, withdistribution=False):
    """Sets up the environment per the new specs"""
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
    # Now we can create a user for this project with just the right permissions
    user, credentials = IAM.GetOrCreateUser(
        session,
        envname,
        "User-Policy-{0}".format(envname),
        IAM.GetPolicyStmtForUser(inputbucket.bucket, inputbucket.bucket),
        )
    usermeta = user.get()
    # With the new user credentials, we can create a queue that is controlled by the new user
    usession = GetSession(access_key=credentials.access_key_id, secret_key=credentials.secret_access_key)
    qurl = SQS.CreateQueue(session, envname)
    # Create SNS topic so that the pipeline can publish notifications
    topic = SNS.CreateTopic(session, envname)
    # Create a pipeline for transcoding videos
    policyname = "Transcoder-Policy-{0}".format(envname)
    transcodername = "Transcoder-{0}".format(envname)
    role = IAM.SetupRoleWithPolicy(
        session,
        transcodername,
        policyname,
        IAM.GetPolicyStmtForTranscoders(envname, topic.topic_arn)
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
    # NOTE: since we only return the qurl, we need a way to convert the URL to an ARN
    # TODO: at some point we need to look at getting the ARN directly from the API
    qarn = SQS.ConvertURLToArn(qurl)
    SNS.CreateSQSQueueSubscription(session, qarn, topic.topic_arn)
    # Save the environment config so that when we start instances, we can pass the config to it as well
    conftuple = ConfigTuple(
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
        )
    confjson = SaveEnvironmentConfig(session, envname, conftuple)
    # We can also start instances to handle queue
    instances = [
        EC2.StartInstance(session=session, imageid=AC_AWSAMSID, pemfilename=AC_AWSPEMFILENAME, userdata=b64encode(confjson.encode("utf-8")).decode("utf-8")),
        # EC2.StartInstance(imageid=AC_AWSAMSID, pemfilename=AC_AWSPEMFILENAME, user_data=b64encode(confjson)),
        ]
    # Print out results
    return conftuple


if __name__ == '__main__':
    import sys
    MakeEnvironment(sys.argv[1], sys.argv[2])
