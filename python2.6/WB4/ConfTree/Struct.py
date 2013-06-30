from __future__ import with_statement

from ConfTree import Node, NodeCollection

import os
from os.path import isdir, abspath, exists, join
from types import NoneType
import glob
import re

from Extruct import ParseFileForNames

	
####################################################################################################
class App(Node):
	
	FieldSpec 			= ('ModuleName', 'Path', 'API')

	onSet_ModuleName	= Node.String

	def onSet_Path(self, value):
		if not isdir(value):
			raise ValueError("Directory must exist: %s" % str(value))
		return abspath(value)

	onNew_API			= lambda self: {}
	onSet_API			= Node.Dict
		

	def __init__(self, oInstance, oProject):
		object.__setattr__(self, 'ParentInstance', oInstance)
		object.__setattr__(self, 'ParentProject', oProject)
		Node.__init__(self)
	
	def __repr__(self):
		return "<App '%s' at %s>" % (self.GetRaw('ModuleName'), hex(id(self)))

####################################################################################################
class ExtructCollection(dict):
	
	def __init__(self, oInstance, oProject):
		object.__setattr__(self, 'ParentInstance', oInstance)
		object.__setattr__(self, 'ParentProject', oProject)
		dict.__init__(self)
	
	def Scan(self, GlobPath):
		"""
		Scans the paths found on GlobPath, and parses the XML files in question
		"""
		for sFile in glob.glob(GlobPath):
			for name in ParseFileForNames(sFile):
				self[name] = abspath(sFile)



####################################################################################################
class MySQL(Node):
	
	FieldSpec 			= ('Host', 'Port', 'Username', 'Password', 'Database')
	XMLAttribs 			= ('Host', 'Port', 'Username', 'Password', 'Database')

	onNew_Host			= lambda self: self.ParentInstance.Default_MySQL_Host
	onSet_Host 			= Node.String
	
	onNew_Port			= lambda self: self.ParentInstance.Default_MySQL_Port
	onSet_Port 			= Node.Integer
	
	onNew_Username		= lambda self: self.ParentProject.ID
	onSet_Username 		= Node.String
	
	onSet_Password		= Node.String
	
	onNew_Database		= lambda self: "%s_%i" % (self.ParentProject.ID, self.ParentInstance.DevLevel)
	onSet_Database		= Node.String
	
	def __init__(self, oInstance, oProject):
		object.__setattr__(self, 'ParentInstance', oInstance)
		object.__setattr__(self, 'ParentProject', oProject)
		Node.__init__(self)


####################################################################################################
class VirtualHost(Node):
	
	FieldSpec 			= ('ID', 'Protocol', 'IP', 'Port', 'Extra', 'ServerName', 'ServerAlias', 'DocumentRoot', 'URL')
	XMLAttribs			= ('ID', 'Protocol', 'IP', 'Port')

	onNew_Protocol		= lambda self: 'http'
	def onSet_Protocol(self, value):
		if value not in ('http', 'https'):
			raise ValueError("Invalid value!")

		if self.ParentInstance.DevLevel > 0:
			return 'http'
		else:
			return value
	

	onNew_Extra			= lambda self: []
	onSet_Extra			= Node.List

	onNew_IP			= lambda self: '*'
	onSet_IP			= Node.String

	onNew_Port			= lambda self: 80
	onSet_Port			= Node.Integer

	def onSet_ServerName(self, value):
		return self.ParentInstance.MangleHost(value)

	onNew_ServerAlias	= lambda self: []
	def AddAlias(self, sAlias):
		self.ServerAlias.append(self.ParentInstance.MangleHost(sAlias))

	def onSet_DocumentRoot(self, value):
		if not isdir(value):
			raise ValueError("DocumentRoot must exist: %s" % str(value))
		return abspath(value)

	def onNew_URL(self):
		return "%s://%s" % (self.Protocol, self.ServerName)

	def __init__(self, oInstance, oProject):
		object.__setattr__(self, 'ParentInstance', oInstance)
		object.__setattr__(self, 'ParentProject', oProject)
		Node.__init__(self)
	
	def __repr__(self):
		return "<VirtualHost '%s' at %s>" % (self.GetRaw('ID'), hex(id(self)))


	
####################################################################################################
class VirtualHostCollection(NodeCollection):
	
	ItemType 			= VirtualHost
	KeyField 			= 'ID'
	XMLItemName			= 'VirtualHost'

	def __init__(self, oInstance, oProject):
		object.__setattr__(self, 'ParentInstance', oInstance)
		object.__setattr__(self, 'ParentProject', oProject)
		NodeCollection.__init__(self)

	def Add(self, Key):
		return NodeCollection.Add(self, Key, self.ParentInstance, self.ParentProject)


