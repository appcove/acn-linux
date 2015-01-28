# vim:encoding=utf-8:ts=2:sw=2:expandtab
import json


##################################################
class JobSpecification(object):

  def __init__(self, *, InputKey, OutputKeyPrefix, Name=""):
    if Name:
      self.Name = Name
    self.InputKey = InputKey
    self.OutputKeyPrefix = OutputKeyPrefix

  def ToJSON(self):
    # Validate that the basic fields are there
    if not (self.InputKey or self.OutputKeyPrefix):
      raise Exception("InputKey and OutputKeyPrefix are required fields.")
    # Prepare params to configure job
    Params = {
      "InputKey": self.InputKey,
      "OutputKeyPrefix": self.OutputKeyPrefix,
      }
    # Update with passed in "ExtraParams"
    if isinstance(self.ExtraParams, dict):
      Params.update(self.ExtraParams)
    # Prepare the JSON to return
    return json.dumps({
      "Type": "Job",
      "Job": self.Name,
      "Params": Params
      })


##################################################
class TranscodeVideoJob(JobSpecification):

  Name = "TranscodeVideo"

  @property
  def ExtraParams(self):
    return {
      "OutputFormats": ('webm', 'mp4')
      }


##################################################
class ConvertToPDFJob(JobSpecification):

  Name = "ConvertToPDF"

  @property
  def ExtraParams(self):
    return {
      "OutputKey": "output.pdf"
      }


##################################################
class ResizeImageJob(JobSpecification):

  Name = "ResizeImage"

  @property
  def ExtraParams(self):
    return {
      "PreferredOutputs": ((200, 200, '200x200.jpg'), (300, 300, '300x300.jpg'),)
      }


##################################################
class NormalizeImageJob(JobSpecification):

  Name = "NormalizeImage"

  @property
  def ExtraParams(self):
    return {
      "PreferredOutputs": ((200, 200, '200x200-nomarlized.jpg'), (300, 300, '300x300-normalized.jpg'),)
      }
