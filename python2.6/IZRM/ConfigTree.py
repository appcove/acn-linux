"""
ConfigTree - automatic configurations made easy

Copyright (C) 2007 IonZoft, Inc. ALL RIGHTS RESERVED.

--
The premise here is that there are, within a given source tree, specific file names called
_Lace.py and _Knot.py

The end result is a large and comprehensive configuration instance object that contains all static
configuration information about the projects in question.

Starting in /etc/WhiteBoot4, and then moving to your project root dir, and then recursing down
through the tree from there, this module will identify those two files.

The recursion function looks like this:
1. Include _Lace.py
2. Recurse (another nested function call, starting at 1) 
3. Include _Knot.py
4. Return

An example include order looks like:
  '/etc/WhiteBoot4/_Lace.py'
  '/var/var-home/jason/WhiteBoot4/DevLevel.2/_Lace.py'
  '/var/var-home/jason/WhiteBoot4/DevLevel.2/Tread/_Lace.py'
  '/var/var-home/jason/WhiteBoot4/DevLevel.2/ApexGlobal/_Lace.py'
  '/var/var-home/jason/WhiteBoot4/DevLevel.2/ApexGlobal/Web/Virtual/www.useapex.com/DocumentRoot/_Lace.py'
  '/var/var-home/jason/WhiteBoot4/DevLevel.2/ApexGlobal/Web/Virtual/api.useapex.com/DocumentRoot/_Lace.py'
  '/var/var-home/jason/WhiteBoot4/DevLevel.2/ApexGlobal/Conf/_Lace.py'
  '/var/var-home/jason/WhiteBoot4/DevLevel.2/wb/_Lace.py'
  '/var/var-home/jason/WhiteBoot4/DevLevel.2/wb/Python/_Lace.py'
  '/var/var-home/jason/WhiteBoot4/DevLevel.2/_Knot.py'
  '/etc/WhiteBoot4/_Knot.py'

Key Feature:
  This module preserves locals defined on a given _Lace.py for all of the _Lace.py and _Knot.py files found 
  on or below that point.

  This allows you to define a variable like "Project" which can then be referenced as "Project" within all
  of the files within that directory.

Behavior may be changed by altering modules variables:
  REGEXP_DEV_LEVEL
  CONFIG_SERVER_DIR
  CONFIG_RECURSE_FILENAME
  CONFIG_FINALIZE_FILENAME

"""
from __future__ import with_statement

from os import listdir
from os.path import join, isdir, islink, realpath, dirname, basename, exists
import re

REGEXP_DEV_LEVEL = re.compile('/DevLevel\\.([0-9])\\.?([0-9a-zA-Z]*)$')
CONFIG_SERVER_DIR = "/etc/WhiteBoot4"
CONFIG_RECURSE_FILENAME = "_Lace.py"
CONFIG_FINALIZE_FILENAME = "_Knot.py"
CONFIG_AUTOCONF_FILENAME = "_AutoConf.py"





#######################################################################################################################
class ArbitraryData(object):
	"""
	Generic Object for holding arbitrary properties
	"""
	


#######################################################################################################################
def FileWriter(*args):
	"""
	Returns a file open for writing that is identified by join()ing all of the arguments.
	In the case that the directory (holding) the specified file does not exist, an exception
	will be raised (of course).
	"""
	return open(join(*args), 'w')


#######################################################################################################################
class _Base(object):
	PropList = ()

	def __init__(self, MyInstance):			# MyInstance IS A KEWORD ARGUMENT
		self.__dict__['MyInstance'] = MyInstance
	
	def Print(self, Indent=0, Verbose=1, PropList=None):
		
		# The caller can pass a PropList, or just use slots..
		if PropList == None:
			PropList = self.__class__.PropList
		
		for v in PropList:
			
			# /^_/ is hidden
			if v[0] == '_':
				continue

			o = getattr(self, v)
			if isinstance(o, _Base):
				print (" " * Indent) + str(v) + " {}" + (" (" + str(o.__class__.__name__) + ")" if Verbose > 1 else '')
				o.Print(Indent=Indent+4, Verbose=Verbose)
			else:
				print (" " * Indent) + str(v) + (" == " + ("(" + type(o).__name__  +  ") " if Verbose > 1 else "" ) + str(o) if Verbose > 0 else '')
			

