
# Import types
from types import NoneType, BooleanType, IntType, FloatType, StringType, ListType, TupleType, DictType
from decimal import Decimal as DecimalType

# Other code needed
from xml.etree import cElementTree as ElementTree
from decimal import Decimal
import hashlib
import re

# This is a cache of all spec names => spec objects
Debug = False
PrivateSpecName = '_LOCAL_'

# A regular expression which should match Spec names...
REGEX_SPEC_NAME = re.compile('^[0-9a-zA-Z_][0-9a-zA-Z._]*$')
REGEX_NODE_NAME = re.compile('^[a-zA-Z_][0-9a-zA-Z_]*$')



class Array(object):
	def __init__(self):
		self.D = {}
		self.L = []
	def __setitem__(self, k, v):
		self.D[k] = v
		self.L.append(v)


###################################################################################################
class ParseError(Exception):
	pass

###################################################################################################
def Parse(sXML):
	
	oXML = ElementTree.fromstring(sXML)
	sSum = hashlib.sha1(sXML).hexdigest()
	
	if oXML.tag != 'Extruct':
		raise ParseError("The root element of the XML must be <Extruct>, not: %s" % oXML.tag)
	
	RVAL = []

	for oElement in oXML:
		oSpec = Spec(oElement)
		oSpec.Checksum = sSum
		RVAL.append(oSpec)
	
	return RVAL


###################################################################################################
def ParseOne(sXML):
	
	oXML = ElementTree.fromstring(sXML)
	
	oSpec = Spec(oXML)
	oSpec.Checksum = hashlib.sha1(sXML).hexdigest()
	
	return oSpec

###################################################################################################
def ParseFile(sPath):
	try:
		return Parse(open(sPath, 'r').read())
	except Exception, e:
		raise ParseError("%s encountered while parsing '%s': %s" % (e.__class__.__name__, sPath, e.message))


###################################################################################################
def ParseFileForNames(sPath):
	
	try:
		oXML = ElementTree.parse(sPath).getroot()

		if oXML.tag != 'Extruct':
			raise ValueError("The root element of the XML must be <Extruct>, not: %s" % oXML.tag)

		RVAL = []
		for node in oXML:
			RVAL.append(node.attrib['Name'])

		return RVAL
	
	except Exception, e:
		raise ParseError("%s encountered while parsing '%s': %s" % (e.__class__.__name__, sPath, e.message))


###################################################################################################
###################################################################################################
class _SpecError(Exception):
	"""
	The internal representation of a Spec parsing error
	"""
	
	# A stack representing the position in the Struct
	Stack = None
	
	def __init__(self, Message, Attribute=None):
		self.Stack = [] 
		
		if Attribute != None:
			self.Stack.append("Attrib:%s" % Attribute)

		Exception.__init__(self, Message)

	def InsertStack(self, oElement):
		self.Stack.insert(0, "%s:%s" % (oElement.tag, oElement.attrib['Name'] if 'Name' in oElement.attrib else '?'))

###################################################################################################

class SpecError(Exception):
	"""
	The public exception class of Spec parsing errors.
	"""
	
	Stack = None

	def __init__(self, oError):
		"""
		Takes a _SpecError instance as its only parameter.  Not to be used externally.
		"""
		
		if not isinstance(oError, _SpecError):
			raise TypeError("Invalid type '%s' passed to constructor." % type(oError))

		self.Stack = tuple(oError.Stack)

		Exception.__init__(self, "%s (/%s)" % (oError.message, str.join("/", self.Stack)))
		

###################################################################################################

