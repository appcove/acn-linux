# vim:encoding=utf-8:ts=2:sw=2:expandtab
from os.path import basename
from DocStruct.Base import ElasticTranscoder


def Main(*, Session, InputKey, OutputKeyPrefix, OutputFormats, Config):
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
    return ElasticTranscoder.StartTranscoding(Session, PipelineId, InputKey,
                                              output_key_prefix=OutputKeyPrefix,
                                              outputs=Outputs)