#######################################################################################################################
class _BaseCollection(_Base):
	ProxyClass = None		#This is the class to proxy-create

	#==============================================================================================
	def __init__(self, MyInstance):			# MyInstance IS A KEWORD ARGUMENT
		_Base.__init__(self, MyInstance=MyInstance)
		self.__dict__['_Collection'] = {}
		pass

	#==============================================================================================
	def __setitem__(self, name, value):
		if not isinstance(name, str):
			raise TypeError("Attribute name must be a string")
		
		if not isinstance(value, self.__class__.ProxyClass):
			raise TypeError("New attribute must be an instanceof '%s'." % self.__class__.ProxyClass)

		self.__dict__['_Collection'][name] = value
	
	#==============================================================================================
	__setattr__ = __setitem__

	#==============================================================================================
	def __getitem__(self, name):
		if not isinstance(name, str):
			raise TypeError("Attribute name must be a string")
		
		if not self.__dict__['_Collection'].has_key(name):
			raise KeyError("Collection Item '%s' does not exist." % name)
		
		return self.__dict__['_Collection'][name]

	#==============================================================================================
	__getattr__ = __getitem__
		

	#==============================================================================================
	def __contains__(self, name):
		return self.__dict__['_Collection'].has_key(name)

	#==============================================================================================
	__hasattr__ = __contains__

	#==============================================================================================
	def Print(self, *args, **kwargs):
		kwargs['PropList'] = self.__dict__['_Collection'].keys()
		_Base.Print(self, *args, **kwargs)

	#==============================================================================================
	# Return a list of all the items in this collection
	def GetAll(self):
		return self.__dict__['_Collection'].values()

#######################################################################################################################
#######################################################################################################################
#######################################################################################################################

