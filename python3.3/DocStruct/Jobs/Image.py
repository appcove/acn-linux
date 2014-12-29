# vim:encoding=utf-8:ts=2:sw=2:expandtab
import os.path
import collections
import subprocess
import mimetypes

from hashlib import sha1
from ..Base import GetSession, S3
from . import Job


BIN_CONVERT = "/usr/bin/convert"
Output = collections.namedtuple('Output', ('Width', 'Height', 'OutputKey'))


def DownloadImageFromS3(Config, SourceKey):
  fpath = os.path.join('/tmp', SourceKey.replace('/', '--'))
  if not os.path.exists(fpath):
    with open(fpath, 'wb') as fp:
      fp.write(S3.GetObject(session=Config.Session, bucket=Config.S3_InputBucket, key=SourceKey))
  return fpath


def ProcessImage(*, Output, Command, SourceKey, OutputKeyPrefix, JobName, Config, Logger):
  Logger.debug("{0} job for {1} started".format(JobName, SourceKey))
  subprocess.check_output(Command, stderr=subprocess.STDOUT)
  Logger.debug("{0} job for {1} completed".format(JobName, SourceKey))
  # Upload new file to S3
  Logger.debug("Starting Upload of {0} to S3".format(Output.OutputKey))
  o_fpath = Command[-1]
  o_type = mimetypes.guess_type(o_fpath)[0]
  o_key = os.path.join(OutputKeyPrefix, Output.OutputKey)
  with open(o_fpath, 'rb') as fp:
    S3.PutObject(session=Config.Session, bucket=Config.S3_OutputBucket, key=o_key, content=fp, type_=o_type)
  Logger.debug("Finished Upload of {0} to S3".format(Output.OutputKey))
  # Delete the temporary output file
  os.remove(o_fpath)


@Job
def ResizeImage(*, SourceKey, OutputKeyPrefix, Outputs, Config, Logger):
  Logger.debug("ResizeImage job for {0} started".format(SourceKey))
  # Download the required file and save it to a temp location
  FilePath = DownloadImageFromS3(Config, SourceKey)
  # Loop over required outputs to create them
  for o_ in Outputs:
    o = Output(*o_)
    cmd = (
      BIN_CONVERT,
      FilePath,
      '-resize', '{0}x{1}'.format(str(o.Width), str(o.Height)),
      os.path.join('/tmp', '{0}{1}'.format(OutputKeyPrefix.replace('/', '--'), o.OutputKey)),
      )
    # Now we can actually run the command
    ProcessImage(Output=o, Command=cmd, SourceKey=SourceKey, OutputKeyPrefix=OutputKeyPrefix, JobName='ResizeImage', Config=Config, Logger=Logger)
  # We're done with the temp file, delete it
  os.remove(FilePath)


@Job
def NormalizeImage(*, SourceKey, OutputKeyPrefix, Outputs, Config, Logger):
  Logger.debug("NormalizeImage job for {0} started".format(SourceKey))
  # Download the required file and save it to a temp location
  FilePath = DownloadImageFromS3(Config, SourceKey)
  # Loop over required outputs to create them
  for o_ in Outputs:
    o = Output(*o_)
    cmd = (
      BIN_CONVERT,
      FilePath,
      '-resize', '{0}x{1}^'.format(str(o.Width), str(o.Height)),
      '-gravity', 'Center',
      '-extent', '{0}x{1}'.format(str(o.Width), str(o.Height)),
      os.path.join('/tmp', '{0}{1}'.format(OutputKeyPrefix.replace('/', '--'), o.OutputKey)),
      )
    # Now we can actually run the command
    ProcessImage(Output=o, Command=cmd, SourceKey=SourceKey, OutputKeyPrefix=OutputKeyPrefix, JobName='NormalizeImage', Config=Config, Logger=Logger)
  # We're done with the temp file, delete it
  os.remove(FilePath)
