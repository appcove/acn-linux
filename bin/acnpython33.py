# vim:encoding=utf-8:ts=2:sw=2:expandtab

# WARNING: these may be used in scripts that import * from this script

import sys
import re
import os
import shutil
import pwd
from os.path import abspath, dirname, join, exists, isdir
from optparse import OptionParser
from subprocess import call, check_call, check_output, Popen, PIPE, STDOUT, CalledProcessError
import tempfile

###############################################################################
# Setup environment

class Config:
  class OS:
    Name = None
  class Nginx:
    RepoRPM = 'http://nginx.org/packages/rhel/6/noarch/RPMS/nginx-release-rhel-6-0.el6.ngx.noarch.rpm'
    SERVER_DOCUMENT_ROOT = '/home/deploy/ServerDocumentRoot'
    SERVER_ERROR_LOG = '/home/deploy/Log/nginx/error.log'
    SERVER_ACCESS_LOG = '/home/deploy/Log/nginx/access.log'
  class Postgres:
    RepoRPM_Centos = 'http://yum.postgresql.org/9.2/redhat/rhel-6-x86_64/pgdg-centos92-9.2-6.noarch.rpm'
    RepoRPM_RHEL = 'http://yum.postgresql.org/9.2/redhat/rhel-6-x86_64/pgdg-redhat92-9.2-7.noarch.rpm'
    ServerPackage = 'postgresql92-server'
    ClientPackage = 'postgresql92'
    ContribPackage = 'postgresql92-contrib'
    ServiceName = 'postgresql-9.2'
    InstallDir = '/var/lib/pgsql/9.2'
  class MySQL:
    ServerPackage = 'mysql-server'
    ClientPackage = 'mysql'
    ServiceName = 'mysqld'
  class Apache:
    CustomLog = '/home/deploy/Log/apache/access.log'
    ErrorLog = '/home/deploy/Log/apache/error.log'
    DocumentRoot = '/home/deploy/ServerDocumentRoot'
  class PHP:
    PackageList = (
      'php54',
      'php54-bcmath',
      'php54-cli',
      'php54-common',
      'php54-gd',
      'php54-imap',
      'php54-mysql',
      'php54-pdo',
      'php54-xml',
      )
  class mod_wsgi:
    PackageList = ('python33-mod_wsgi',)
  class PythonPostgres:
    Package = 'python33-postgresql'
  class PythonRedis:
    PackageList = ('python33-redis', 'python33-hiredis')


if exists('/etc/oracle-release'):
  Config.OS.Name = 'oracle'
elif exists('/etc/centos-release'):
  Config.OS.Name = 'centos'
elif exists('/etc/redhat-release'):
  Config.OS.Name = 'redhat'
else:
  raise Exception("Cannot determine Config.OS.Name")


#==============================================================================
# Add THIS acn-linux's python32 directory to the near-beginning of sys.path

Path = dirname(abspath(sys.path[0]))
PythonPath = join(Path, 'python3.2')

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

    # If Default is None and nothing was entered, then return None
    if text == None:
      return None
    
    if text in ('y', 'yes', 'Y', 'YES', 'Yes'):
      return True
    elif text in ('n', 'no', 'N', 'NO', 'No'):
      return False
    else:
      print("Invalid Input. Must be either 'yes' or 'no'.")


###############################################################################
def GetInput_Int(Prompt, *, MinValue=None, MaxValue=None, Trim=True, Default=''):
  Prompt = Prompt.replace('(DEF)', ('('+str(Default)+')' if Default else ''))
  while True:
    text = input(Prompt)

    if Trim:
      text = text.strip()

    if text == '':
      text = Default

    # If Default is None and nothing was entered, then return None
    if text == None:
      return None
    
    try:
      value = int(text)
    except ValueError:
      print("Invalid Input. Must be an integer.")
      continue

    if MinValue != None and value < MinValue:
      print("Invalid Input. Must be at least {0}.".format(MinValue))
      continue

    if MaxValue != None and value > MaxValue:
      print("Invalid Input. Must be no more than {0}.".format(MaxValue))
      continue

    return value


###############################################################################
def GetInput_Regex(Prompt, *, Regex, Trim=True, Default=''):
  Prompt = Prompt.replace('(DEF)', ('('+str(Default)+')' if Default else ''))
  while True:
    text = input(Prompt)

    if Trim:
      text = text.strip()

    if text == '':
      text = Default

    # If Default is None and nothing was entered, then return None
    if text == None:
      return None
    
    # validation
    if re.match(Regex, text):
      return text
    else:
      print("Invalid Input. Must match /{0}/.".format(Regex))

