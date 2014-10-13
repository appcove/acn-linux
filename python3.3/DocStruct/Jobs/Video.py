# vim:encoding=utf-8:ts=2:sw=2:expandtab
from os.path import basename
from DocStruct.Base import ElasticTranscoder
from . import Job


@Job
def TranscodeVideo(*, Session, InputKey, OutputKeyPrefix, OutputFormats, Config, Logger=None):
    if Logger:
      Logger.debug("TranscodeVideo started for {0}".format(InputKey))
    # Convert formats to output types
    Outputs = []
    for o in OutputFormats:
      if o == 'webm':
        Outputs.append({'Key': 'webm.webm', 'PresetId': basename(Config["ElasticTranscoder"]["WebPresetArn"])})
      elif o == 'mp4':
        Outputs.append({'Key': 'web.mp4', 'PresetId': basename(Config["ElasticTranscoder"]["WebmPresetArn"])})
    # Set Pipeline ID
    PipelineId = basename(Config["ElasticTranscoder"]["PipelineArn"])
    # Trigger the transcoding
    ret = ElasticTranscoder.StartTranscoding(
      Session,
      PipelineId,
      InputKey,
      output_key_prefix=OutputKeyPrefix,
      outputs=Outputs
      )
    if Logger:
      Logger.debug("ElasticTranscoder job created: {0}".format(ret["Job"]["Arn"]))
    # Now we are ready to return
    return ret
