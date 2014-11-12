# vim:encoding=utf-8:ts=2:sw=2:expandtab
from os.path import basename
from DocStruct.Base import ElasticTranscoder
from . import Job


@Job
def TranscodeVideo(*, InputKey, OutputKeyPrefix, OutputFormats, Config, Logger):
  Logger.debug("TranscodeVideo started for {0}".format(InputKey))
  # Convert formats to output types
  Outputs = []
  for o in OutputFormats:
    if o == 'webm':
      Outputs.append({'Key': 'webm.webm', 'PresetId': basename(Config.ElasticTranscoder_WebPresetArn)})
    elif o == 'mp4':
      Outputs.append({'Key': 'web.mp4', 'PresetId': basename(Config.ElasticTranscoder_WebmPresetArn)})
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
