# vim:encoding=utf-8:ts=2:sw=2:expandtab

from decimal import Decimal
import re
import inspect
from os.path import join, isfile, isdir

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
  

class Object(BaseValue):
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
    for name in classes:
      cls2 = getattr(cls, name)

      # that is a subclass of BaseValue...
      if inspect.isclass(cls2) and issubclass(cls2, BaseValue):
        # Create an item in this class dict with the default 
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
    
    if len(path):
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

  

class Integer(BaseValue):
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

  

     
class String(BaseValue):
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
  @staticmethod
  def Validate(cls, path, value, errors):
    value = String.Validate(cls, path, value, errors)
    if cls.MustExist and not isfile(value):
      raise ValueError("Directory '{0}' does not exist".format(value))
    return value

class Directory(String):
  Exists = True
  @staticmethod
  def Validate(cls, path, value, errors):
    value = String.Validate(cls, path, value, errors)
    if cls.MustExist and not isdir(value):
      raise ValueError("Directory '{0}' does not exist".format(value))
    return value


class FileStruct(Object):
  class Path(Directory):
    Description = 'Absolute path to FileStruct database with trailing slash'
    RegexMatch = r'\/$', 'FileStuct Path MUST have a trailing slash'
    MustExist = True

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

class UserPass(Object):
  class Username(String):
    pass
  class Password(String):
    pass


class ProxiedSite(Object):
  class ServerName(String):
    pass
  class IP(IPAddress):
    pass
  class Port(Port):
    Default=80
  class SSLPort(Port):
    Default=443
  class ProxyIP(IPAddress):
    Default='127.0.0.1'
  class ProxyPort(Port):
    pass
  class URL_HTTP(String):
    pass
  class URL_HTTPS(String):
    pass
  class SSLCrt(File):
    Description = 'Path to SSL Crt file for this site'
    MustExist = False  #we lack permissions most likel 
    AllowNone = True
  class SSLKey(File):
    Description = 'Path to SSL Key file for this site'
    MustExist = False  #we lack permissions most likely
    AllowNone = True


