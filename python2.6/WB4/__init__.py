"""
The WhiteBoot4 Loader.
"""

import re
import sys
import time
from os.path import abspath, join, exists
from os import getcwd

import Extruct

###################################################################################################
class InvalidOperation(Exception):
	"""
	To be raised in the event that an object's internal state is not valid
	for the requested operation.
	"""
	pass


class AuthError(Exception):
	def __init__(self, sMessage, sCode=''):
		self.Code = sCode
		Exception.__init__(self, sMessage)

class GeneralError(Exception):
	def __init__(self, sMessage, eData):
		self.Data = eData
		Exception.__init__(self, sMessage)

class SecurityError(Exception):
	"""
	To be raised in the event of a security error.
	"""
	pass

class ValidationError(Exception):
	"""
	To be raise in the event of bad or incorrect data passed to a method
	that may expect such (ie. user input)

	The list of errors is propogated via the Data attribute 
	"""
	def __init__(self, Messages = None):
		if Messages == None:
			self.Error = []
		else:		
			self.Error = Messages
			
		Exception.__init__(self, "Data validation error.")

	@property
	def Data(self):
		return self.Error


__builtins__['AuthError'] = AuthError
__builtins__['GeneralError'] = GeneralError
__builtins__['InvalidOperation'] = InvalidOperation
__builtins__['SecurityError'] = SecurityError
__builtins__['ValidationError'] = ValidationError

###################################################################################################
# CallPath is the (relative) path to load this WB4 instance from.  
#   It is a keyword paraater.
#   If it is not specified, the value is obtained from getcwd()
def Load(CallPath=None):

	# If path is not specified, find it
	if CallPath == None:
		CallPath = getcwd()

	PI = PathInfo(CallPath)

	# Add the .WB4/AutoConf/Package directory to the WB4 search path
	__path__.append(PI.Package)


###################################################################################################
# DEPRICATED - replace with PathInfo class
def ParsePath(sPath):
	"""
	Returns a tuple of (InstancePath, DevLevel, DevName)

	Raises a ValueError in the case that these elements cannot be identified
	DevName will be None if it was not sepecified
	"""
	
	# Looking for DevLevel.[0-9]
	found = re.search('(/.*/DevLevel\.([0-9])(\.([a-zA-Z0-9_]+))?)/', sPath + "/")

	if found == None:
		raise Exception, "DevLevel.[0-9] directory not found in '%s'." % sPath

	#       Path            DevLevel             DevName
	return (found.group(1), int(found.group(2)), found.group(4))





###################################################################################################
class PathError(Exception):
	pass

class PathInfo(object):
	"""
	Takes a given path and parses it into all of the WB4 path components.
	- Raises a WB4.PathError if the path is invalid.
	- Raises an OSError if the path is not found

	Contains the following attributes:

		Instance		- Full path to this instance
		DevLevel		- integer development level
		DevName			- None or string DevName if present
		Conf			- Full path to the .WB4 directory
		ConfFile		- Full path to the instance conf file (.WB4/Instance.py)
		SystemConfFile	- Full path to the standard system conf file
		AutoConf		- Full path to the instance AutoConf dir (.WB4/AutoConf)
		DataFile		- Full path to the instance data file (.WB4/AutoConf/Instance.xml)
		Package			- Full path to the WB4 package directory
	"""

	def __init__(self, sPath):
		
		sPath = abspath(sPath)
		
		# Looking for DevLevel.[0-9]
		found = re.search('(/.*/DevLevel\.([0-9])(\.([a-zA-Z0-9_]+))?)/', sPath + "/")

		if found == None:
			raise PathError("DevLevel.[0-9] directory not found in '%s'." % sPath)

		self.Instance		= found.group(1)
		self.DevLevel 		= int(found.group(2))
		self.DevName		= found.group(4)

		self.Conf		 	= join(self.Instance, '.WB4')
		
		self.ConfFile		= join(self.Conf, 'Config.py')
		self.SystemConfFile = '/etc/WhiteBoot4/Server.py'
		
		self.AutoConf		= join(self.Conf, 'AutoConf')
		self.DataFile		= join(self.AutoConf, 'Instance.xml')
		self.Package		= join(self.AutoConf, 'Package')

		if not exists(self.Instance):
			raise OSError(2, "Instance path not found", self.Instance)



###################################################################################################
# Debugging support

__builtins__['DE'] = 0