class Instance(_Base):
	"""
	Parser Documentation
	"""
	
	__slots__ = (
		'Path', 
		'CallPath', 
		'AutoConf',
		'FileList', 
		'DevLevel', 
		'DevName', 
		'Verbose', 
		'Project',
		'Apache',
		'Server',
		'_ExecGlobals',
		)


	#==============================================================================================
	def __init__(self, sCallPath, Verbose=0):
		"""
		I am documentation on Parser Constructor
		"""
		
		# Get the realpath of the calling path
		self.CallPath = sTmpPath = realpath(sCallPath)

		# Must be a directory
		if not isdir(self.CallPath):
			raise Exception("Calling path '%s', (realpath='%s'), must be a directory" % (sCallPath, self.CallPath))
	
		# Controls output
		self.Verbose = Verbose


		# Assuming a call path of /home/user/WhiteBoot4/DevLevel.2/SomeProject/Web, this list should end up with:
		#   /etc/WhiteBoot4/
		#   /home/user/WhiteBoot4/DevLevel.2
		lNextPaths = []

		while True:
			# If this is the DevLevel directory, then stop
			match = REGEXP_DEV_LEVEL.search(sTmpPath)
			if match:
				self.Path = sTmpPath
				self.DevLevel = int(match.group(1))
				self.DevName = match.group(2)
				lNextPaths.append(sTmpPath)
				break
			
			# Go back a level
			sTmpPath = dirname(sTmpPath)
			
			# Check for the beginning
			if sTmpPath == '/':
				raise Exception("Invalid Call Path '%s'.  DevLevel.[0-9] directory not found." % sCallPath)

		# Check to see if the server config file is present.
		if exists(CONFIG_SERVER_DIR):
			lNextPaths.append(CONFIG_SERVER_DIR)

		# Now, reverse the list, so that they are in the right order
		lNextPaths.reverse()
		
		# List of files that were included
		self.FileList = []
		
		# AutoConf list
		# A list of 3-tuples
		# [0] Path to autoconf file
		# [1] Dictionary of locals used in that directory
		self.AutoConf = []


		# Load up remaining instance variabes
		self.Project = _ProjectCollection(MyInstance=self)
		self.Apache = _Apache(MyInstance=self)
		self.Server = _Server(MyInstance=self)
		oFactory = _Factory(self)

		# Globals to put into every function
		self._ExecGlobals = {
			'__builtins__'	: __builtins__, 	# Need this, otherwise __builtins__.* will get copied in!
			'Instance'		: self,				# The configuration instance variable	
			'Server'		: self.Server,		# Server related defaults
			'Factory'		: oFactory,			# Factory for creating new instances
			'dirname'		: dirname,			# useful function
			'join'			: join,				# useful function
			}


		# Start recursion
		self.__ScanDir(lNextPaths, {})
	

	#==============================================================================================	
	def	Print(self, Indent=4, Verbose=None):
		
		if Verbose == None:
			Verbose = self.Verbose
	
		if Verbose > 1:
			print "Instance" + (" {} (" + self.__class__.__name__ + ")" if Verbose > 1 else "")
		else:
			print "Instance {}"
		
		PropList = list(self.__slots__)
		
		# Remove some things that don't need to be displayed normally
		if Verbose < 2:
			PropList.remove('AutoConf')
			PropList.remove('FileList')
			PropList.remove('CallPath')
			PropList.remove('Verbose')
			
		_Base.Print(self, Indent=Indent, Verbose=Verbose, PropList=PropList)

	#==============================================================================================	
	def	__ScanDir(self, lNextPaths, oLocals):
		"""
		Pass a list of paths to examine next for self.BaseName files.  
		NOTE: If len(lNextPaths) == 1, then that directory and all visible subdirs will be 
		  scanned for self.BaseName files 
		"""
		
		sPath = lNextPaths.pop(0)

		# Theory: We want all children to have all of the data of the parent, but not be stuck
		#   with that data when we return and go to another child.
		oLocals = oLocals.copy()  # SHALLOW COPY!!!
			

		# -----------------------------------------------------------------------------------------
		# Obtain the list of directories in this one
		lDirs = listdir(sPath)

		# -----------------------------------------------------------------------------------------
		# If we find self.BaseName, then include it first
		if CONFIG_RECURSE_FILENAME in lDirs:
			self.__IncludeFile(join(sPath, CONFIG_RECURSE_FILENAME), oLocals)
	
		# -----------------------------------------------------------------------------------------
		if len(lNextPaths) > 0:
			# We know exactly where to go, because we have an item in the path list
#			print " >> AutoEntering %s because of %s" % (lNextPaths[0], lNextPaths)
			self.__ScanDir(lNextPaths, oLocals)
		else:
			# Recursion, but skip hidden files
			for sDir in (join(sPath, s) for s in lDirs if s[0] != '.'):
#				print "Looking at %s" % sDir
			
				# Do not follow symbolic links
				if isdir(sDir) and not islink(sDir):
#					print " >> Entering %s" % sDir
					self.__ScanDir([sDir], oLocals)
			
		# -----------------------------------------------------------------------------------------
		# If we find a finalize filename, then include it before backing out of this function
		if CONFIG_FINALIZE_FILENAME in lDirs:
			self.__IncludeFile(join(sPath, CONFIG_FINALIZE_FILENAME), oLocals)
		
		# -----------------------------------------------------------------------------------------
		# Take not of any AUTOCONF files, and add them to the self.AutoConf list
		if CONFIG_AUTOCONF_FILENAME in lDirs:
			self.AutoConf.append((join(sPath, CONFIG_AUTOCONF_FILENAME), oLocals))

	
	#==============================================================================================	
	def	__IncludeFile(self, sFile, oLocals):
			
			self.FileList.append(sFile)
			
			# Prepare the file for inclusion
			oLocals['File'] = ArbitraryData()
			oLocals['File'].Path = dirname(sFile)
			

			# Include the file
