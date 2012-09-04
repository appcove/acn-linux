"""
WB4 Application Server Packet Definition:



Three types of packets:
1. Request
2. Response
3. Exception

Each packet type has a different set of fields.


All packets contain:
	
	CORE fields set on packet creation:
		Version				= 1
		Type 				= 'Request' | 'Response' | 'Exception'

	Fields common to all packets
		DataType			= 'Native' | 'BinaryString' | 'BinaryPickle' | 'ExtructSerialize'
		Data				= (as per DataType)


Request Packet:
	
	Set by Client/Worker:
		DevLevel			= [0-9] The DevLevel of the client
		DevName				= (string) The DevName of the client
		ProjectIdentifier	= The ProjectIdentifier of the client
		DSEG				= The int DSEG of the client
		ADDR		= IP address of the original requestor, if possible
		AuthToken			= (string|none) the authentication token that the client sent
		Target				= What Project to send the request to?
		Method				= string (what do you want?)
	
	Set by Server:
		SecurityContext		= (string) the security context of this request

Response Packet:

	<no extra fields>

Exception Packet:

	Set by worker/server:
		ExceptionType		= (string) full class name of exception
		Message				= (base64) string of message of what went wrong


Usage:

	# Create a new RequestPacket (empty)
	oPacket = BuildPacket('Request', 'BinaryPickle')

	# Create a new RequestPacket (cloning core fields from another packet)
	oPacket = BuildPacket('Request', 'BinaryPickle', oOtherPacket)

	# Read a packet off the wire
	oPacket = ParsePacket(stringdata)





"""

import cPickle
import cjson
import Extruct

###################################################################################################
class PacketError(Exception):
	pass


###################################################################################################
def ParsePacket(data):
	try:
		data = cjson.decode(data)
		
		if data['Type'] == 'Request':
			return RequestPacket(data)
		elif data['Type'] == 'Response':
			return ResponsePacket(data)
		elif data['Type'] == 'Exception':
			return ExceptionPacket(data)
		else:
			raise PacketError("Packet does not have a valid Type: %s" % data['Type'])
	
	except PacketError:
		raise
	
	except cjson.DecodeError, e:
		raise PacketError(e.message)
	
	except KeyError:
		raise PacketError("Packet does not have a valid Type attribute.")
	
	except Exception, e:
		raise PacketError("Unknown error: %s: %s" % (type(e).__name__, e))
		

###################################################################################################




class BasePacket(object):
	_DataType = ('Native', 'BinaryString', 'BinaryPickle', 'ExtructSerialize')
	_Version = 4
	
	#==============================================================================================
	def __init__(self, DATA=None):
		
		self._Data = {'Version': self._Version}
		
		if DATA:
			try:
				if DATA['Version'] != self._Version:
					raise PacketError("Packet version %s does not match class version %s." % (DATA['Version'], self._Version))
				
				self._Data['DataType']	 		= DATA['DataType']
				self._Data['Data'] 				= DATA['Data']

			except KeyError, e:
				raise PacketError("Key missing: %s" % e)
		else:
			self._Data['DataType'] 			= 'Native'
			self._Data['Data']		 		= {}


	#==============================================================================================
	def ToString(self):
		return cjson.encode(self._Data)
	
	#==============================================================================================
	@property
	def Version(self):
		return self._Version
	
	#==============================================================================================
	@property
	def Type(self):
		return self._Data['Type']

	#==============================================================================================
	def DataType_get(self):
		return self._Data['DataType']
	
	def DataType_set(self, value):
		"""Warning!  If the datatype is set, the data value will be truncated."""
		if value not in self._DataType:
			raise ValueError("Invalid DataType: %s" % value)
		self._Data['Data'] = None
		self._Data['DataType'] = value

	DataType = property(DataType_get, DataType_set)

	#==============================================================================================
	def Data_get(self):
		if self._Data['DataType'] == 'Native':
			return self._Data['Data']
		elif self._Data['DataType'] == 'ExtructSerialize':
			return Extruct.Unserialize(self._Data['Data'])
		elif self._Data['DataType'] == 'BinaryString':
			return self._Data['Data'].decode('base_64')
		elif self._Data['DataType'] == 'BinaryPickle':
			return cPickle.loads(self._Data['Data'].decode('base_64'))
		else:
			raise ValueError("PANIC: Invalid value for DataType: %s" % self._Data['DataType'])
	
	def Data_set(self, value):
		if self._Data['DataType'] == 'Native':
			self._Data['Data'] = value
		elif self._Data['DataType'] == 'ExtructSerialize':
			self._Data['Data'] = Extruct.Serialize(value)
		elif self._Data['DataType'] == 'BinaryString':
			self._Data['Data'] = value.encode('base_64')
		elif self._Data['DataType'] == 'BinaryPickle':
			self._Data['Data'] = cPickle.dumps(value, 2).encode('base_64')
		else:
			raise ValueError("PANIC: Invalid value for DataType: %s" % self._Data['DataType'])
	
	Data = property(Data_get, Data_set)
		
	#==============================================================================================