###############################################################################
def GetInput_FilePath(Prompt, *, Regex='^(/[a-zA-Z0-9_.-]+)+$', ParentDirectoryMustExist=True, FileMustExist=False, Trim=True, Default=''):
  Prompt = Prompt.replace('(DEF)', ('('+str(Default)+')' if Default else ''))
  while True:
    text = input(Prompt)

    if Trim:
      text = text.strip()

    if text == '':
      text = Default

    # If Default is None and nothing was entered, then return None
    if text == None:
      return None
    
    # validation
    if not re.match(Regex, text):
      print("Invalid Input. Must match /{0}/.".format(Regex))
      continue

    if ParentDirectoryMustExist:
      if not exists(dirname(text)):
        print("Invalid Input.  Directory '{0}' must exist.".format(dirname(text)))
        continue
    
    if FileMustExist:
      if not exists(text):
        print("Invalid Input.  File '{0}' must exist.".format(text))
        continue


    return text

###############################################################################
def GetInput_DirectoryPath(Prompt, *, Regex='^(/[a-zA-Z0-9_.-]+)+$', DirectoryMustExist=False, StripTrailingSlash=True, Trim=True, Default=''):
  Prompt = Prompt.replace('(DEF)', ('('+str(Default)+')' if Default else ''))
  while True:
    text = input(Prompt)

    if Trim:
      text = text.strip()

    if StripTrailingSlash:
      text = text.rstrip('/')

    if text == '':
      text = Default

    # If Default is None and nothing was entered, then return None
    if text == None:
      return None
    
    # validation
    if not re.match(Regex, text):
      print("Invalid Input. Must match /{0}/.".format(Regex))
      continue
    
    if DirectoryMustExist:
      if not exists(text) or not isdir(text):
        print("Invalid Input.  Directory '{0}' must exist and be a directory.".format(text))
        continue

    return text

###############################################################################
def GetInput_IPv4(Prompt, *, WithRange=False, Trim=True, Default=''):
  if WithRange:
    Regex='^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\/[0-9]{1,2}$'
  else:
    Regex='^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$'

  Prompt = Prompt.replace('(DEF)', ('('+str(Default)+')' if Default else ''))

  while True:
    text = input(Prompt)

    if Trim:
      text = text.strip()

    if text == '':
      text = Default

    # If Default is None and nothing was entered, then return None
    if text == None:
      return None
    
    # validation
    if not re.match(Regex, text):
      print("Invalid Input. Must match /{0}/.".format(Regex))
      continue

    return text

###############################################################################
def GetInput(Prompt, *, Trim=True, Default='', Required=False):
  Prompt = Prompt.replace('(DEF)', ('('+str(Default)+')' if Default else ''))
  while True:
    text = input(Prompt)

    if Trim:
      text = text.strip()

    if text == '':
      text = Default

    if not text and Required:
      print("Invalid Input.  Must not be empty.")
      continue

    # If Default is None and nothing was entered, then return None
    if text == None:
      return None
    
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

    # If Default is None and nothing was entered, then return None
    if text == None:
      return None
    
    # validation
    if text in Choices:
      return text
    else:
      print("Invalid Input. Must be one of [{0}].".format(str.join(', ', Choices)))
      print()


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
def SystemFilePath(RelativePath):
  return join(Path, 'os-template', RelativePath)

###############################################################################

def CopySystemFile(RelativePath):
  
  # Make any absolute paths relative
  if RelativePath.startswith('/'):
    RelativePath = RelativePath[1:]
  
  sp = join(Path, 'os-template', RelativePath)
  dp = join('/', RelativePath)

  if not exists(sp):
    raise Exception("Specified path does not exist: {0}".format(sp))

  shutil.copyfile(sp, dp)

###############################################################################

def ReadSystemFile(RelativePath):
  sp = join(Path, 'os-template', RelativePath)

  if not exists(sp):
    raise Exception("Specified path does not exist: {0}".format(sp))

  return open(sp, 'r', encoding='utf-8').read()

###############################################################################

def WriteSystemFile(RelativePath, Data):
  
  # Make any absolute paths relative
  if RelativePath.startswith('/'):
    RelativePath = RelativePath[1:]

  dp = join('/', RelativePath)
  open(dp, 'w', encoding='utf-8').write(Data)



###############################################################################