class BaseNode(object):
	"""
	Base class for all nodes on this Spec.

	- BaseNode
		- ScalarNode 
			- NoneNode
			- BoolNode
			- IntNode
			- FloatNode
			- DecimalNode
			- StringNode
			- UnicodeNode
			- BinaryNode
			- VectorNode
			- ListNode
			- DictNode
			- StructNode
	"""

	# STATIC: This must be overridden on base classes.

	Type 		= None
	Name 		= None

	Nullable 	= False
	
	# Despite the fact that only scalars can have defaults, we are relying 
	# on always having a Default attribute available, so it is defaulted here.
	Default 	= None

	#==============================================================================================
	def __init__(self, oSpec, oElement):
		
		try:
			self.Name = oElement.attrib['Name']
				
			if 'Nullable' in oElement.attrib:
	
				if oElement.attrib['Nullable'] == '1':
					self.Nullable = True

				elif oElement.attrib['Nullable'] == '0':
					self.Nullable = False

				else:
					raise _SpecError("Nullable attribute must be either '1' or '0'")				
			
		except KeyError:
			raise _SpecError("Attribute 'Name' is missing.")
		
		if not REGEX_NODE_NAME.match(self.Name):
			raise _SpecError("Attribute 'Name' is not valid: %s" % self.Name)
						
		
	#=============================================================================================
	def VarDump(self, Indent=0, NoEnd=False):
		ending = "" if NoEnd else "\n"
		
		print "%s[%s] Property at (%s) %s%s" % ("    "*Indent, self.Name, self.__class__.__name__, "" if not self.Nullable else "Nullable", ending),
	
###################################################################################################
class ScalarNode(BaseNode):
	

	#==============================================================================================
	def __init__(self, oSpec, oElement):
		BaseNode.__init__(self, oSpec, oElement)
	
		if 'Default' in oElement.attrib:
			self.Default = oElement.attrib['Default']
	
		if len(oElement) > 0:
			raise _SpecError("Element must have 0 children elements.")


###################################################################################################
class NoneNode(ScalarNode):
	Type = 'None'

###################################################################################################
class BoolNode(ScalarNode):
	Type = 'Bool'

###################################################################################################
class IntNode(ScalarNode):
	Type = 'Int'

###################################################################################################
class FloatNode(ScalarNode):
	Type = 'Float'

###################################################################################################
class DecimalNode(ScalarNode):
	Type = 'Decimal'

###################################################################################################
class StringNode(ScalarNode):
	Type = 'String'
	
	# The maximum allowable length of a string
	MaxLength = None

	#=============================================================================================
	def __init__(self, oSpec, oElement):
		ScalarNode.__init__(self, oSpec, oElement)

		try:
			if 'MaxLength' in oElement.attrib:
				self.MaxLength = int(oElement.attrib['MaxLength'])

		except Exception, e:
			raise _SpecError(e.message, 'MaxLength')
	
	#=============================================================================================
	def VarDump(self, Indent=0):
		ScalarNode.VarDump(self, Indent, NoEnd=True)
		if self.MaxLength:
			print "MaxLength=%s" % self.MaxLength
		else:
			print ""

###################################################################################################
class UnicodeNode(ScalarNode):
	Type = 'Unicode'

###################################################################################################
class BinaryNode(ScalarNode):
	Type = 'Binary'

###################################################################################################
class VectorNode(BaseNode):
	pass

###################################################################################################
class ListNode(VectorNode):
	Type = 'List'
	
	Value = None
	
	#==============================================================================================
	def __init__(self, oSpec, oElement):
		VectorNode.__init__(self, oSpec, oElement)

		if len(oElement) != 1:
			raise _SpecError("Vector element must have exactly 1 child element.")

		self.Value = oSpec.MakeNode(oElement[0])

	#=============================================================================================
	def VarDump(self, Indent=0):
		VectorNode.VarDump(self, Indent)
		self.Value.VarDump(Indent+1)


###################################################################################################
class DictNode(VectorNode):
	Type = 'Dict'
	
	Key = None
	Value = None
	
	#==============================================================================================
	def __init__(self, oSpec, oElement):
		VectorNode.__init__(self, oSpec, oElement)

		if len(oElement) != 2:
			raise _SpecError("Vector element must have exactly 2 child elements.")

		if oElement[0].tag not in ('Int', 'String', 'Unicode'):
			raise _SpecError("Element key type is invalid: <%s>" % oElement[0].tag)

		self.Key = oSpec.MakeNode(oElement[0])
		self.Value = oSpec.MakeNode(oElement[1])

	#=============================================================================================
	def VarDump(self, Indent=0):
		VectorNode.VarDump(self, Indent)
		self.Key.VarDump(Indent+1)
		self.Value.VarDump(Indent+1)


###################################################################################################
class StructNode(VectorNode):
	Type = 'Struct'
	
	Prop = None
	
	
	#==============================================================================================
	def __init__(self, oSpec, oElement):
		VectorNode.__init__(self, oSpec, oElement)

		self.Prop = []
		
		for element in oElement:
			self.Prop.append(oSpec.MakeNode(element))
			
	#=============================================================================================
	def VarDump(self, Indent=0):
		VectorNode.VarDump(self, Indent)

		for o in self.Prop:
			o.VarDump(Indent+1)