#			print "Running %s with %s ..." % (sFile, oLocals)
			execfile(sFile, self._ExecGlobals, oLocals)
		
	#==============================================================================================	
	"""
	Run all of the CONFIG_AUTOCONF_FILENAME files found in the directory tree, along with the locals
	that were present when they were found.
	"""

	def RunAutoConf(self, Verbose=None):

		# Globals
		dGlobals = {
			'__builtins__'	: __builtins__, 	# Need this, otherwise __builtins__.* will get copied in!
			'Instance'		: self,				# The configuration instance variable	
			'FileWriter'	: FileWriter,		# A utility function for opening a file for writing
			'dirname'		: dirname,			# useful function
			'join'			: join,				# useful function
			}

		if Verbose == None:
			Verbose = self.Verbose
		
		for sFile, dLocals in self.AutoConf:
			
			dLocals['Verbose'] = Verbose
			
			if Verbose >= 1:
				print "Running AutoConf File '%s'" % sFile

			if Verbose >= 2:
				print "  Global Variables are %s" % dLocals
				print "  Local Variables are %s" % dLocals
				print 

			execfile(sFile, dGlobals, dLocals)


	
				
#######################################################################################################################
class _Server(_Base):
	PropList = ('HostName', 'IP', 'DevIP', 'DevPort')
	
	def __init__(self, MyInstance):			# MyInstance IS A KEWORD ARGUMENT
		_Base.__init__(self, MyInstance=MyInstance)
		
		self.HostName = None
		self.IP = None

		
	# To be changed in the future to functional property
	@property
	def DevIP(self):
		return self.IP

	@property
	def DevPort(self):
		return 80


#######################################################################################################################
class _Project(_Base):
	PropList = ('Identifier', 'Path', 'MySQL', 'Data')

	def __init__(self, MyInstance):			# MyInstance IS A KEWORD ARGUMENT
		_Base.__init__(self, MyInstance=MyInstance)

		self.Identifier = None
		self.Path = None
		self.MySQL = None
		self.Data = {}
		
		
#######################################################################################################################
class _ProjectCollection(_BaseCollection):
	ProxyClass = _Project
	
	def __init__(self, MyInstance):			# MyInstance IS A KEWORD ARGUMENT
		_BaseCollection.__init__(self, MyInstance=MyInstance)

#######################################################################################################################
class _MySQL(_Base):
	PropList = ('Host', 'Port', 'Username', 'Password', 'Database')

	def __init__(self, MyInstance):			# MyInstance IS A KEWORD ARGUMENT
		_Base.__init__(self, MyInstance=MyInstance)

		self.Host = 'localhost'
		self.Port = 3306
		self.Username = None
		self.Password = None
		self.Database = None

#######################################################################################################################
class _Apache(_Base):
	PropList = ('VirtualHost', 'Directory', 'DomainNameTemplate')

	def __init__(self, MyInstance):			# MyInstance IS A KEWORD ARGUMENT
		_Base.__init__(self, MyInstance=MyInstance)
		
		self.VirtualHost = _VirtualHostCollection(MyInstance=MyInstance)
		self.Directory = _DirectoryCollection(MyInstance=MyInstance)
		
		# Used by the function below to generate a development domain name
		self.DomainNameTemplate = "%(ServerName)s.%(DevLevel)s.%(DevName)s.%(HostName)s"

	# Make a domain name from the DomainTemplate on this apache object
	def MakeDomainNameFromTemplate(self, sServerName):
		
		if self.MyInstance.DevLevel == 0:
			return sServerName
		
		data = {
			'Instance': self.MyInstance,
			'ServerName': sServerName, 
			'DevLevel': self.MyInstance.DevLevel,
			'DevName': self.MyInstance.DevName,
			'HostName': self.MyInstance.Server.HostName}

		# If it is a string, use standard python dict replacement syntax
		if isinstance(self.DomainNameTemplate, str):
			return self.DomainNameTemplate % data
		
		# Otherwise, if it is callable, then call it with the data
		elif callable(self.DomainNameTemplate):
			return self.DomainNameTemplate(data)
		
		# Uh-uo
		else:
			raise TypeError("Instance.Apache.DomainNameTemplate must either be a string, or callable")


