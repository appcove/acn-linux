# vim:encoding=utf-8:ts=2:sw=2:expandtab
import os
import os.path
import mimetypes

from ..Base import S3
from ..DocumentConverter import DocumentConverter
from . import Job, S3BackedFile


class S3BackedDocument(S3BackedFile):

  def __init__(self, *, OutputKey, **kw):
    super().__init__(**kw)
    self.OutputKey = OutputKey

  def Run(self):
    FilePath = self.LocalFilePath
    # Save the input file
    self.Output['Outputs'].append({'Key': self.InputKey})
    OutputFilePath = self.GetLocalFilePathFromS3Key(Key=self.OutputKey, KeyPrefix=self.OutputKeyPrefix)
    self.Logger.debug("Will convert {0} to {1}".format(self.InputKey, self.OutputKey))
    # Use pyuno to speak to the headless openoffice server
    # NOTE: the envvarname is used if we are running in docker
    envvarname = os.environ.get('OO_HOST_VAR', 'OOSERVER_PORT_8100_TCP_ADDR')
    converter = DocumentConverter(host=os.environ.get(envvarname, 'localhost'))
    converter.convert(FilePath, OutputFilePath)
    self.Logger.debug("Done with conversion")
    # After conversion upload the file to S3
    o_key = os.path.join(self.OutputKeyPrefix, self.OutputKey)
    o_mime = mimetypes.guess_type(self.OutputKey)[0] or "application/octet-stream"
    with open(OutputFilePath, 'rb') as fp:
      S3.PutObject(
        session=self.Config.Session,
        bucket=self.Config.S3_OutputBucket,
        key=o_key,
        content=fp,
        type_=o_mime,
        )
    # Save output key
    self.Output['Outputs'].append({'Key': o_key})
    # Log a message
    self.Logger.debug("Finished Upload of {0} to S3".format(self.OutputKey))
    # Mark the new file for deletion
    self.MarkFilePathForCleanup(OutputFilePath)


@Job
def ConvertToPDF(*, InputKey, OutputKeyPrefix, Config, Logger):
  Logger.debug("ResizeImage job for {0} started".format(InputKey))
  # Prepare context in which we'll run
  ctxt = S3BackedDocument(
    InputKey=InputKey,
    OutputKeyPrefix=OutputKeyPrefix,
    Config=Config,
    Logger=Logger,
    OutputKey='output.pdf',
    )
  # Start the processing
  with ctxt as doc:
    doc.Run()