def BUG(level, msg):
	if DE >= level:
		sys.stdout.write("[Debug%s] [%s] %s\n\n" % (level, time.strftime("%Y-%S-%d %H:%M:%S"), msg))

def EnableDEBUG(level):
	__builtins__['DE'] = level
	__builtins__['BUG'] = BUG


###################################################################################################
def Log(Level, Message):
	"""
	This is the function used to log.
	For now, we log to stderr via print
	"""
	sys.stderr.write("%s\t%s\t%s\n" % (Level, time.strftime('%c'), Message))
	
__builtins__['Log_Info'] 	= lambda m: Log(6, m)
__builtins__['Log_Notice']	= lambda m: Log(5, m)
__builtins__['Log_Warning'] = lambda m: Log(4, m)
__builtins__['Log_Error']	= lambda m: Log(3, m)
__builtins__['Log_Fatal']	= lambda m: Log(2, m)

__builtins__['Log_Panic']	= lambda m: Log(1, m) 


###################################################################################################


class WB4_App(object):
	
	# A mapping of (Realm, Type) => instanceof(SecurityContext)
	SCMap = {}
	
	# A map of Extruct Names mapped to file paths
	Extruct = {}
	
	# A MySQL data structure
	MySQL = None
	
	# A map of API Name to Location of function call
	API = {}
		
	# The path to this WB4 instance
	InstancePath = None

	# The DevLevel this code is running under
	DevLevel = None

	# The DevName this code is running under
	DevName = None

	# The Identifier of this Project
	Identifier = None

	# The full path to this project
	Path = None

	
	
	# The Application Server object, or None if not connected
	AS = None
	
	# The Security Context OBJECT that this code is running under
	# This MUST ALWAYS be referred to by App.SecurityContext.
	# The reason is that it will switch frequently, and outstanding
	# references must not be created and held.
	SecurityContext = None

	
	
	# A map of ID => Spec object of preloaded Extruct
	_Extruct = {}


	#==========================================================================
	# Forbid the creation of this or child classes
	def __new__(cls):
		raise NotImplementedError("This is a static class.")

	#==========================================================================
	@classmethod
	def LoadSecurityContext(cls, Context, ADDR):
		# Parse the security context
		RELM, TYPE, DSEG, UUID = SecurityContext.ParseString(Context)

		# Dynamically load and instanciate the correct class
		try:
			cls.SecurityContext = cls.SCMap[(RELM, TYPE)](RELM, TYPE, DSEG, UUID, ADDR)
		except KeyError:
			raise InvalidOperation("No SecurityContext registered with (%s,%s)." % (RELM, TYPE))

	#==========================================================================
	@classmethod
	def SwapSecurityContext(cls, RELM, TYPE, DSEG, UUID):
		"""
		Swaps the current security context for a new one...
		Normally, "<SELF>" would be used for Realm (translates to ProjectIdentifier)
		"""
		
		if RELM == "<SELF>":
			RELM = cls.Identifier
		
		# Keep the address from the old one
		ADDR = cls.SecurityContext.ADDR
		
		# Dynamically load and instanciate the correct class
		try:
			cls.SecurityContext = cls.SCMap[(RELM, TYPE)](RELM, TYPE, DSEG, UUID, ADDR)
		except KeyError:
			raise InvalidOperation("No SecurityContext registered with (%s,%s)." % (RELM, TYPE))
	
	#==========================================================================
	@classmethod
	def FreeSecurityContext(cls):
		cls.SecurityContext = None

	#==========================================================================
	# Takes a module or object containign at least the following attributes:
	@classmethod
	def Init(cls):

		# Public Attributes

		if not hasattr(cls, 'InstancePath'):
			raise AttributeError("Class '%s' did not define attribute '%s'." % (cls.__name__, 'InstancePath'))
		
		if not hasattr(cls, 'DevLevel'):
			raise AttributeError("Class '%s' did not define attribute '%s'." % (cls.__name__, 'DevLevel'))
		
		if not hasattr(cls, 'DevName'):
			raise AttributeError("Class '%s' did not define attribute '%s'." % (cls.__name__, 'DevName'))
		
		if not hasattr(cls, 'Identifier'):
			raise AttributeError("Class '%s' did not define attribute '%s'." % (cls.__name__, 'Identifier'))
		
		if not hasattr(cls, 'Path'):
			raise AttributeError("Class '%s' did not define attribute '%s'." % (cls.__name__, 'Path'))
		
		if not hasattr(cls, 'SCMap'):
			raise AttributeError("Class '%s' did not define attribute '%s'." % (cls.__name__, 'SCMap'))
		
		# Private attributes


	#==========================================================================
	# Convert Extruct, but look up registered xdata files to load the spec from
	@classmethod
	def Convert(cls, ID, DATA, ConversionType='Native>>Native'):
		
		# If the ID is found in the ID=>Path map, but not found in the cached Extruct...
		if ID in cls.Extruct and ID not in cls._Extruct:
			for oSpec in Extruct.ParseFile(cls.Extruct[ID]):
				cls._Extruct[oSpec.Name] = oSpec
		
		try:
			return cls._Extruct[ID].Convert(DATA, ConversionType)
		except KeyError:
			raise KeyError("Extruct Spec not found: %s" % ID)
	

	#==========================================================================
	@classmethod
	def CallAPI(cls, Method, DATA, Target='<SELF>'):
		
		# If the target of the API is this app, then call it directly.  Otherwise,
		# rely on the cls.AS attribute
		if Target in ('<SELF>', cls.Identifier):
			try:
				FunctionPath = cls.API[Method]
			except KeyError:
				raise KeyError("Method '%s' not defined in API." % Method)


			if FunctionPath[0] != ".":
				raise NotImplementedError("Absolute imports are not yet supported.")

			if "." not in FunctionPath[1:]:
				raise ValueError("Function '%s' is not valid." % FunctionPath)
			
			# Add the path of the module which contains this class (ie WB4.Project.SomeProject) to the beginning, resulting
			# in a FunctionPath that looks like: WB4.Project.SomeProject.API.Member.Select
			FunctionPath = cls.__module__ + FunctionPath

			# break it into a Module path, and a Function
			sModule, dot, sFunction = FunctionPath.rpartition('.')

			try:
				__import__(sModule)
				oModule = sys.modules[sModule]
			except (KeyError, ImportError), e:
				raise ImportError("During import of '%s' an error occured: %s" % (sModule, e.message))

			
			try:
				oFunc = getattr(oModule, sFunction)
			except AttributeError:
				raise ImportError("Module '%s' does not contain an attribute/function named '%s'." % (sModule, sFunction))

			return oFunc(DATA)
		
		# If the target is something els, then pass it on to the AppServer
		else:
			# NOTE: this will fail if the AS attribute is not defined
			return cls.AS.CallAPI(Method, DATA, Target=Target)
			





