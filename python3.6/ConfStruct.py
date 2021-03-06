# vim:fileencoding=utf-8:ts=2:sw=2:expandtab

from decimal import Decimal
import re
import inspect
from os.path import join, isfile, isdir, dirname
from collections import OrderedDict

###############################################################################
class _Undefined:
  __slots__ = ()
  def __repr__(cls):
    return "_Undefined"
  def __str__(cls):
    return "_Undefined"
  def __bool__(cls):
    return False
_Undefined = _Undefined()

###############################################################################

# Match a yield statment (with optional comment) at the beginning of the line)
YieldMatch = re.compile(r'^yield\s*(#.*)?$').match

def ParseAndCompileFile(path, minchunks, maxchunks):
  '''
  Parses an input file into chunks separated by top level `yield` statements
  Returns a list of compiled code or None (for empty chunks)

  '''
  chunks = [[] for n in range(maxchunks)]
  curpos = 0

  with open(path, 'r') as f:
    for line in f:
      
      if YieldMatch(line):
        curpos += 1
        line = '#' + line

        if curpos == maxchunks:
          raise SyntaxError('In {0}, you must have no more than {1} sections (with {2} yield statements)'.format(path, maxchunks, maxchunks-1))


      for chunk in chunks:
        chunk.append(line if chunk is chunks[curpos] else "\n")

    else:
      if curpos+1 < minchunks:
        raise SyntaxError('In {0}, you must have at least {1} sections (with {2} yield statements)'.format(path, minchunks, minchunks-1))

  compiled_chunks = []
  for chunk in chunks:
    if len(chunk) == 0:
      compiled_chunks.append(None)
    else:
      compiled_chunks.append(compile(str.join('', chunk), path, 'exec'))

  return compiled_chunks


###############################################################################

class BaseValue():
  Description = "<BaseValue>"
  Default = None
 
  def __new__(cls):
    raise NotImplementedError('BaseValue is abstract')
  
  @staticmethod
  def Describe(cls, path):
    print('\033[93m{0}:\033[0m {1}'.format('.'.join(path), cls.Description))

  @staticmethod
  def Validate(cls, path, value, errors):
    raise NotImplementedError('BaseValue is abstract')


class Scalar(BaseValue):
  pass

class Vector(BaseValue):
  pass


class Mapping(Vector, OrderedDict):
  '''
  '''
  Description = 'Mapping'
 
  def __repr__(self):
    return "<{0}>".format(type(self).__name__)

  def __new__(cls):
    self = OrderedDict.__new__(cls)
    
    if not hasattr(cls, 'Key'):
      raise TypeError("Mapping classes must define an inner class called 'Key'")

    if not hasattr(cls, 'Value'):
      raise TypeError("Mapping classes must define an inner class called 'Value'")
    
    if not (inspect.isclass(cls.Key) and issubclass(cls.Key, Scalar)):
      raise TypeError("Inner class 'Key' must be a subclass of Scalar")

    if not (inspect.isclass(cls.Value) and issubclass(cls.Value, BaseValue)):
      raise TypeError("Inner class 'Value' must be a subclass of BaseValue")

    return self

  
  @staticmethod
  def Describe(cls, path):
    
    print('\033[93m{0}:\033[0m {1}\033[93m with key being\033[0m {2}'.format('.'.join(path), cls.Description, cls.Key.Description))
    
    mpath = path[0:-1] + (path[-1] + '[KEY]',)
    cls.Value.Describe(cls.Value, mpath)
    
    

  @staticmethod
  def Validate(cls, path, self, errors):
    if not isinstance(self, cls):
      raise TypeError("value must be of type {0}, not {1}".format(type(cls), type(self)))


    for key in self:
      mpath = path[0:-1] + (path[-1] + '[{0}]'.format(key),)
      value = self[key]
      self[key] = cls.Value.Validate(cls.Value, mpath, value, errors)
      
    # Because this is and object reference, just return current instance
    return self
  