###################################################################################################


class Spec(object):
	
	# STATIC mapping of all Node tags to Node classes
	TagMap = {
		'None'		: NoneNode,
		'Bool'		: BoolNode,
		'Int'		: IntNode,
		'Float'		: FloatNode,
		'Decimal'	: DecimalNode,
		'String'	: StringNode,
		'Unicode'	: UnicodeNode,
		'Binary'	: BinaryNode,
		'List'		: ListNode,
		'Dict'		: DictNode,
		'Struct'	: StructNode,
	}


	# A list of Property nodes for this Spec
	Prop = None

	# The unique ID of this spec
	Name = None

	# The SHA1 of the text XML input
	# This is set externally.
	Checksum = "NO-CHECKSUM"

	#==============================================================================================
	def __init__(self, oElement, Checksum=None):
		"""
		Either pass a valid xml.etree.ElementTree.Element that represents the <Node> tag, or a 
		string containing valid <Node> xml (none other).
		"""

		#------------------------------------------------------------------------------------------
		if not ElementTree.iselement(oElement):
			raise TypeError("Invalid type '%s' passed to constructor." % type(XML))


		#------------------------------------------------------------------------------------------
		try:
			if oElement.tag != 'Struct':
				raise _SpecError("Invalid tag passed to constructor: <%s>" % oElement.tag)

			try:
				self.Name = oElement.attrib['Name']
			except KeyError:
				self.Name = PrivateSpecName

			if not REGEX_SPEC_NAME.match(self.Name):
				raise _SpecError("Attribute 'Name' is not valid: %s" % self.Name)
				
			self.Prop = []
			
			for element in oElement:
				self.Prop.append(self.MakeNode(element))
		
		except _SpecError, e:
			if Debug: raise
			# Convert an internal _SpecError into a public SpecError
			e.InsertStack(oElement)
			raise SpecError(e)
	
	#==============================================================================================
	def Convert(self, DATA, ConversionType="Native>>Native"):
		if ConversionType == 'Native>>Native':
			return NativeToNative_Convertor(self).Convert(DATA)
		elif ConversionType == 'Native>>Stream':
			return NativeToStream_Convertor(self).Convert(DATA)
		elif ConversionType == 'Stream>>Native':
			return StreamToNative_Convertor(self).Convert(DATA)
		elif ConversionType == 'Native>>XML':
			from .XML import NativeToXML_Convertor
			return NativeToXML_Convertor(self).Convert(DATA) 
		elif ConversionType == 'XML>>Native':
			from .XML import XMLToNative_Convertor
			return XMLToNative_Convertor(self).Convert(DATA)
		else:
			raise ValueError("Invalid value for ConversionType: %s" % str(ConversionType))


	#==============================================================================================
	def MakeNode(self, oElement):
		"""
		Rather like the super constructor of all nodes.
		"""
		
		try:
			try:
				return self.TagMap[oElement.tag](self, oElement)
			except KeyError:
				raise _SpecError('Encountered invalid tag: <%s>.' % oElement.tag)

		except _SpecError, e:
			e.InsertStack(oElement)
			raise
		
		except Exception, e:
			if Debug: raise
			raise _SpecError(e.message)
		
		
	#==============================================================================================
	def VarDump(self):
	 	print	
		print '   %s Data Specification' % self.Name
		print 
		for o in self.Prop:
			o.VarDump(2)

###################################################################################################
class _ConversionError(Exception):
	"""
	This class represents the internal error stack of an error found while performing a conversion
	"""

	Stack = None
	Node = None
	Value = None
	
	def __init__(self, oNode, eValue, sError):
		
		self.Node = oNode
		self.Value = eValue
		self.Stack = [oNode.Name]

		Exception.__init__(self, sError)

	def InsertStack(self, oNode, Key=None):
		"""
		Call this to insert a stack element on to the beginning of the stack.
		"""
		
		if Key == None:
			self.Stack.insert(0, oNode.Name)
		else:
			Key = str(Key)
			if len(Key) > 20: Key = Key[:20] + "..."
			self.Stack.insert(0, "%s[%s]" % (oNode.Name, Key)) 


