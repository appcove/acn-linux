
import sys
import traceback
import time

from os import path, listdir, chdir, getcwd
from os.path import join, exists, dirname, abspath, isdir
import glob

from types import NoneType, BooleanType, IntType, FloatType, StringType, TupleType, ListType, DictType

from xml.etree import ElementTree


DUMP_SEP = "   "



class TreeException(Exception):
	def __init__(self, CallStack, Message):
		self.Stack = CallStack
		Exception.__init__(self, Message)


###################################################################################################
class Tree(object):
	
	CONF_FILE_NAME = "_Twig.py"


	#==============================================================================================
	def __init__(self):

		self.Globals = {
			'__builtins__' 	: {},
			'abspath'		: path.abspath,
			'AutoConf'		: self._AutoConf,
			'basename'		: path.basename,
			'dirname'		: path.dirname,
			'exists'		: path.exists,
			'getcwd'		: getcwd,
			'Include'		: self.Include,
			'IncludeCF'		: self._IncludeCF,
			'isfile'		: path.isfile,
			'isdir'			: path.isdir,
			'islink'		: path.islink,
			'join'			: path.join,
			'now'			: time.time,
			'str'			: str,
			'int'			: int,
			}

		self.Log = [
			"Globals: %s" % str([s for s in self.Globals]),
			]

		# This holds the namespace for the currently running Include call.
		self._ns_current = None

		self._Stack = []

		# This holds a list of AutoConf entries
		self._AutoConf = []

	#==============================================================================================
	def SetVars(self, **kwargs):
		for k in kwargs:
			self.Globals[k] = kwargs[k]
	
	#==============================================================================================
	def DelVars(self, *args):
		for k in args:
			del(self.Globals[k])
	


	#==============================================================================================
	def Include(self, sGlobPath):
		
		paths = glob.glob(sGlobPath)

		if len(paths) == 0:
			raise OSError(2, "File(s) not found", sGlobPath)

		for sPath in paths:
			self._Include(sPath)
	
	#==============================================================================================
	def _Include(self, sPath):
		
		# Get some path info for below
		sFullPath = abspath(sPath)
		sWorkDir = dirname(sFullPath)

		# Log our action
		self.Log.append("Included: '%s' as '%s'" % (sPath, sFullPath))
		
		# Save the "state" of the current namespace in a local variable
		ns_old = self._ns_current

		# Generate a new namespace
		ns_new = {} if ns_old == None else ns_old.copy()

		# This is in a try block to facilitate cleanup and clean exception raising
		try:
			# Push this file on the stack
			self._Stack.append(sFullPath)
			
			# Update the "Current" namespace
			self._ns_current = ns_new
			
			# Get the old working directory
			cwd_old = getcwd()
			
			# Update the current working directory
			chdir(sWorkDir)

			# Include the file with the "New" namespace
			execfile(sFullPath, self.Globals, ns_new)
		
		
		# This is to prevent recursive catching of the re-thrown TreeException below
		except TreeException:
			raise
		
		
		except SyntaxError, e:

			msg = "SyntaxError at line %s, character %s: %s" % (e.lineno, e.offset, e.msg)
			stack = self._Stack[0:-1] + ["%s:%s" % (e.filename, e.lineno)]

			raise TreeException(stack, msg)
		

		# Catch all other exceptions and turn them into a TreeException
		except:
			stack = self._Stack[:]
			msg = "unknown error occured while handling error!"
			
			try:
				# Grab exception and traceback info
				e, tb = sys.exc_info()[1:3]
			
				# Extract the last element from the tb stack, and add it to the end of our stack
				tbe = traceback.extract_tb(tb, 2)

				if len(tbe) > 1:
					tbe = tbe[1]
				elif len(tbe) > 0:
					tbe = tbe[0]
				else: 
					tbe = ('Unknown-Error-No-Traceback', '?')
			
				# When forming the final stack for the exception, we don't want a duplicate last element on the 
				# stack, so strip it off.  The format for the last element includes the line number.
				stack = self._Stack[0:-1] + ["%s:%s" % (tbe[0], tbe[1])]

				# Format the message (may depend on the exception type
				if isinstance(e, OSError):
					msg = "OSError: [Errno %s] %s: '%s'" % (e.errno, e.strerror, e.filename)
				else:
					msg = "%s: %s" % (e.__class__.__name__, str(e))
				
				# Must explicitly break these references
				del(e, tb, tbe)

				# Log ths error to the log
				self.Log.append(msg)
			
			except:
				pass

			# Raise a custom exception			
			raise TreeException(stack, msg)
	
		# Clean up
		finally:
			# Replace the "old" namespace before exiting.
			self._ns_current = ns_old

			# Reset to the old cwd
			chdir(cwd_old)

			# Pop this file off the stack
			self._Stack.pop()

	#==============================================================================================
	def RunAutoConf(self):
		"""
		Includes all of the registered auto conf files
		"""
		
		while len(self._AutoConf):
			
			path, locals = self._AutoConf.pop(0)
			
			self.Log.append("Including AutoConf %s with %s" % (path, str(locals)))
			
			self._ns_current = locals
			
			try:
				self.Include(path)
			
			finally:
				self._ns_current = {}
			
	#==============================================================================================
	def _IncludeCF(self, sFileName):
		"""
		Includes all of the children files relative to the current directory.
		"""
		
		filelist = listdir('.')
		filelist.sort()

		for sFile in (join(f, sFileName) for f in filelist if isdir(f)):
			if exists(sFile):
				self.Include(sFile)
	
	#==============================================================================================
	def _AutoConf(self, sPath, **locals):
		"""
		This method registers an AutoConf file, along with any local variables to be made 
		available at the time of SaveAutoConf()
		"""

		# Append a Tuple
		self._AutoConf.append((abspath(sPath), locals))
	
		

