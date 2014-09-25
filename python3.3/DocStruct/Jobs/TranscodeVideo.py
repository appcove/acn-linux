# vim:encoding=utf-8:ts=2:sw=2:expandtab
from DocStruct.Base import ElasticTranscoder


def Main(*, Session, PipelineId, InputKey, OutputKeyPrefix, Outputs):
    return ElasticTranscoder.StartTranscoding(Session, PipelineId, InputKey,
                                              output_key_prefix=OutputKeyPrefix,
                                              outputs=Outputs)