class Sequence(Vector, list):
  '''
  '''
  Description = 'Sequence'
  MinLength = 0
 
  #def __repr__(self):
  #  return "<{0}>".format(type(self).__name__)

  def __new__(cls):
    self = list.__new__(cls)
    
    if not hasattr(cls, 'Value'):
      raise TypeError("Sequence classes must define an inner class called 'Value'")
    
    if not (inspect.isclass(cls.Value) and issubclass(cls.Value, BaseValue)):
      raise TypeError("Inner class 'Value' must be a subclass of BaseValue")

    return self

  
  @staticmethod
  def Describe(cls, path):
    
    print('\033[93m{0}:\033[0m {1}\033[93m with value being\033[0m {2}'.format('.'.join(path), cls.Description, cls.Value.Description))
    
    mpath = path[0:-1] + (path[-1] + '[INDEX]',)
    cls.Value.Describe(cls.Value, mpath)
    
    

  @staticmethod
  def Validate(cls, path, self, errors):
    if not isinstance(self, cls):
      raise TypeError("value must be of type {0}, not {1}".format(type(cls), type(self)))

    if len(self) < self.MinLength:
      raise ValueError('MinLength must be {0} instead of {1}'.format(self.MinLength, len(self)))

    for key in range(len(self)):
      mpath = path[0:-1] + (path[-1] + '[{0}]'.format(key),)
      value = self[key]
      self[key] = cls.Value.Validate(cls.Value, mpath, value, errors)
      
    # Because this is and object reference, just return current instance
    return self



class Object(Vector):
  '''
  '''
  Description = 'Object'
 
  def __repr__(self):
    return "<{0}>".format(type(self).__name__)

  def __new__(cls):
    self = object.__new__(cls)
    
    #TODO: must look at __mro__ to find any classes, then use getattr on the class
    # to get an instance of them.

    classes = dir(cls)

    # for each item in the class dict...
    for (name, cls2, path2) in cls.iter1(cls, ('',)):
      self.__dict__[name] = cls2()
    
    return self

  @staticmethod
  def iter1(cls, path):
    #TODO: must look at __mro__ to find any classes, then use getattr on the class
    # to get an instance of them.

    classes = dir(cls)

    # for each item in the class dict...
    for name in classes:
      cls2 = getattr(cls, name)
      
      # that is a subclass of BaseValue...
      if inspect.isclass(cls2) and issubclass(cls2, BaseValue):

        # Calculate next path level
        path2 = path + (name,)

        yield (name, cls2, path2)

  
  @staticmethod
  def iter2(cls, path, value):
    
    for name, cls2, path2 in cls.iter1(cls, path):
        # Get current value from instance
        value2 = value.__dict__.get(name, _Undefined)
        yield (name, cls2, path2, value2)
  
  @staticmethod
  def Describe(cls, path):
    
    if len(path):  # Don't print root element
      print('\033[93m{0}:\033[0m {1}'.format('.'.join(path), cls.Description))

    for name, cls2, path2 in cls.iter1(cls, path):
      cls2.Describe(cls2, path2)
    
    

  @staticmethod
  def Validate(cls, path, value, errors):
    if not isinstance(value, cls):
      raise TypeError("value must be of type {0}, not {1}".format(type(cls), type(value)))

    for name, cls2, path2, value2 in cls.iter2(cls, path, value):
      # Replace value with the validated version 
      try:
        setattr(value, name, cls2.Validate(cls2, path2, value2, errors))
        print('\033[92m✔ {0}:\033[0m {1} '.format('.'.join(path2), repr(value2)))
      except Exception as e:
        errors.append(('.'.join(path2), cls2.Description))
        print('\033[91m✘ {0}:\033[0m {1}\n \033[93m➜ {2}\033[0m'.format('.'.join(path2), repr(value2), str(e)))
        
    # Because this is and object reference, just return current instance
    return value

  def update(self, data):
    for k,v in data.items():
      setattr(self, k, v)

  

class Integer(Scalar):
  Description = 'Integer'
  Minvalue = None
  Maxvalue = None
  Required = True
  AllowNone = False
 
  def __new__(cls):
    return cls.Default

  @staticmethod
  def Validate(cls, path, value, errors):

    # Pass None if allowed
    if value is None: 
      if cls.AllowNone:
        return None
      else:
        raise TypeError("Value required.")
    
    # Handle string input
    if isinstance(value, str):
      value = value.strip()

      if value == '':
        if cls.Required:
          raise ValueError('Integer value is required')

      else:
        try:
          value = int(re.sub('[,$+]', '', value))
        except ValueError:
          raise
  
    # Pass integer instance
    elif isinstance(value, int):
      pass

    # convert Float, Decimal
    elif isinstance(value, (float, Decimal)):
      value = int(value)
    
    # invalid type
    else:
      raise ValueError("Expected instance of (str, int, float, decimal.Decimal) instead of " + repr(type(value)))

    #
    # At this point we have a `int` instance
    #

    # Minvalue ?
    if cls.Minvalue is not None and cls.Minvalue > value:
      raise ValueError("value must be at least {0}.".format(cls.Minvalue))

    # Maxvalue ?
    if cls.Maxvalue is not None and value > cls.Maxvalue:
      raise ValueError("value must not exceed {0}.".format(cls.Maxvalue))
    
    # At this point return a valid `int` instance
    return value

  
