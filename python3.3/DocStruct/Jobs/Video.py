# vim:encoding=utf-8:ts=2:sw=2:expandtab
from os.path import basename
from DocStruct.Base import ElasticTranscoder
from . import Job


def TranscodeVideoBase(*, InputKey, OutputKeyPrefix, OutputFormats, Config, Logger):
  Logger.debug("TranscodeVideo started for {0}".format(InputKey))
  # Convert formats to output types
  Outputs = []
  for o in OutputFormats:
    if o == 'webm':
      Outputs.append({'Key': 'video.webm', 'PresetId': basename(Config.ElasticTranscoder_WebmPresetArn)})
    elif o == 'mp4':
      Outputs.append({'Key': 'video.mp4', 'PresetId': basename(Config.ElasticTranscoder_WebPresetArn)})
  # Set Pipeline ID
  PipelineId = basename(Config.ElasticTranscoder_PipelineArn)
  # Trigger the transcoding
  ret = ElasticTranscoder.StartTranscoding(
    session=Config.Session,
    pipeline_id=PipelineId,
    video_path=InputKey,
    output_key_prefix=OutputKeyPrefix,
    outputs=Outputs
    )
  Logger.debug("ElasticTranscoder job created: {0}".format(ret["Job"]["Arn"]))
  # Now we are ready to return
  return ret


@Job
def TranscodeVideo(*, InputKey, OutputKeyPrefix, Config, Logger):
  return TranscodeVideoBase(
    InputKey=InputKey,
    OutputKeyPrefix=OutputKeyPrefix,
    OutputFormats=('webm', 'mp4'),
    Config=Config,
    Logger=Logger,
    )