###################################################################################################
class RequestPacket(BasePacket):
	
	#==============================================================================================
	def __init__(self, DATA=None):
		BasePacket.__init__(self, DATA)
		
		self._Data['Type'] = 'Request'

		if DATA:
			try:
				self._Data['DevLevel'] 			= DATA['DevLevel']
				self._Data['DevName'] 			= DATA['DevName']
				self._Data['ProjectIdentifier'] = DATA['ProjectIdentifier']
				self._Data['DSEG'] 				= DATA['DSEG']
				self._Data['ADDR'] 	= DATA['ADDR']
				self._Data['AuthToken'] 		= DATA['AuthToken']
				self._Data['Target'] 			= DATA['Target']
				self._Data['Method'] 			= DATA['Method']
				self._Data['SecurityContext'] 	= DATA['SecurityContext']

			except KeyError, e:
				raise PacketError("Key missing: %s" % e)
		else:
			self._Data['DevLevel'] 			= None
			self._Data['DevName'] 			= None
			self._Data['ProjectIdentifier'] = None
			self._Data['DSEG'] 				= None
			self._Data['ADDR'] 	= None
			self._Data['AuthToken'] 		= None
			self._Data['Target'] 			= None
			self._Data['Method'] 			= None
			self._Data['SecurityContext'] 	= None

	
	#==============================================================================================
	def DevLevel_get(self):
		return self._Data['DevLevel']
	
	def DevLevel_set(self, value):
		self._Data['DevLevel'] = int(value)
		
	DevLevel = property(DevLevel_get, DevLevel_set)
	
	#==============================================================================================
	def DevName_get(self):
		return self._Data['DevName']
	
	def DevName_set(self, value):
		self._Data['DevName'] = value
		
	DevName = property(DevName_get, DevName_set)
	
	#==============================================================================================
	def ProjectIdentifier_get(self):
		return self._Data['ProjectIdentifier']
	
	def ProjectIdentifier_set(self, value):
		self._Data['ProjectIdentifier'] = value
		
	ProjectIdentifier = property(ProjectIdentifier_get, ProjectIdentifier_set)
	
	#==============================================================================================
	# DSEG is ALWAYS an integer

	def DSEG_get(self):
		return int(self._Data['DSEG'])
	
	def DSEG_set(self, value):
		self._Data['DSEG'] = int(value)
		
	DSEG = property(DSEG_get, DSEG_set)
	
	#==============================================================================================
	def ADDR_get(self):
		return self._Data['ADDR']
	
	def ADDR_set(self, value):
		self._Data['ADDR'] = value
		
	ADDR = property(ADDR_get, ADDR_set)
	
	#==============================================================================================
	def AuthToken_get(self):
		return self._Data['AuthToken']
	
	def AuthToken_set(self, value):
		self._Data['AuthToken'] = value
		
	AuthToken = property(AuthToken_get, AuthToken_set)
		
	#==============================================================================================
	def Target_get(self):
		return self._Data['Target']
	
	def Target_set(self, value):
		self._Data['Target'] = value
		
	Target = property(Target_get, Target_set)

	#==============================================================================================
	def Method_get(self):
		return self._Data['Method']
	
	def Method_set(self, value):
		self._Data['Method'] = value
		
	Method = property(Method_get, Method_set)

	#==============================================================================================
	def SecurityContext_get(self):
		return self._Data['SecurityContext']
	
	def SecurityContext_set(self, value):
		self._Data['SecurityContext'] = value
		
	SecurityContext = property(SecurityContext_get, SecurityContext_set)


	#==============================================================================================
	def ExpirationDate_get(self):
		return self._Data['ExpirationDate']
	
	def ExpirationDate_set(self, value):
		self._Data['ExpirationDate'] = value
		
	ExpirationDate = property(ExpirationDate_get, ExpirationDate_set)


	#==============================================================================================
	def RequestCount_get(self):
		return self._Data['RequestCount']
	
	def RequestCount_set(self, value):
		self._Data['RequestCount'] = value
		
	RequestCount = property(RequestCount_get, RequestCount_set)




###################################################################################################

class ResponsePacket(BasePacket):
	
	#==============================================================================================
	def __init__(self, DATA=None):
		BasePacket.__init__(self, DATA)
		self._Data['Type'] = 'Response'



###################################################################################################

class ExceptionPacket(BasePacket):
	
	#==============================================================================================
	def __init__(self, DATA=None):
		BasePacket.__init__(self, DATA)
		self._Data['Type'] = 'Exception'

		if DATA:
			try:
				self._Data['ExceptionType'] 	= DATA['ExceptionType']
				self._Data['Message'] 			= DATA['Message']

			except KeyError, e:
				raise PacketError("Key missing: %s" % e)
		else:
			self._Data['ExceptionType']		= None
			self._Data['Message'] 			= None


	#==============================================================================================
	def ExceptionType_get(self):
		return self._Data['ExceptionType']
	
	def ExceptionType_set(self, value):
		self._Data['ExceptionType'] = value
		
	ExceptionType = property(ExceptionType_get, ExceptionType_set)

	#==============================================================================================
	def Message_get(self):
		return self._Data['Message'].decode('base_64')
	
	def Message_set(self, value):
		self._Data['Message'] = str(value).encode('base_64')
		
	Message = property(Message_get, Message_set)