class Boolean(Scalar):
  Description = 'Boolean'
  AllowNone = False
 
  def __new__(cls):
    return cls.Default

  @staticmethod
  def Validate(cls, path, value, errors):

    # Pass None if allowed
    if value is None: 
      if cls.AllowNone:
        return None
      else:
        raise TypeError("Value required.")
   
    return bool(value)
  

     
class String(Scalar):
  Description = 'String'
  Strip = True
  Truncate = False
  MinLength = None 
  MaxLength = None 
  Required = True 
  RegexMatch = None  #2-tuple of regex and error message
  AllowNone = False
  
  def __new__(cls):
    return cls.Default
  
  @staticmethod
  def Validate(cls, path, value, errors):
    
    # Pass None if allowed
    if value is None: 
      if cls.AllowNone:
        return None
      else:
        raise TypeError("Value required.")
        
    if not isinstance(value, str):
      raise TypeError("value must be an instance of `str`, not `{0}`".format(repr(type(value))))
    
    #
    # at this point we have a `str` instance
    #
      
    # Strip?
    if cls.Strip:
      value = value.strip()

    # Check for Required or valid Default
    if value == '':
      if cls.Required:
        raise ValueError('value is required.')
    
    # Truncate?
    if cls.Truncate and len(value) > cls.MaxLength:
      value = value[0:cls.MaxLength]


    # MinLength?
    if cls.MinLength and len(value) < cls.MinLength:
      raise ValueError('value must be at least {0} characters'.format(cls.MinLength))
    
    # MaxLength?
    if cls.MaxLength and len(value) > cls.MaxLength:
      raise ValueError('value Must be limited to {0} characters'.format(cls.MaxLength))

    # RegexMatch?
    if cls.RegexMatch and not re.search(cls.RegexMatch[0], value):
      raise ValueError(cls.RegexMatch[1])
    
    # If we are here, returning a valid `str` instance
    return value


class File(String):
  MustExist = True
  DirectoryMustExist = False
  @staticmethod
  def Validate(cls, path, value, errors):
    value = String.Validate(cls, path, value, errors)
    if cls.MustExist and not isfile(value):
      raise ValueError("File '{0}' does not exist".format(value))
    if cls.DirectoryMustExist and not isdir(dirname(value)):
      raise ValueError("Directory '{0}' does not exist".format(dirname(value)))
    return value

class LogFile(File):
  MustExist = False
  DirectoryMustExist = True

class Directory(String):
  Exists = True
  @staticmethod
  def Validate(cls, path, value, errors):
    value = String.Validate(cls, path, value, errors)
    if cls.MustExist and not isdir(value):
      raise ValueError("Directory '{0}' does not exist".format(value))
    return value

class Domain(Object):
  class Name(String):
    RegexMatch = r'^[0-9a-z_-]+(\.[0-9a-z_-]+)+$'
  @property 
  def HTTP(self):
    return 'http://' + self.Name
  @property 
  def HTTPS(self):
    return 'https://' + self.Name
  def __repr__(self):
    return repr({
      'Name': self.Name, 
      'HTTP': self.HTTP, 
      'HTTPS': self.HTTPS
      })
    
  

class FileStruct(Object):
  class Path(Directory):
    Description = 'Absolute path to FileStruct'
    MustExist = True
  def __repr__(self):
    return repr({
      'Path': self.Path, 
      })


class ProjectIdentifier(String):
  RegexMatch = r'^[a-zA-Z0-9_]{1,32}', 'value must only contain [a-zA-Z0-9_]'
  Description = 'Unique project identifier'

