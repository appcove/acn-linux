
	
class ConnectionLost(Exception):
	pass


###################################################################################################
class BlockingPacketConnection(object):

	# Class variables
	PacketDelimiter = "\r\n"  #for telnet
	BufSize = 4096
	
	# Instance variables
	Address = None
	
	_Socket = None
	_RecvBuffer = ''

	#==========================================================================
	def __init__(self, sock, addr):
		
		# Address of the connection
		self.Address = addr
		
		# The actual socket
		self._Socket 			= sock
		
	
	#==============================================================================================
	def SendPacket(self, data):
		"""
		Sends the data until it is all sent.
		"""
		
		if data.find(self.PacketDelimiter) != -1:
			raise ValueError("The packet being queued must not contain the PacketDelimiter.")

		data += self.PacketDelimiter

		while len(data):
			bytes = self._Socket.send(data)
			data = data[bytes:]

		return


	#==========================================================================
	def RecvPacket(self):
		
		while True:
			
			pos = self._RecvBuffer.find(self.PacketDelimiter)

			if pos >= 0:
				packet = self._RecvBuffer[0:pos]
				self._RecvBuffer = self._RecvBuffer[pos+len(self.PacketDelimiter):]
				return packet

			data = self._Socket.recv(self.BufSize)

			if data == '':
				self._Socket.close()
				raise ConnectionLost("Socket closed due to zero length read.")

			self._RecvBuffer += data

	
	#==========================================================================
	def Close(self, sReason='No Reason Given'):

		# Close the listening socket
		self._Socket.close()


