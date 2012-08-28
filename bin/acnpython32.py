# vim:encoding=utf-8:ts=2:sw=2:expandtab

# WARNING: these may be used in scripts that import * from this script

import sys
import re
import os
import shutil
import pwd
from os.path import abspath, dirname, join, exists
from optparse import OptionParser
from subprocess import call, check_call, check_output, Popen, PIPE, STDOUT, CalledProcessError
import tempfile

###############################################################################
# Setup environment

class Config:
  class Nginx:
    RepoRPM = 'http://nginx.org/packages/rhel/6/noarch/RPMS/nginx-release-rhel-6-0.el6.ngx.noarch.rpm'
    SERVER_DOCUMENT_ROOT = '/home/deploy/ServerDocumentRoot'
    SERVER_ERROR_LOG = '/home/deploy/Log/nginx/error.log'




#==============================================================================
# Add THIS acn-linux's python31 directory to the near-beginning of sys.path

Path = dirname(abspath(sys.path[0]))
PythonPath = join(Path, 'python32')

try:
  sys.path.remove(PythonPath)
except ValueError:
  pass

sys.path.insert(1, PythonPath)





###############################################################################
def Die(m, n=1):
  sys.stderr.write(str(m) + "\n")
  sys.exit(n)

###############################################################################
def HR():
  print()
  print("=" * 80)
  print()


###############################################################################
def GetInput_YesNo(Prompt, *, Default=''):
  Prompt = Prompt.replace('(DEF)', ('('+str(Default)+')' if Default else ''))
  while True:
    text = input(Prompt).strip()

    if text == '':
      text = Default
    
    if text in ('y', 'yes', 'Y', 'YES', 'Yes'):
      return True
    elif text in ('n', 'no', 'N', 'NO', 'No'):
      return False
    else:
      print("Invalid Input. Must be either 'yes' or 'no'.")


###############################################################################
def GetInput_Regex(Prompt, *, Regex, Trim=True, Default=''):
  Prompt = Prompt.replace('(DEF)', ('('+str(Default)+')' if Default else ''))
  while True:
    text = input(Prompt)

    if Trim:
      text = text.strip()

    if text == '':
      text = Default
    
    # validation
    if re.match(Regex, text):
      return text
    else:
      print("Invalid Input. Must match /{0}/.".format(Regex))

###############################################################################
def GetInput_FilePath(Prompt, *, Regex='^(/[a-zA-Z0-9_.-]+)+$', DirectoryMustExist=True, Trim=True, Default=''):
  Prompt = Prompt.replace('(DEF)', ('('+str(Default)+')' if Default else ''))
  while True:
    text = input(Prompt)

    if Trim:
      text = text.strip()

    if text == '':
      text = Default
    
    # validation
    if not re.match(Regex, text):
      print("Invalid Input. Must match /{0}/.".format(Regex))
      continue

    if DirectoryMustExist:
      if not exists(dirname(text)):
        print("Invalid Input.  Directory '{0}' must exist.".format(dirname(text)))
        continue

    return text

###############################################################################
def GetInput_IPv4(Prompt, *, Regex='^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$', Trim=True, Default=''):
  Prompt = Prompt.replace('(DEF)', ('('+str(Default)+')' if Default else ''))
  while True:
    text = input(Prompt)

    if Trim:
      text = text.strip()

    if text == '':
      text = Default
    
    # validation
    if not re.match(Regex, text):
      print("Invalid Input. Must match /{0}/.".format(Regex))
      continue

    return text

###############################################################################
def GetInput(Prompt, *, Trim=True, Default=''):
  Prompt = Prompt.replace('(DEF)', ('('+str(Default)+')' if Default else ''))
  while True:
    text = input(Prompt)

    if Trim:
      text = text.strip()

    if text == '':
      text = Default
    
    return text

###############################################################################
def GetInput_Choices(Prompt, *, Choices, PrintChoices=True, Trim=True, Default=''):
  Prompt = Prompt.replace('(DEF)', ('('+str(Default)+')' if Default else ''))
  while True:
    if PrintChoices:
      print('Valid Choices:')
      for choice in Choices:
        print('* {0}'.format(choice))
      print()

    text = input(Prompt)

    if Trim:
      text = text.strip()

    if text == '':
      text = Default
    
    # validation
    if text in Choices:
      return text
    else:
      print("Invalid Input. Must match /{0}/.".format(Regexp))


###############################################################################
# Edit a file and return True if it was changed

def EditFile(FileName):
  sha1_a = check_output(('/usr/bin/sha1sum', FileName))
  call(('/usr/bin/vim', FileName))
  sha1_b = check_output(('/usr/bin/sha1sum', FileName))

  return (sha1_a != sha1_b)


###############################################################################
# Provide seed contents, edit it in a temp file, and return the contents of the file

def EditData(input):
  File = tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8')
  File.write(input)
  File.close()

  EditFile(File.name)

  output = open(File.name, 'r', encoding='utf-8').read()
  os.remove(File.name)

  return output

###############################################################################
# Write a file to disk with the 

def WriteFile(FileName, data):
  open(FileName, 'w', encoding='utf-8').write(data)
  
###############################################################################

def CopySystemFile(RelativePath):
  sp = join(Path, 'os', RelativePath)
  dp = join('/', RelativePath)

  if not exists(sp):
    raise Exception("Specified path does not exist: {0}".format(sp))

  shutil.copyfile(sp, dp)


###############################################################################

def ReadSystemFile(RelativePath):
  sp = join(Path, 'os', RelativePath)

  if not exists(sp):
    raise Exception("Specified path does not exist: {0}".format(sp))

  return open(sp, 'r', encoding='utf-8').read()

###############################################################################

def WriteSystemFile(RelativePath, Data):
  dp = join('/', RelativePath)
  open(dp, 'w', encoding='utf-8').write(Data)



###############################################################################