###################################################################################################
#Conversion functions


def ThingToXML(oNode, value):
	"""
	If the data type of a given field implements ToXML, then an empty node will be attached 
	and passed to the ToXML method of the child field object.

	Otherwise, the data type of the given field must be one of: (NoneType, BooleanType, IntType, 
	FloatType, StringType, ListType, DictType), which will be written as a child node
	"""	

	if hasattr(value, 'ToXML'):
		value.ToXML(oNode)
	
	elif isinstance(value, NoneType):
		pass

	elif isinstance(value, BooleanType):
		oNode.text = "1" if value else "0"

	elif isinstance(value, (IntType, FloatType, StringType)):
		oNode.text = str(value)

	elif isinstance(value, ListType):
		for value2 in value:	
			oChildNode = ElementTree.SubElement(oNode, 'Value')
			ThingToXML(oChildNode, value2)
	
	elif isinstance(value, DictType):
		for key2, value2 in value.items():	
			oChildNode = ElementTree.SubElement(oNode, 'Value', Key=str(key2))
			ThingToXML(oChildNode, value2)

	else:
		raise TypeError("ThingToXML knows nothing about the %s type." % type(value))



###################################################################################################
#Conversion functions

class Convert(object):
	def __new__(cls, value):
		o = object.__new__(cls)
		o.TL = []
		o.Indent = 0
		o.Value(value)
		return str.join("", o.TL)

		
	def Value(self, DATA):
		
		if isinstance(DATA, NoneType):
			self._NoneType(DATA)
		
		elif isinstance(DATA, BooleanType):
			self._BooleanType(DATA)
		
		elif isinstance(DATA, IntType):
			self._IntType(DATA)
		
		elif isinstance(DATA, FloatType):
			self._FloatType(DATA)
		
		elif isinstance(DATA, StringType):
			self._StringType(DATA)
		
		elif isinstance(DATA, TupleType):
			self._TupleType(DATA)
		
		elif isinstance(DATA, ListType):
			self._ListType(DATA)
		
		elif isinstance(DATA, DictType):
			self._DictType(DATA)
		
		else:	
			raise AttributeError("No type conversion defined for Type %s (value=%s)" % (type(DATA), str(DATA)))