class IPAddress(String):
  Description = "An IPV4 address in the form of 192.168.100.200"
  Strip = True
  RegexMatch = r'^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$', 'Invalid IP address'

class Port(Integer):
  Description = "An integer port number between 8000 and 65535"
  Minvalue = 1
  Maxvalue = 65535

_port = Port


class UserPass(Object):
  class Username(String):
    pass
  class Password(String):
    pass

class Postgres(Object):
  class Host(String):
    Default='localhost'
  class Port(Port):
    Default=5432
  class Username(String):
    pass
  class Password(String):
    pass
  class Database(String):
    pass
  def __repr__(self):
    return repr({
      'host': self.Host, 
      'port': self.Port,
      'user': self.Username,
      'password': self.Password,
      'database': self.Database,
      })

class Mailgun(Object):
  class URL(String):
    pass
  class Key(String):
    pass
  def __repr__(self):
    return repr({
      'URL': self.URL, 
      'Key': self.Key,
      'Auth': ('api', self.Key),
      })

class Stripe(Object):
  class PublicKey(String):
    pass
  class SecretKey(String):
    pass
  def __repr__(self):
    return repr({
      'PublicKey': self.PublicKey,
      'SecretKey': self.SecretKey,
      })

class Twilio(Object):
  class URL(String):
    pass
  class AccountSID(String):
    pass
  class AuthToken(String):
    pass
  def __repr__(self):
    return repr({
      'URL': self.URL,
      'AccountSID': self.AccountSID, 
      'AuthToken': self.AuthToken,
      'Auth': (self.AccountSID, self.AuthToken),
      })

class Braintree(Object):
  class Environment(String):
    Description = '"Sandbox" for development, "Production" for production'
    def Validate(cls, path, value, errors):
      if value not in ('Sandbox', 'Production'):
        raise ValueError('Invalid value')
      return value
  class MerchantId(String):
    Description = 'See Braintree Docs'
  class PublicKey(String):
    Description = 'See Braintree Docs'
  class PrivateKey(String):
    Description = 'See Braintree Docs'
  class CSEKey(String):
    Description = 'See Braintree Docs'
  def __repr__(self):
    return repr({
      'Environment': self.Environment, 
      'MerchantId': self.MerchantId,
      'PublicKey': self.PublicKey,
      'PrivateKey': self.PrivateKey,
      'CSEKey': self.CSEKey,
      })


class Redis(Object):
  class Host(String):
    Default='localhost'
  class Port(Port):
    Default=6379
  class DB(Integer):
    Default=0
  def __repr__(self):
    return repr({
      'host': self.Host, 
      'port': self.Port,
      'db': self.DB,
      })

# Typical usage would be `class FooSite(Site, SSLSite, SiteProxy)`


class SiteProxy(Object):
  class ProxyIP(IPAddress):
    Default='127.0.0.1'
    Description = 'IP address that backend server (e.g. apache) is listening on'
  class ProxyPort(Port):
    Description = 'Port that backend server (e.g. apache) is listening on'

class Site(Object):
  class ServerName(String):
    pass
  class IP(IPAddress):
    pass
  class Port(Port):
    Default=80
  class URL(String):
    pass

class SSLSite(Object):
  class SSLServerName(String):
    pass
  class SSLIP(IPAddress):
    pass
  class SSLPort(Port):
    Default=443
  class SSLURL(String):
    pass
  class SSLCrt(File):
    Description = 'Path to SSL Crt file for this site'
    MustExist = False  #we lack permissions most likel 
  class SSLKey(File):
    Description = 'Path to SSL Key file for this site'
    MustExist = False  #we lack permissions most likely

class WSGIProcessGroup(Object):
  class Threads(Integer):
    Description = 'Number of WSGI Daemon Process threads to launch per process'
    Default = 2
  class Processes(Integer):
    Description = 'Number of WSGI Daemon Processes to launch'
    Default = 2 


class Pusher(Object):
  Description = 'Information for connecting to pusher.com'
  class host(String):
    Description = 'pusher.com API Host'
    Default = 'api.pusherapp.com'
  class port(Port):
    Description = 'pusher.com API Port'
    Default = 80
  class app_id(String):
    Description = 'app_id for pusher.com application'
  class key(String):
    Description = 'key for pusher.com application'
  class secret(String):
    Description = 'secret for pusher.com application'
  def __repr__(self):
    return repr({
      'host': self.host, 
      'port': self.port,
      'app_id': self.app_id,
      'key': self.key,
      'secret': self.secret,
      })