#######################################################################################################################
class _Directory(_Base):
	PropList = ('Path',)
	
	def __init__(self, MyInstance):			# MyInstance IS A KEWORD ARGUMENT
		_Base.__init__(self, MyInstance=MyInstance)
		
		self.Path = Path

#######################################################################################################################
class _DirectoryCollection(_BaseCollection):
	ProxyClass = _Directory

	def __init__(self, MyInstance):			# MyInstance IS A KEWORD ARGUMENT
		_BaseCollection.__init__(self, MyInstance=MyInstance)


#######################################################################################################################
class _VirtualHost(_Base):
	PropList = ('Identifier', 'URL', 'DocumentRoot', 'ServerName', 'ServerAlias', 'IP', 'Port', 'Extra', 'SSL')

	def __init__(self, MyInstance):			# MyInstance IS A KEWORD ARGUMENT
		_Base.__init__(self, MyInstance=MyInstance)
		
		# Absolute path to the document root
		self.DocumentRoot = None
		
		# Production Servername (ex: "example.com")
		self.ServerName = None
		
		# List of Production Servername aliases (ex: "site.example.com")
		self.ServerAlias = []
		
		# Production IP Address 
		self.IP = None
		
		# Extra lines to add to the <VirtualHost> container
		self.Extra = []

		# SSL Mode?
		self.SSL = False


	@property
	def Identifier(self):
		return "%s|%s" % (self.ServerName, "SSL" if self.SSL else "NoSSL")
	
	@property
	def URL(self):
		return "%s://%s" % ("https" if self.SSL else "http", self.ServerName)

	@property
	def IPPort(self):
		return "%s:%s" % (self.IP, self.Port)

	@property
	def Port(self):
		if self.MyInstance.DevLevel == 0 and self.SSL:
			return 81
		else:
			return 80

	def SetServerName(self, ServerName):
		self.ServerName = self.MyInstance.Apache.MakeDomainNameFromTemplate(ServerName)

	def SetServerAlias(self, *args):
		self.ServerAlias = []
		self.AddServerAlias(*args)
	
	def AddServerAlias(self, *args):
		for sa in args:
			self.ServerAlias.append(self.MyInstance.Apache.MakeDomainNameFromTemplate(sa))

	def SetIP(self, sIP, sDevIP=None):
		if self.MyInstance.DevLevel == 0:
			self.IP = sIP
		elif sDevIP == None:
			self.IP = self.MyInstance.Server.DevIP
		else:
			self.IP = sDevIP
			

#######################################################################################################################
class _VirtualHostSSL(_VirtualHost):

	def __init__(self, MyInstance):			# MyInstance IS A KEWORD ARGUMENT
		_VirtualHost.__init__(self, MyInstance=MyInstance)

		if MyInstance.DevLevel == 0:
			self.SSL = True
		else:
			self.SSL = False

		
#######################################################################################################################
class _VirtualHostCollection(_BaseCollection):
	ProxyClass = _VirtualHost
	
	def __init__(self, MyInstance):			# MyInstance IS A KEWORD ARGUMENT
		_BaseCollection.__init__(self, MyInstance=MyInstance)

#######################################################################################################################

# Exists to create other objects in this module
# Instanciate one with the current Instance as the only parameter to the constructor
# This will allow the automatic configuration of the MyInstance property on each object

class _Factory(object):

	def __init__(self, oInstance):
		self._Instance = oInstance

	def Project(self, *a, **b):
		b['MyInstance'] = self._Instance
		return _Project(*a, **b)
	
	def MySQL(self, *a, **b):
		b['MyInstance'] = self._Instance
		return _MySQL(*a, **b)
	
	def VirtualHost(self, *a, **b):
		b['MyInstance'] = self._Instance
		return _VirtualHost(*a, **b)
	
	def VirtualHostSSL(self, *a, **b):
		b['MyInstance'] = self._Instance
		return _VirtualHostSSL(*a, **b)
	
	def Directory(self, *a, **b):
		b['MyInstance'] = self._Instance
		return _Directory(*a, **b)