class Convert_Python(Convert):
	
	def _NoneType(self, DATA):
		self.TL.append('None')
	
	def _BooleanType(self, DATA):
		self.TL.append('True' if DATA else 'False')

	def _IntType(self, DATA):
		self.TL.append(str(DATA))

	def _FloatType(self, DATA):
		self.TL.append(str(DATA))

	def _StringType(self, DATA):
		self.TL.append('"' + DATA.encode('string_escape') + '"')
	
	def _ListType(self, DATA):
		self.TL.append('[')
		for v in DATA:
			self.Value(v)
			self.TL.append(',')
		if self.TL[-1] == ',':
			self.TL.pop()
		self.TL.append(']')

	def _TupleType(self, DATA):
		self.TL.append('(')
		for v in DATA:
			self.Value(v)
			self.TL.append(',')
		self.TL.append(')')

	def _DictType(self, DATA):
		self.Indent += 1
		self.TL.append('{')
		self.TL.append("\n")
		for k in DATA:
			v = DATA[k]
			self.TL.append("\t"*self.Indent)
			self.TL.append('"' + str(k).encode('string_escape') + '"')
			self.TL.append(': ')
			self.Value(v)
			self.TL.append(',')
			self.TL.append("\n")
		self.TL.append("\t"*self.Indent)
		self.TL.append('}')
		self.Indent -= 1


class Convert_PHP(Convert):
	
	def _NoneType(self, DATA):
		self.TL.append('NULL')
	
	def _BooleanType(self, DATA):
		self.TL.append('True' if DATA else 'False')

	def _IntType(self, DATA):
		self.TL.append(str(DATA))

	def _FloatType(self, DATA):
		self.TL.append(str(DATA))

	def _StringType(self, DATA):
		self.TL.append('"' + DATA.encode('string_escape') + '"')
	
	def _ListType(self, DATA):
		self.TL.append('array(')
		for v in DATA:
			self.Value(v)
			self.TL.append(',')
		if self.TL[-1] == ',':
			self.TL.pop()
		self.TL.append(')')
	
	_TupleType = _ListType
	
	def _DictType(self, DATA):
		self.TL.append('array')
		self.TL.append("\n")
		self.TL.append("\t"*self.Indent)
		self.TL.append("(")
		self.TL.append("\n")
		self.Indent += 1
		for k in DATA:
			v = DATA[k]
			self.TL.append("\t"*self.Indent)
			self.TL.append('"' + str(k).encode('string_escape') + '"')
			self.TL.append(' => ')
			self.Value(v)
			self.TL.append(',')
			self.TL.append("\n")
		self.Indent -= 1
		self.TL.append("\t"*self.Indent)
		self.TL.append(')')




###################################################################################################
class FileWriter(object):

	
	#==============================================================================================
	def __init__(self):
		self.Data = {}

	def __len__(self):
		return len(self.Data)
	
	def __getitem__(self, key):
		return self.Data[key]

	def __setitem__(self, key, value):
		
		if not isinstance(key, StringType):
			raise TypeError("All keys must be string, not: %s" % type(key))

		if isinstance(value, (NoneType, BooleanType, IntType, FloatType, StringType, TupleType, ListType, DictType)):
			self.Data[key] = value
		elif hasattr(value, 'ToNative'):
			self.Data[key] = value.ToNative()
		else:
			raise TypeError("Incompatible type for value: %s" % type(value))
	
	def __iter__(self):
		return iter(self.Data)
	
	def __contains__(self, item):
		return item in self.Data

	#==============================================================================================
	def Write(self, sPath, sContent, Language=None):

		sPath = abspath(sPath)

		if not isdir(dirname(sPath)):
			raise OSError("Directory %s does not exist." % dirname(sPath))
		
		if Language == None:
			if sPath[-3:] == ".py":
				Language = 'Python'
			elif sPath[-4:] == ".php":
				Language = 'PHP'

		if Language == 'PHP':
			oConv = Convert_PHP
		elif Language == 'Python':
			oConv = Convert_Python
		else:
			raise ValueError('Invalid Language argument: %s' % str(Language))
		

		# Execute replacement using 'data'
		for key, value in self.Data.items():
			new_key = "{%s}" % key
			new_value = oConv(value)
			sContent = sContent.replace(new_key, new_value)
			
			
		oFile = open(sPath, 'w')
		oFile.write(sContent)
		oFile.close()


			
	#==============================================================================================
	