####################################################################################################
class Project(Node):

	FieldSpec 			= ('ID', 'Path', 'MySQL', 'VirtualHost', 'Extruct', 'App', 'OtherData')
	XMLAttribs			= ('ID',)
	XMLRenames			= {'VirtualHost': 'VirtualHost-List', 'Extruct': 'Extruct-List'}


	def onSet_Path(self, value):
		if not isdir(value):
			raise ValueError("Path must exist: %s" % str(value))
		return abspath(value)
	
	onNew_MySQL			= lambda self: MySQL(self.ParentInstance, self)

	onNew_VirtualHost	= lambda self: VirtualHostCollection(self.ParentInstance, self)
	
	onNew_Extruct			= lambda self: ExtructCollection(self.ParentInstance, self)

	def onNew_App(self):
		return None
	def onSet_App(self, value):
		if not isinstance(value, (NoneType, App)):
			raise TypeError("Value must be instance of App.")
		return value
	def AppInit(self, Path):
		self.App = App(self.ParentInstance, self)
		self.App.ModuleName = self.ID
		self.App.Path = Path
		return self.App

	onNew_OtherData		= lambda self: {}

	def __init__(self, oInstance):
		object.__setattr__(self, 'ParentInstance', oInstance)
		Node.__init__(self)

	def __repr__(self):
		return "<Project '%s' at %s>" % (self.GetRaw('ID'), hex(id(self)))

####################################################################################################
class ProjectCollection(NodeCollection):

	ItemType 			= Project
	KeyField 			= 'ID'
	XMLItemName			= 'Project'

	def __init__(self, oInstance):
		object.__setattr__(self, 'ParentInstance', oInstance)
		NodeCollection.__init__(self)

	def Add(self, Key):
		o = NodeCollection.Add(self, Key, self.ParentInstance)
		o.Path = "."
		return o


####################################################################################################


class AppServer(Node):
	"""
	The defaults for the appserver are:
		AF_UNIX
		Instance.Path + /.WB4/AppServer.sock

	"""


	FieldSpec		= ('Address', 'Port', 'Type')
	
	onNew_Address	= lambda self: join(self.ParentInstance.PathInfo.Conf, 'AppServer.sock')
	onSet_Address	= Node.String
	
	onNew_Port		= lambda self: 0
	onSet_Port		= Node.Integer
	
	onNew_Type		= lambda self: 'AF_UNIX'
	onSet_Type		= Node.Enum('AF_INET', 'AF_UNIX')
	
	
	def __init__(self, oInstance):
		object.__setattr__(self, 'ParentInstance', oInstance)
		Node.__init__(self)


####################################################################################################


class Apache(Node):
	"""
	"""

	FieldSpec		= ('Conf',)
	
	onNew_Conf		= lambda self: []
	onSet_Conf		= Node.List
	
	def __init__(self, oInstance):
		object.__setattr__(self, 'ParentInstance', oInstance)
		Node.__init__(self)





####################################################################################################
class Instance(Node):
	
	FieldSpec 			= ('Path', 'DevLevel', 'DevName', 'ServerName', 'ServerAddr', 'AppServer', 'Apache', 'User', 'Project', 'PortMap', 'OtherData')
	OtherProp			= ('PathInfo', 'MangleHost', 'MangleHostIZRM', 'Default_MySQL_Port', 'Default_MySQL_Host')
	XMLRenames			= {'Project': 'Project-List'}

	def onSet_Path(self, value):
		if not isdir(value):
			raise ValueError("Path must exist: %s" % str(value))
		return abspath(value)

	onSet_DevLevel		= Node.Integer

	onSet_DevName		= Node.StringOrNone

	onSet_ServerName	= Node.String
	
	onSet_ServerAddr	= Node.String

	onNew_AppServer		= lambda self: AppServer(self)
	
	onNew_Apache		= lambda self: Apache(self)

	onNew_User			= lambda self: os.environ['USER']
	onSet_User			= Node.String
	
	onNew_Project		= lambda self: ProjectCollection(self)

	onNew_PortMap		= lambda self: {}
	
	onNew_OtherData		= lambda self: {}
	
	def __init__(self):
		
		# Create a reference to MangleHostname on THIS object. 
		# Why?  To facilitate replacing it without having to use __dict__
		object.__setattr__(self, 'MangleHost', self.MangleHost)
		
		# Other useful data
		object.__setattr__(self, 'Default_MySQL_Port', 3306)
		object.__setattr__(self, 'Default_MySQL_Host', 'localhost')
	
		# Call parent constructor
		Node.__init__(self)


	def MangleHost(self, value):
		if self.DevLevel == 0:
			return value
		elif self.DevName:
			return "%s.%s.%s.%s.%s" % (value, self.DevLevel, self.DevName.lower(), self.User, self.ServerName)
		else:
			return "%s.%s.%s.%s" % (value, self.DevLevel, self.User, self.ServerName)
	
	def MangleHostIZRM(self, value):
		if self.DevLevel == 0:
			return value
		elif self.DevName:
			return "%s.%s.%s.preview.appcove.net" % (value, self.DevLevel, self.DevName.lower())
		else:
			return "%s.%s.preview.appcove.net" % (value, self.DevLevel)

	def UseIZRM(self):
		self.MangleHost = self.MangleHostIZRM
		