###################################################################################################
class ConversionError(Exception):
	"""
	This class is the public face of Convertor object errors.  It is derived from a _ConversionError
	instance.
	"""

	Stack = None
	Value = None
	
	def __init__(self, oError):
		"""
		Takes a _ConversionError instance as its only parameter.  Not to be used externally.
		"""
		
		if not isinstance(oError, _ConversionError):
			raise TypeError("Invalid type '%s' passed to constructor." % type(oError))

		self.Stack = tuple(oError.Stack)
		self.Value = oError.Value

		Exception.__init__(self, "%s (/%s)" % (oError.message, str.join("/", self.Stack)))

###################################################################################################
class NativeToNative_Convertor(object):

	Spec = None

	#==============================================================================================
	def __init__(self, eSpec):
		# We are dealing directly with a spec
		if not isinstance(eSpec, Spec):
			raise TypeError("Parameter 1 must be an instance of %s." % Spec)
		
		self.Spec = eSpec

	#==============================================================================================
	def Convert(self, DATA):
		try:
			return self._Struct(self.Spec, DATA)
		except _ConversionError, e:
			if Debug: raise
			raise ConversionError(e)
	
	#==============================================================================================
	def _Bool(self, oNode, DATA):
		try:
			return bool(DATA)
		except Exception, e:
			raise _ConversionError(oNode, DATA, e.message)

	#==============================================================================================
	def _Int(self, oNode, DATA):
		try:
			return int(DATA)
		except Exception, e:
			raise _ConversionError(oNode, DATA, e.message)

	#==============================================================================================
	def _Float(self, oNode, DATA):
		try:
			return float(DATA)
		except Exception, e:
			raise _ConversionError(oNode, DATA, e.message)

	#==============================================================================================
	def _Decimal(self, oNode, DATA):
		try:
			# Cannot convert float to Decimal. First convert the float to a string.
			if isinstance(DATA, float):
				return Decimal(str(DATA))
			else:
				return Decimal(DATA)
		except Exception, e:
			raise _ConversionError(oNode, DATA, e.message)

	#==============================================================================================
	def _String(self, oNode, DATA):
		try:
			DATA = str(DATA)
		except Exception, e:
			raise _ConversionError(oNode, DATA, e.message)
	
		if oNode.MaxLength and len(DATA) > oNode.MaxLength:
			raise _ConversionError(oNode, DATA, "String length exceeded maximum of %s bytes." % oNode.MaxLength)
		
		return DATA
	
	#==============================================================================================
	def _Unicode(self, oNode, DATA):
		try:
			return unicode(DATA)
		except Exception, e:
			raise _ConversionError(oNode, DATA, e.message)

	#==============================================================================================
	def _Binary(self, oNode, DATA):
		try:
			return str(DATA)
		except Exception, e:
			raise _ConversionError(oNode, DATA, e.message)

	#==============================================================================================
	def _List(self, oNode, DATA):
		try:
			oValueNode = oNode.Value
			oValueFunc = getattr(self, "_"+oValueNode.Type)
			
			RVAL = []
			
			# Handle the special array type
			if isinstance(DATA, Array):
				DATA = DATA.L
			
			i = 0
			for value in DATA:
				i += 1
				RVAL.append(oValueFunc(oValueNode, value))

			return RVAL
		
		except _ConversionError, e:
			e.InsertStack(oNode, i)
			raise

		except Exception, e:
			if Debug: raise
			raise _ConversionError(oNode, DATA, "%s: %s" % (e.__class__.__name__, e.message))

	
	#==============================================================================================
	def _Dict(self, oNode, DATA):
		try:
			oKeyNode = oNode.Key
			
			oKeyFunc = getattr(self, "_"+oKeyNode.Type)

			oValueNode = oNode.Value
			oValueFunc = getattr(self, "_"+oValueNode.Type)
			
			RVAL = {}
			
			# Handle the special array type
			if isinstance(DATA, Array):
				DATA = DATA.D

			for key in DATA:
				value = DATA[key]
				
				# New key, value
				key = oKeyFunc(oKeyNode, key)
				RVAL[key] = oValueFunc(oValueNode, value)

			return RVAL

		except _ConversionError, e:
			e.InsertStack(oNode, key)
			raise

		except Exception, e:
			if Debug: raise
			raise _ConversionError(oNode, DATA, "%s: %s" % (e.__class__.__name__, e.message))

	#==============================================================================================
	def _Struct(self, oNode, DATA):
		try:
				
			RVAL = {}
		
			# Handle the special array type
			if isinstance(DATA, Array):
				DATA = DATA.D

			for oPropNode in oNode.Prop:
				oFunc = getattr(self, "_"+oPropNode.Type)
				
				try:
					value = DATA[oPropNode.Name]
				
				except KeyError, e:
					value = oPropNode.Default
					
				if value == None:
					if not oPropNode.Nullable:
						raise KeyError("[%s] must be set, Nullable or Defaulted" % oPropNode.Name)
					else:
						RVAL[oPropNode.Name] = None
				else:
					RVAL[oPropNode.Name] = oFunc(oPropNode, value)
				
							
			return RVAL
		
		except _ConversionError, e:
			e.InsertStack(oNode)
			raise

		except Exception, e:
			if Debug: raise
			raise _ConversionError(oNode, DATA, "%s: %s" % (e.__class__.__name__, e.message))

