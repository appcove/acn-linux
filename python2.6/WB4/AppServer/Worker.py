
import os
import signal
import socket
import sys
import traceback
from time import time, sleep

import Extruct
from WB4.AppServer import FunctionCallException
from WB4.AppServer.Packet import RequestPacket, ResponsePacket, ExceptionPacket, ParsePacket, PacketError
from WB4.Network.Connection import BlockingPacketConnection, ConnectionLost


###################################################################################################
class StopLoop(Exception):
	pass

###################################################################################################

# Setup sig handlers
signal.signal(signal.SIGINT, signal.SIG_IGN)

###################################################################################################

class WorkerConnection(BlockingPacketConnection):
	PacketDelimiter = "\0"
	
	#==========================================================================
	def __init__(self, sInstancePath, sProjectIdentifier, nConnectionID, nSocketFD):

		# Instance variables
		self.ID 				= nConnectionID
		self.Running 			= False
		self.CurrentPacket 		= None
		self.App 				= None


		# Load up WB4 with the path specified
		import WB4
		WB4.Load(sInstancePath)
		import WB4.Project
		
		# Import the project, and get a handle to the project's app object
		__import__('WB4.Project.%s' % sProjectIdentifier)
		self.App = getattr(WB4.Project, sProjectIdentifier).App
		
		# Set the AS attribute of the App object
		self.App.AS = self

		# Create a new socket object from the passed socket
		conn = socket.fromfd(nSocketFD, socket.AF_UNIX, socket.SOCK_STREAM)
		addr = ("FD-%i" % nSocketFD, "from-exec")
			
		# Close the original FD if it is not the same as the new socket object's fd 
		if nSocketFD != conn.fileno():
			os.close(nSocketFD)

		# Call base class constructor
		BlockingPacketConnection.__init__(self, conn, addr)
	
	#==========================================================================
	def __repr__(self):
		return "<Worker #%i>" % self.ID

	#==========================================================================
	def SendPacket(self, oPacket):
		sPacket = oPacket.ToString()
		if DE:BUG(5, "WORKER Sending Packet packet on %s: \n%s" % (self, sPacket))
		BlockingPacketConnection.SendPacket(self, sPacket)

	#==========================================================================
	def RecvPacket(self):
		sPacket = BlockingPacketConnection.RecvPacket(self)
		if DE:BUG(5, "WORKER Received Packet packet on %s: \n%s" % (self, sPacket))
		return ParsePacket(sPacket)
		
	#==========================================================================
	def Loop(self):
		"""
		The main event loop.  Can be stopped by calling the Halt method.
		"""
		
		self.Running = True
		
		while self.Running:
			try:
				# 1. Receive a packet
				oPacket = self.RecvPacket()

				# 2. Process it
				self.HandlePacket(oPacket)

			except StopLoop, e:
				if DE:BUG(3, "Worker %s StopLoop: %s" % (self, e.message))
				return
			
			except ConnectionLost, e:
				if DE:BUG(3, "Worker %s Connection Lost: %s" % (self, e.message))
				return

			except Exception, e:
				print
				print
				print "Worker %s DIED UNEXPECTEDLY:" % self
				traceback.print_exc()
				print
				print

				return

				

	#==========================================================================
	def Halt(self):
		"""Stops the main event loop on it's next iteration."""
		self.Running = False

	#==========================================================================
	def HandlePacket(self, oPacketI):
		
		try:
			
			# Handle Function Request packets
			if oPacketI.Type != 'Request':
				raise InvalidOperation("It is illegal to send a worker a packet of type '%s'." % oPacketI.Type)
				
			# Sanity check
			if oPacketI.Target != self.App.Identifier:
				raise InvalidOperation("A packet with Target='%s' may not be sent to a worker with App.Identifier='%s'." % (oPacketI.Target, self.App.Identifier))
			
			try:
				self.App.LoadSecurityContext(oPacketI.SecurityContext, oPacketI.ADDR)
			
				# Call the API
				DATA = self.App.CallAPI(oPacketI.Method, oPacketI.Data, Target='<SELF>')

			finally:
				self.App.FreeSecurityContext()


			# Create the response packet (clone core fields off of the incoming packet)
			oPacketO = ResponsePacket()
			oPacketO.DataType = oPacketI.DataType
			oPacketO.Data = DATA

			# Send the response
			self.SendPacket(oPacketO)

		except Exception, e:
			
			# Print exception
			print; traceback.print_exc(); print
			
			# Format message:
			if DE:BUG(3, "Worker %s received %s: \n%s" % (self, type(e).__name__, e.message))
			
			# Create an exception response packet
			oPacketO = ExceptionPacket()
			if hasattr(e, 'Data'):
				oPacketO.Data = e.Data				
			oPacketO.ExceptionType = type(e).__name__
			oPacketO.Message = e.message

			self.SendPacket(oPacketO)

		
	#==========================================================================
	def CallAPI(self, Method, DATA, Target):
		# Form the request packet
		oPacketO = RequestPacket();
		oPacketO.DevLevel			= self.App.DevLevel
		oPacketO.DevName			= self.App.DevName
		oPacketO.ProjectIdentifier	= self.App.Identifier
		oPacketO.DSEG				= self.App.SecurityContext.DSEG
		oPacketO.ADDR				= self.App.SecurityContext.ADDR
		oPacketO.AuthToken			= None #TODO
		oPacketO.Target				= Target
		oPacketO.Method				= Method
		oPacketO.DataType 			= 'BinaryPickle'
		oPacketO.Data				= DATA
	
		self.SendPacket(oPacketO)
		oPacketI = self.RecvPacket()

		if oPacketI.Type == 'Response':
			return oPacketI.Data

		elif oPacketI.Type == 'Exception':
			raise FunctionCallException("Exception received during ModuleAPI call: %s: %s" % (oPacketI.ExceptionType, oPacketI.Message))
		
		else:
			raise Exception("Can't handle response packet of type '%s'." % oPacketI.Type)

	
	#==========================================================================
	def Authenticated(self, Duration):
		"""
		This method informs the Application Server that the client in question
		has been authenticated.  In other words, 
		
		"hey server, remember this security context, and give me a token to 
		refer to it by."

		Also, we have the opportunity to pass a Duration, which will cause
		the AppServer to set the expiration date of this security context
		to (time() + duration) each time it is "hit".

		This method should only be called as part of an authentication
		mechanism.  Rather like this:

		1. Validate username/password
		2. Get UUID
		3. App.SwapSecurityContext(Realm, Type, UUID)
		4. AuthToken = App.AS.Authenticated(Duration)
		5. Send auth token back to client to be saved in a cookie or something
		
		"""

		DATA = {
			'SecurityContext': self.App.SecurityContext.ToString(),
			'Duration': Duration,
			}
			
		RVAL = self.App.CallAPI('Authenticated', DATA, Target='<SERVER>')

		return RVAL['AuthToken']
		










	


