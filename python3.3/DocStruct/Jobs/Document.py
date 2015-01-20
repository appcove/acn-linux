# vim:encoding=utf-8:ts=2:sw=2:expandtab
import re
import os
import os.path
import glob
import mimetypes
import subprocess

from ..Base import S3
from . import Job, S3BackedFile


GS_BIN = "/usr/bin/gs"
CONVERTER_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../DocumentConverter.py'))


class S3BackedDocument(S3BackedFile):

  def __init__(self, *, OutputKey, **kw):
    super().__init__(**kw)
    self.OutputKey = OutputKey

  def GenerateImagesFromPDF(self, *, PDFPath):
    # Generate images from pages of PDF and save images to S3
    PageNamePrefix = PDFPath.replace('.pdf', '')
    PageNameFormat = PageNamePrefix + '-%d.jpg'
    # Call ghostscript to produce the images
    try:
      out = subprocess.check_output((GS_BIN, '-sDEVICE=jpeg', '-dNOPAUSE', '-r72', '-o', PageNameFormat, PDFPath), stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as exc:
      raise Exception("ERROR: {0}".format(exc.output))

    # search for all files with the relevant prefix and upload them to S3
    images = glob.glob(PageNamePrefix + '-*.jpg')
    regex = re.compile(PageNamePrefix + '-(\d+)\.jpg')
    images.sort(key=lambda im: int(regex.sub('\g<1>', im)))
    thumbs = []

    for im in images:
      with open(im, 'rb') as fp:
        key = "{0}{1}".format(self.OutputKeyPrefix, im.replace(PageNamePrefix, 'thumb'))
        S3.PutObject(
          session=self.Config.Session,
          bucket=self.Config.S3_OutputBucket,
          key=key,
          content=fp,
          type_='image/jpeg',
          )

        # Log message saying that images has uploaded
        self.Logger.debug("Finished Upload of {0} to S3".format(key))

        # Inspect the path so that we get image props
        props = self.InspectImage(im)
        props['Key'] = key
        thumbs.append(props)

        # Make sure the file gets deleted after we exit
        self.MarkFilePathForCleanup(im)

    # Return all the keys that have been uploaded to S3
    return thumbs

  def ConvertToPDF(self):
    FilePath = self.LocalFilePath
    # Save the input file
    self.Output['Outputs'].append({'Key': self.InputKey})
    OutputFilePath = self.GetLocalFilePathFromS3Key(Key=self.OutputKey, KeyPrefix=self.OutputKeyPrefix)
    self.Logger.debug("Will convert {0} to {1}".format(self.InputKey, self.OutputKey))

    # Use pyuno to speak to the headless openoffice server
    try:
      out = subprocess.check_output(('python2', CONVERTER_PATH, FilePath, OutputFilePath), stderr=subprocess.STDOUT)
      self.Logger.debug("Done with conversion")
    except subprocess.CalledProcessError as exc:
      raise Exception("ERROR: {0}".format(exc.output))

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
    self.Output['Outputs'].append({'Key': o_key, 'Type': 'PDF'})
    # Log a message
    self.Logger.debug("Finished Upload of {0} to S3".format(self.OutputKey))

    # Generate images from all pages of PDF
    o_thumbs = self.GenerateImagesFromPDF(PDFPath=OutputFilePath)
    self.Output['Outputs'].extend(o_thumbs)
    # Add number of thumbnails to Input
    self.Output['Input'] = {'NumPages': len(o_thumbs)}

    # Mark the new file for deletion
    self.MarkFilePathForCleanup(OutputFilePath)

  def Run(self):
    self.ConvertToPDF()


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