###################################################################################################
class Node(object):
	"""
	A node is a very general purpose object...

	It has static attribute support via attributes defined in the FieldSpec attribute.
	It has arbitrary item support via __getitem__ and __setitem__.

	FieldSpec:
		A tuple of field names.

	OtherProp:
		A tuple of "normal" properties

	onSet_FieldName(self, value):
		Called when FieldName is set via Set() or __setattr__().
		Must return (potentially modified) the value to set.
		
		If this method does not exist when FieldName is set, an exception is raised.
	
	onGet_FieldName(self, value):
		Called when FieldName is gotten via Get() or __getattr__().
		Must return the (potentially modified) value.

		If this method does not exist when FieldName is gotten, the value of Field Name is returned.

	onNew_FieldName(self, value):
		Called when FieldName is gotten but has not been set.
		Must return a new, default value.
		These typically take the form:
			
			onNew_X = lambda self: [1,2,3]
		
		But they can also be normal methods



	In order to access a field, it must first be initialized.  
	This can happen by:
		Settting it first (via SetRaw, Set, __setattr__), or
		By implementing a method onNew_FieldName, which returns a new value

	To make a field read only, do not implement the onSet_FieldName event.


	"""
	FieldSpec = ()
	OtherProp = ()
	XMLAttribs = ()
	XMLRenames = {}

	#==============================================================================================
	def __init__(self):
		
		# Field data is a list of field names mapped to field values
		object.__setattr__(self, '_FieldData', {})
		
	#==============================================================================================
	def __getattr__(self, sName):
		
		# Maybe it is in OtherProp
		if sName in self.__class__.OtherProp:
			return object.__getattr__(self, sName)
	
		# Ensure it is a valid attribute
		if sName not in self.__class__.FieldSpec:
			raise AttributeError("No field with name '%s' defined in FieldSpec." % sName)
			
		# Do we have a value set?
		if sName in self._FieldData:
			
			# Do we have a onGet event?
			if hasattr(self, "onGet_"+sName):
				# We do, call onGet with the value
				return getattr(self, "onGet_"+sName)(self._FieldData[sName])
			else:
				# No onGet override, just return the value
				return self._FieldData[sName]
		else:
			# Do we have an onNew event to init the value?
			if hasattr(self, "onNew_"+sName):
				# We do, call onNew with no parameters
				self._FieldData[sName] = getattr(self, "onNew_"+sName)()
				return self._FieldData[sName]
			else:
				# No onNew event, raise an exception
				raise AttributeError("Cannot read uninitialized value for field '%s'." % sName)


	Get = __getattr__

	#==============================================================================================
	def __setattr__(self, sName, eValue):
		
		# Maybe it is in OtherProp
		if sName in self.__class__.OtherProp:
			object.__setattr__(self, sName, eValue)
			return
		
		# Ensure it is a valid attribute
		if sName not in self.__class__.FieldSpec:
			raise AttributeError("No field with name '%s' defined in FieldSpec." % sName)
			
		# Check for presence of onSet override...
		if hasattr(self, "onSet_%s" % sName):
			# If so, save the return of the onSet call
			self._FieldData[sName] = getattr(self, "onSet_%s" % sName)(eValue)
		else:
			# Otherwise, raise an exception
			raise AttributeError("Field '%s' is read only." % sName)
	
	Set = __setattr__

	#==============================================================================================
	def GetRaw(self, sName):
	
		# Ensure it is a valid attribute
		if sName not in self.__class__.FieldSpec:
			raise AttributeError("No field with name '%s' defined in FieldSpec." % sName)
			
		try:
			return self._FieldData[sName]
		except KeyError:
			return None

	#==============================================================================================
	def SetRaw(self, sName, value):
	
		# Ensure it is a valid attribute
		if sName not in self.__class__.FieldSpec:
			raise AttributeError("No field with name '%s' defined in FieldSpec." % sName)
			
		if not isinstance(value, (NoneType, BooleanType, IntType, FloatType, StringType, TupleType, ListType, DictType)):
			raise TypeError("Invalid value type: %s" % type(value))
		
		self._FieldData[sName] = value
	

	#==============================================================================================
	def VarDump(self, nLevel=0):
		
		print self.__class__.__name__ + " Node..."
		nLevel += 1
		
		for sName in self.__class__.FieldSpec:
			try:
				v = self.Get(sName)
			except AttributeError, e:
				v = "AttributeError: " + str(e)

			print (DUMP_SEP*nLevel) + sName + " =",
			
			if hasattr(v, 'VarDump'):
				v.VarDump(nLevel)
			else:
				print str(v)

	#==============================================================================================
	def ToXML(self, oNode):
		"""
		This method takes a xml node which represents itself.

		For each Field, a child node will be created.

		ThingToXML() will be called with the child node and the child value

		"""
		
		# All the other fields, unless it has been placed as an attribute above
		for sName in self.FieldSpec:
		
			# Get the value
			try:
				value = self.Get(sName)
			except AttributeError:
				value = "*ERROR*"
		
			# Skip None values
			if value == None:
				continue
			
			# Obtain the XML name 
			if sName in self.XMLRenames:
				sXMLName = self.XMLRenames[sName]
			else:
				sXMLName = sName
			
			# Turn it into an attribute if needed
			if sName in self.XMLAttribs:
				oNode.attrib[sXMLName] = str(value)
			
			# Otherwise, create a new XML node
			else:
				oChildNode = ElementTree.SubElement(oNode, sXMLName)
				ThingToXML(oChildNode, value)
	
	
	#==============================================================================================
	def ToNative(self, DATA=None):
		if DATA == None:
			DATA = {}
		
		for sName in self.FieldSpec:
			
			value = self.Get(sName)

			if isinstance(value, (Node, NodeCollection)):
				DATA[sName] = {}
				value.ToNative(DATA[sName])
			else:
				DATA[sName] = value

		# Mostly ignored
		return DATA

	
	#==============================================================================================
	def Integer(self, value):
		return int(value)

	#==============================================================================================
	def String(self, value):
		return str(value)

	#==============================================================================================
	def StringOrNone(self, value):
		return None if value == None else str(value)
	
	#==============================================================================================
	def Bool(self, value):
		return bool(value)
	
	#==============================================================================================
	def List(self, value):
		return list(value)

	#==============================================================================================
	def Dict(self, value):
		return dict(value)

	#==============================================================================================
	@staticmethod
	def Enum(*args):
		"""
		You must pass a list of values that will be checked against.
		If none are found, then the [0]th element of *args will be used as the default value.
		Otherwise, a ValueError is raised.
		"""
		
		def _Enum(self, value):
			if value not in args:
				raise ValueError("Value must be one of %s" % (args,))
					
			return value
		
		return _Enum
	
	#==============================================================================================
	def RaiseException(self, value):
		raise AttributeError("Field value cannot be read from or cannot be written to.")