###################################################################################################
class NativeToStream_Convertor(NativeToNative_Convertor):
	
	DELIMITER = "|"
	Stream = None
	
	#==============================================================================================
	def Convert(self, DATA):
		"""
		DATA is a python dictionary.  
		Returns a string of "|" delimited tokens
		"""
		self.Stream = [self.Spec.Checksum]
		NativeToNative_Convertor.Convert(self, DATA)
		return str.join(self.DELIMITER, self.Stream)


	#==============================================================================================
	def _Bool(self, oNode, DATA):
		DATA = NativeToNative_Convertor._Int(self, oNode, DATA)
		self.Stream.append(str(DATA))

	#==============================================================================================
	def _Int(self, oNode, DATA):
		DATA = NativeToNative_Convertor._Int(self, oNode, DATA)
		self.Stream.append(str(DATA))

	#==============================================================================================
	def _Float(self, oNode, DATA):
		DATA = NativeToNative_Convertor._Float(self, oNode, DATA)
		self.Stream.append(str(DATA))

	#==============================================================================================
	def _Decimal(self, oNode, DATA):
		DATA = NativeToNative_Convertor._Decimal(self, oNode, DATA)
		self.Stream.append(str(DATA))

	#==============================================================================================
	def _String(self, oNode, DATA):
		DATA = NativeToNative_Convertor._String(self, oNode, DATA)
		self.Stream.append(DATA.encode('base_64')[:-1])
	
	#==============================================================================================
	def _Unicode(self, oNode, DATA):
		raise _ConversionError(oNode, DATA, "Unsupported data type %s" % type(DATA))

	#==============================================================================================
	def _Binary(self, oNode, DATA):
		DATA = NativeToNative_Convertor._Binary(self, oNode, DATA)
		self.Stream.append(DATA.encode('base_64'))

	#==============================================================================================
	def _List(self, oNode, DATA):
		self.Stream.append('<List>')
		NativeToNative_Convertor._List(self, oNode, DATA)
		self.Stream.append('</List>')

	#==============================================================================================
	def _Dict(self, oNode, DATA):
		self.Stream.append('<Dict>')
		NativeToNative_Convertor._Dict(self, oNode, DATA)
		self.Stream.append('</Dict>')
	
	#==============================================================================================
	def _Struct(self, oNode, DATA):
		self.Stream.append('<Struct>')
		NativeToNative_Convertor._Struct(self, oNode, DATA)
		self.Stream.append('</Struct>')