class pusher(Object):
  Description = 'Information for connecting to pusher.com using `pusher` client (lowercase p)'
  class app_id(String):
    Description = 'app_id for pusher.com application'
  class key(String):
    Description = 'key for pusher.com application'
  class secret(String):
    Description = 'secret for pusher.com application'
  class cluster(String):
    Description = 'cluster param'
  class ssl(Boolean):
    Default = True
    Description = 'ssl param'
  def __repr__(self):
    return repr({
      'app_id': self.app_id,
      'key': self.key,
      'secret': self.secret,
      'cluster': self.cluster,
      'ssl': self.ssl,
      })

class Zen(Object):
  Description = 'Information for connecting to zencoder'
  class FullAccessKey(String):
    Description = 'The Zen Full Access Key'
  def __repr__(self):
    return repr({
      'FullAccessKey': self.FullAccessKey,
      })

class CloudConvert(Object):
  Description = 'Information for connecting to cloudconvert.com'
  class Key(String):
    Description = 'The API Key'
  def __repr__(self):
    return repr({
      'Key': self.Key,
      })


class DocStruct(Object):
  Description = 'AWS Access Info for DocStruct'

  class User(Object):
    Description = 'Project specific user given permissions to access project specific resources'

    class ARN(String):
      Description = 'ARN identifying this user'

    class Username(String):
      Description = 'Username of this user'

    class AccessKeyId(String):
      Description = "Access Key ID belonging to this user"

    class SecretKey(String):
      Description = "Secret Key corresponding to the access_key_id for this user"

    def ToDict(self):
      return {
        'arn': self.ARN,
        'username': self.Username,
        'access_key_id': self.AccessKeyId,
        'secret_key': self.SecretKey,
        }
 
  class SQS(Object):
    Description = "Project specific SQS related credentials"

    class QueueUrl(String):
      Description = "URL of queue"

    def ToDict(self):
      return {
        'queueurl': self.QueueUrl,
        }
  
  class InputBucket(String):
    Description = "Name of the input bucket for this project"

  class OutputBucket(String):
    Description = "Name of the output bucket for this project"
    
  class KeyPrefix(String):
    Description = "A prefix to use when inserting objects into the bucket"
  
  def __repr__(self):
    return repr({
      'user': self.User.ToDict(),
      'sqs': self.SQS.ToDict(),
      'input_bucket': self.InputBucket,
      'output_bucket': self.OutputBucket,
      'keyprefix': self.KeyPrefix,
      })



class ACRM_AWS_Config(Object):
  class Region(String):
    pass
  class Prefix(String):
    pass
  class AccessKeyId(String):
    pass
  class SecretAccessKey(String):
    pass
  class UserArn(String):
    pass
  class BucketArn(String):
    pass
  class BucketEventQueueArn(String):
    pass
  class BucketEventQueueUrl(String):
    pass
  class SystemEventQueueArn(String):
    pass
  class SystemEventQueueUrl(String):
    pass
  class IOUserSecretAccessKey(String):
    pass
  class IOUserAccessKeyId(String):
    pass

  def __repr__(self):
    return repr(dict(
      Region = self.Region,
      Prefix = self.Prefix,
      AccessKeyId = self.AccessKeyId,
      SecretAccessKey = self.SecretAccessKey,
      UserArn = self.UserArn,
      BucketArn = self.BucketArn,
      BucketEventQueueArn = self.BucketEventQueueArn,
      BucketEventQueueUrl = self.BucketEventQueueUrl,
      SystemEventQueueArn = self.SystemEventQueueArn,
      SystemEventQueueUrl = self.SystemEventQueueUrl,
      IOUserSecretAccessKey = self.IOUserSecretAccessKey,
      IOUserAccessKeyId = self.IOUserAccessKeyId,
      ))


def GitCommit(Path):
  import os
  import subprocess
  os.chdir(Path)
  x = subprocess.run(['git', 'rev-parse', 'HEAD'], stdout=subprocess.PIPE).stdout.decode('utf-8').strip()
  
  y = subprocess.run(['git', 'describe', 'HEAD'], stdout=subprocess.PIPE).stdout.decode('utf-8').strip()

  return {'ID': x, 'Name': y}