###################################################################################################
class NodeCollection(object):
	
	# These three items are required material on any derived class
	ItemType = Node
	KeyField = None
	XMLItemName = None
		


	def __init__(self):
		# Must use __setattr__ on base class
		object.__setattr__(self, '_Item', {})
	
	def Add(self, Key, *args, **kwargs):
		
		o = self.__class__.ItemType(*args, **kwargs)
		
		# If a KeyField has been specified, then set it automatically 
		if self.__class__.KeyField:
			o.SetRaw(self.__class__.KeyField, Key)
		
		self._Item[Key] = o

		return o

	def Get(self, sName):
		return self._Item[sName]

	__getattr__ = __getitem__ = Get

	def Set(self, sName, eValue):
		raise RuntimeError("Items cannot be set on a collection, only created through the Add method.")

	__setattr__ = __setitem__ = Set

	def __len__(self):
		return len(self._Item)
	
	def __contains__(self, item):
		return item in self._Item
	
	def __iter__(self):
		return iter(self._Item)

	def values(self):
		return self._Item.values()

	def items(self):
		return self._Item.items()
	
	#==============================================================================================
	def VarDump(self, nLevel=0):
		
		print self.__class__.__name__ + " Collection..."
		nLevel += 1
		
		for sName, v in self.items():

			print (DUMP_SEP*nLevel) + sName + " =",
			
			if hasattr(v, 'VarDump'):
				v.VarDump(nLevel)
			else:
				print str(v)

	#==============================================================================================
	def ToXML(self, oNode):
		"""
		This method takes a xml node which represents itself.

		For each item in the collection, a child node will be created.

		ThingToXML() will be called with the child node and the child value

		"""
		
		for key, value in self.items():
			
			oChildNode = ElementTree.SubElement(oNode, self.XMLItemName)
			ThingToXML(oChildNode, value)

	#==============================================================================================
	def ToNative(self, DATA=None):
		if DATA == None:
			DATA = {}
		
		for key, value in self.items():
			
			if isinstance(value, (Node, NodeCollection)):
				DATA[key] = {}
				value.ToNative(DATA[key])
			else:
				DATA[key] = value

		return DATA
		