###################################################################################################
class StreamToNative_Convertor(NativeToNative_Convertor):
	
	DELIMITER = "|"
	Stream = None
	
	#==============================================================================================
	def Convert(self, DATA):
		"""
		This time, data is a "|" delimited string of tokens
		Returns a python object (hopefully)
		"""
		self.Stream = (token for token in DATA.split(self.DELIMITER))
		
		# Read in the checksum
		Checksum = self.Stream.next()
		if self.Spec.Checksum != Checksum:
			raise ValueError("Stream checksum '%s' does not match spec checksum '%s' for spec '%s'." % (Checksum, self.Spec.Checksum, self.Spec.Name))

		# Obtain the first token...
		DATA = self.Stream.next()
	
		return NativeToNative_Convertor.Convert(self, DATA)

	#==============================================================================================
	def _String(self, oNode, DATA):
		return NativeToNative_Convertor._String(self, oNode, DATA.decode('base_64'))
		#return NativeToNative_Convertor._String(self, oNode, DATA)
	
	#==============================================================================================
	def _List(self, oNode, DATA):
		"""
		DATA RECEIVED will be a start token.
		"""
		try:
			if DATA != '<List>':
				raise Exception("List not starting with a <List> token.");
			
			oValueNode = oNode.Value
			oValueFunc = getattr(self, "_"+oValueNode.Type)
			
			RVAL = []
			i = 0
			while True:
				value = self.Stream.next()
				if value == '</List>':
					break

				i += 1
				RVAL.append(oValueFunc(oValueNode, value))

			return RVAL
		
		except _ConversionError, e:
			e.InsertStack(oNode, i)
			raise

		except Exception, e:
			if Debug: raise
			raise _ConversionError(oNode, DATA, "%s: %s" % (e.__class__.__name__, e.message))

	
	#==============================================================================================
	def _Dict(self, oNode, DATA):
		"""
		DATA RECEIVED will be a start token.
		"""
		try:
			if DATA != '<Dict>':
				raise Exception("Dict not starting with a <Dict> token.");
			
			oKeyNode = oNode.Key
			
			oKeyFunc = getattr(self, "_"+oKeyNode.Type)

			oValueNode = oNode.Value
			oValueFunc = getattr(self, "_"+oValueNode.Type)
			
			RVAL = {}

			while True:
				key = self.Stream.next()
				if key == '</Dict>':
					break
				value = self.Stream.next()
				
				# New key, value
				key = oKeyFunc(oKeyNode, key)
				RVAL[key] = oValueFunc(oValueNode, value)

			return RVAL

		except _ConversionError, e:
			e.InsertStack(oNode, key)
			raise

		except Exception, e:
			if Debug: raise
			raise _ConversionError(oNode, DATA, "%s: %s" % (e.__class__.__name__, e.message))

	#==============================================================================================
	def _Struct(self, oNode, DATA):
		"""
		DATA RECEIVED will be a start token.
		"""
		try:
			if DATA != '<Struct>':
				raise Exception("Struct not starting with a <Struct> token.");
			
			RVAL = {}
		
			for oPropNode in oNode.Prop:
				oFunc = getattr(self, "_"+oPropNode.Type)
				
				value = self.Stream.next()
				
				RVAL[oPropNode.Name] = oFunc(oPropNode, value)
			
			# Discard the final '</Struct>' at the end of the struct.
			self.Stream.next()
			
			return RVAL

		except _ConversionError, e:
			e.InsertStack(oNode)
			raise

		except Exception, e:
			if Debug: raise
			raise _ConversionError(oNode, DATA, "%s: %s" % (e.__class__.__name__, e.message))

	
###################################################################################################



class Serialize(object):
	"""
	Stream Format a simple token stream.

	Stream:
		start-token | (scalar or vectors ...) | end-token

	Scalar:
		name | type | value

	Scalar (None):
		name | type
	
	List:
		name | type | [ | [type | value [| ...]] | ]
	
	Tuple:
		name | type | ( | [type | value [| ...]] | )
	
	Dict/Map/Array:
		name | type | { | [type | key | type | value [| ...]] | }

	N : Null
	B : Bool
	I : Int
	F : Float
	D : Decimal
	S : String
	L : List
	T : Tuple
	M : Dict/Map

	"""
	
	VERSION = 1
	
	STREAM_START = '[[%i' % VERSION
	STREAM_END = ']]'
	
	
	def __new__(cls, DATA):
		self = object.__new__(cls)
		TokenList = []
		self.add = TokenList.append
		
		self.add(self.STREAM_START)
		self.Value(DATA)
		self.add(self.STREAM_END)
		
		return str.join("|", TokenList)

	def Value(self, DATA):
		try:
			self.Map[type(DATA)](self, DATA)
		except KeyError:
			raise TypeError("No type conversion defined for Type %s (value=%s)" % (type(DATA), str(DATA)))

	# For all of the following functions, assume that the name has already been appended
	
	def _NoneType(self, DATA):
		self.add('N')
	
	def _BooleanType(self, DATA):
		self.add('B')
		self.add('1' if DATA else '0')

	def _IntType(self, DATA):
		self.add('I')
		self.add(str(DATA))

	def _FloatType(self, DATA):
		self.add('F')
		self.add(str(DATA))

	def _DecimalType(self, DATA):
		self.add('D')
		self.add(str(DATA))

	def _StringType(self, DATA):
		self.add('S')
		self.add(DATA.encode('base_64').rstrip())
	
	def _ListType(self, DATA):
		self.add('L')
		self.add('[')

		for v in DATA: 
			self.Value(v)
		
		self.add(']')

	def _TupleType(self, DATA):
		self.add('T')
		self.add('(')

		for v in DATA: 
			self.Value(v)
		
		self.add(')')

	def _DictType(self, DATA):
		self.add('M')
		self.add('{')
		for k in DATA:
			if not isinstance(k, (StringType, IntType)):
				raise TypeError("Dictionary keys must be String or Int, not: %s" % type(k))
				
			self.Value(k)
			self.Value(DATA[k])
		
		self.add('}')
		
	Map = {
		NoneType	: _NoneType,
		BooleanType	: _BooleanType,
		IntType		: _IntType,
		FloatType	: _FloatType,
		DecimalType : _DecimalType,
		StringType	: _StringType,
		TupleType	: _TupleType,
		ListType	: _ListType,
		DictType	: _DictType,
		}
	