class SecurityContext(object):
	"""
	Security Contexts take either the form of a string, or an object that represents that string.

	This string format for a global context:
		"[SecurityContext:<GLOBAL>:%s:%i:%s]" % (Type, DSEG, UUID)
	
	Or this for a project specific context:
		"[SecurityContext:%s:%s:%i:%s]" % (Realm, Type, DSEG, UUID)

	
	Regarding RELM:
		<GLOBAL> security contexts are special - they can be instanciated in any project.
		Otherwise, they can only be loaded in the projects that has a matching RELM in the SCMap.
	
	"""
	
	Parse_RE = re.compile('^\[SecurityContext:([a-zA-Z0-9_]+|<GLOBAL>):([a-zA-Z0-9_]+):([0-9]+):([a-zA-Z0-9_.-]+)\]$')

	@staticmethod
	def BuildString(RELM, TYPE, DSEG, UUID):
		
		if UUID == None:
			UUID = '<NONE>'

		return "[SecurityContext:%s:%s:%i:%s]" % (RELM, TYPE, DSEG, UUID)

	@staticmethod
	def ParseString(Context):
		"""Returns a tuple of (RELM, TYPE, DSEG, UUID)"""

		match = SecurityContext.Parse_RE.match(Context)
		if not match:
			raise ValueError("Invalid or malformed security context: %s" % Context)
		
		return (match.group(1), match.group(2), int(match.group(3)), match.group(4))

	
	def __init__(self, RELM, TYPE, DSEG, UUID, ADDR):
		self.RELM = RELM
		self.TYPE = TYPE
		self.DSEG = DSEG
		self.UUID = UUID
		self.ADDR = ADDR
		self.onLoad()

	
	def ToString(self):
		return self.BuildString(self.RELM, self.TYPE, self.DSEG, self.UUID)

	
	# This event can be overridden by the derived classes to set custom 
	# properties, etc...  
	def onLoad(self):
		pass

	
		
	