###################################################################################################
class Unserialize(object):
	
	VERSION = 1
	
	STREAM_START = '[[%i' % VERSION
	STREAM_END = ']]'
	
	
	def __new__(cls, STREAM):
		self = object.__new__(cls)
		TokenList = STREAM.split('|')
	
		if TokenList.pop().rstrip() != self.STREAM_END:
			raise ValueError("Unknown stream end token")
		
		self.next = iter(TokenList).next

		if self.next().lstrip() != self.STREAM_START:
			raise ValueError("Unknown stream start token")

		# Call the Value Function with the first datatype encountered
		return self.Value(self.next())

	
	def Value(self, DATATYPE):
		try:
			return self.Map[DATATYPE](self)
		except KeyError:
			raise TypeError("No type conversion defined for Type %s (value=%s)" % (type(DATA), str(DATA)))

	# For all of the following functions, they need to read thier value; their type has already been read
	
	def _NoneType(self):
		return None
	
	def _BooleanType(self):
		return False if self.next() == '0' else True

	def _IntType(self):
		return IntType(self.next())

	def _FloatType(self):
		return FloatType(self.next())

	def _DecimalType(self):
		return DecimalType(self.next())

	def _StringType(self):
		return self.next().decode('base_64')
	
	def _ListType(self):
		if self.next() != '[':
			raise ValueError("Invalid list start token.")
		
		RVAL = []

		while True:
			t = self.next()
			if t == ']':
				break

			RVAL.append(self.Value(t))

		return RVAL


	def _TupleType(self):
		if self.next() != '(':
			raise ValueError("Invalid tuple start token.")
		
		RVAL = []

		while True:
			t = self.next()
			if t == ')':
				break

			RVAL.append(self.Value(t))

		return TupleType(RVAL)

	def _DictType(self):
		if self.next() != '{':
			raise ValueError("Invalid dict start token.")
		
		RVAL = {}

		while True:
			kt = self.next()
			if kt == '}':
				break

			if kt not in ('I', 'S'):
				raise ValueError("Dictionary keys must be String or Int, not: %s" % kt)

			# The key should be string or int
			key = self.Value(kt)
			
			# Get the value type -> pass it to Value() -> Assign to dict
			RVAL[key] = self.Value(self.next())

		return RVAL
		
	def _ArrayType(self):
		if self.next() != '{':
			raise ValueError("Invalid array start token.")
		
		RVAL = Array()

		while True:
			kt = self.next()
			if kt == '}':
				break

			if kt not in ('I', 'S'):
				raise ValueError("Dictionary keys must be String or Int, not: %s" % kt)

			# The key should be string or int
			key = self.Value(kt)
			
			# Get the value type -> pass it to Value() -> Assign to dict
			RVAL[key] = self.Value(self.next())

		return RVAL
	
	Map = {
		'N'	: _NoneType,
		'B'	: _BooleanType,
		'I'	: _IntType,
		'F'	: _FloatType,
		'D'	: _DecimalType,
		'S'	: _StringType,
		'T'	: _TupleType,
		'L'	: _ListType,
		'M'	: _DictType,
		'A' : _ArrayType,
		}
	




