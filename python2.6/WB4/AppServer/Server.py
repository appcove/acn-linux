from __future__ import with_statement

import WB4
from WB4.Network.Connection import BlockingPacketConnection, ConnectionLost
from WB4.AppServer.Packet import RequestPacket, ResponsePacket, ExceptionPacket, ParsePacket, PacketError

from xml.etree import cElementTree as ElementTree

import atexit
import sys
import time
import re
import random
import hashlib

import socket
import os
from os import path
import threading
import signal
import fcntl

import traceback


"""

This is the WB4 Application Server.  It is designed to serve the 
applications from a single WB4 instance.

TODO:
1. Startup / shutdown / refresh (ie. signals)
2. mysqld_safe type script
3. init.d
4. Forking from init?
5. Cleanup of auth tokens.  Store them in a database?
6. Worker expiration...



The string representation of a security context is:


	Realm may be <GLOBAL> if it is a shared security context.

		Example: "[SecurityContext:VOS5:Member:123:12345]"
		Example: "[SecurityContext:<GLOBAL>:UserAuth:123:12345]"

	The default security contexts for clients and workers are (respectivly):
	(where 123 is the data segment, and "SomeProject" is the Realm)

		[SecurityContext:<GLOBAL>:WORKER:123:SomeProject]
		[SecurityContext:<GLOBAL>:CLIENT:123:SomeProject]



Notes:
	DevName seems to be a real potential problem...

"""


###############################################################################
# Server defaults
SOCKET_TIMEOUT = 10

# These will be used to verify packets came from the right place...
Run_DevLevel = None
Run_DevName = None

# The current server time (to a resolution of about 1 second)
Run_ServerTime = time.time()

###############################################################################

# Is the server running?
Running = False
Running_Lock = threading.Lock()

# A reference to the ProcessManagerThread object
ProcessManager = None

# A reference to the AuthManagerThread Object
AuthManager = None

# A reference to the ListenerThread object
Listener = None

###############################################################################


def SIGINT(a,b):
	Stop()

def SIGTERM(a,b):
	print "Caught SIGTERM. Stopping..."
	Stop()

# A handler for the interrupt
signal.signal(signal.SIGINT, SIGINT)

# We DO NOT want to have to reap children
signal.signal(signal.SIGCHLD, signal.SIG_IGN)

# Gracefully handle SIGTERM
signal.signal(signal.SIGTERM, SIGTERM)



###############################################################################
def Init(InstancePathList, WorkerPath):
	"""
	Multiple instance paths may be passed into the server.
	Projects are registered in a first-come, first-serve basis.

	If a project is already registered, it will not be overwritten.

	Presently, all projects have to match DevLevel and DevName.

	"""

	if DE:BUG(1, "Initializing Server...")
	
	global ProcessManager, AuthManager, Listener
	global Run_DevLevel
	global Run_DevName
	
	# -------------------------------------------------------------------------
	# Parse out specific data from the PRIMARY Instance.xml file...
		
	PI = WB4.PathInfo(InstancePathList[0])

	# These will be used to verify packets came from the right place...
	Run_DevLevel = PI.DevLevel
	Run_DevName = PI.DevName
	
	oXML = ElementTree.parse(PI.DataFile)

	AS_Type = oXML.find('//AppServer/Type').text
	AS_Address = oXML.find('//AppServer/Address').text
	AS_Port = int(oXML.find('//AppServer/Port').text)
	

	# Now handle each quent Instance.xml file...
	for InstancePath in InstancePathList:
	
		PI = WB4.PathInfo(InstancePath)

		if Run_DevLevel != PI.DevLevel:
			raise Exception("During Server.Init(): A subsequent InstancePath did not match the DevLevel specified on the first instance path: %s" % str(InstancePathList))
		
		if Run_DevName != PI.DevName:
			raise Exception("During Server.Init(): A subsequent InstancePath did not match the DevName specified on the first instance path: %s" % str(InstancePathList))
		
		# These will be used to verify packets came from the right place...
		Run_DevLevel = PI.DevLevel
		Run_DevName = PI.DevName

		if not path.exists(PI.DataFile):
			raise Exception("Instance Data File does not exist: %s" % InstancePath)

		oXML = ElementTree.parse(PI.DataFile)

		InstancePath = oXML.find('//Path').text

		for oProject in oXML.find('//Project-List'):
			
			oModuleName = oProject.find('App/ModuleName')
			
			if oModuleName != None: 
				try:
					Project.Register(InstancePath, PI.DevLevel, PI.DevName, oModuleName.text, WorkerPath)
				except Project.AlreadyRegistered, e:
					if DE:BUG(2, str(e))


	# -------------------------------------------------------------------------
	# Configure the server to start
	
	
	ProcessManager = ProcessManagerThread()
	ProcessManager.start()
	
	AuthManager = AuthManagerThread()
	AuthManager.start()
	
	Listener = ListenerThread(AS_Type, AS_Address, AS_Port)
	Listener.start()



###############################################################################
def Run():
	global Running, Run_ServerTime
	with Running_Lock: Running = True
	
	if DE:BUG(1, "Started Server.")
	
	while Running:
		Run_ServerTime = time.time()
		time.sleep(1.00)

	if DE:BUG(1, "Stopped Server.")



###############################################################################
def Stop():
	if DE:BUG(1, "Stopping Server...")
	global Running
	with Running_Lock: Running = False




###############################################################################
class Project(object):
	
	# This is a Dict of projects keyed by tuples of 
	#   (DevLevel, DevName, ProjectIdentifier) 
	ProjectMap = {}

	class AlreadyRegistered(Exception):
		pass
	
	__slots__ = ('InstancePath', 'DevLevel', 'DevName', 'ProjectIdentifier', 'WorkerExecutable')

	#==========================================================================
	def __init__(self, InstancePath, DevLevel, DevName, ProjectIdentifier, WorkerExecutable):
		
		if DE:BUG(2, "Registering Project: %s:%s:%s:%s" % (InstancePath, DevLevel, DevName, ProjectIdentifier))
		
		self.InstancePath 		= InstancePath
		self.DevLevel 			= DevLevel
		self.DevName 			= DevName
		self.ProjectIdentifier 	= ProjectIdentifier
		self.WorkerExecutable 	= WorkerExecutable	

	#==========================================================================
	@classmethod
	def Register(cls, InstancePath, DevLevel, DevName, ProjectIdentifier, WorkerExecutable):
		
		# "k" means lookup key
		k = (DevLevel, DevName, ProjectIdentifier)
		
		# Cannot re-register the same project identifier on this DevLevel
		if k in cls.ProjectMap:
			t = cls.ProjectMap[k]
			raise cls.AlreadyRegistered("Project %s already registered at %s" % (t.ProjectIdentifier, t.InstancePath))
		
		# otherwise, register the project
		self = cls(InstancePath, DevLevel, DevName, ProjectIdentifier, WorkerExecutable)
		cls.ProjectMap[k] = self 

	#==========================================================================
	@classmethod
	def GetByKey(cls, DevLevel, DevName, ProjectIdentifier):
		try:
			return cls.ProjectMap[(DevLevel, DevName, ProjectIdentifier)]
		except KeyError:
			raise KeyError("No project is registered that matches {DevLevel=%s, DevName=%s, ProjectIdentifier=%s}." % (DevLevel, DevName, ProjectIdentifier))
	


###############################################################################
class ProcessManagerThread(threading.Thread):

	CLEANUP_INTERVAL = 15
	
	
	#==========================================================================
	def __init__(self):
		threading.Thread.__init__(self)
		
		# this thread should NOT keep the server alive
		self.setDaemon(True)
		
		self.Pool_Rest = set()
		self.Pool_Work = set()
		self.Pool_Lock = threading.Lock()
		
		
		# Local variable, no lock needed
		self.KillSet = set()

		# Set the cleanup count
		self.CleanupCount = 0
		
	#==========================================================================
	def run(self):
		"""
		The objective of this being a thread is to be able clean up and manage
		processes as they come and go...

		"""
		
		if DE:BUG(2, "Starting Process Manager...")

		while True:
			try:
				time.sleep(self.CLEANUP_INTERVAL)
				self.CleanupCount += 1
				if DE:BUG(4, "Running ProcessManager cleanup routine (#%i)..." % self.CleanupCount)
				
				# Lock the pool
				with self.Pool_Lock:
					
					if DE:BUG(4, str(self.Pool_Rest))
					if DE:BUG(4, str(self.Pool_Work))

					# Hunt down expired workers and add them to the killlist
					for oWorker in self.Pool_Rest:
						if oWorker.WORKER_TIMEOUT + oWorker.StartTime < Run_ServerTime:
							self.KillSet.add(oWorker)
					
					# Now, remove them from the resting pool
					self.Pool_Rest.difference_update(self.KillSet)
			

				#endwith
				
				while len(self.KillSet):
					try:
						oWorker = self.KillSet.pop()
						oWorker.Close()
					except:
						print; traceback.print_exc(); print
						if DE:BUG(3, "ProcessManager Cleanup Routine (#%i) received %s: \n%s" % (self.CleanupCount, type(e).__name__, str(e)))
			except:
				print; print "Process Manager Exception!"; print
				print; traceback.print_exc(); print
				
			

	#==========================================================================
	def GetWorker(self, oProject):
		"""
		Get a new worker.
		
		1. Obtain an existing worker that is associated with oProject, and 
		   transfer it from Pool_Rest to Pool_Work, OR
		2. Fork and exec a new worker that is associated with oProject and add
		   it to Pool_Work

		Returns the WorkerConnection object.
		"""
		
		# Lock the pool
		with self.Pool_Lock:

			# Hunt down an available connection
			for oWorker in self.Pool_Rest:
				if oWorker.Project == oProject:
					
					self.Pool_Rest.remove(oWorker)
					self.Pool_Work.add(oWorker)
					break
			
			# Need to create one
			else:
				oWorker = WorkerConnection(oProject)
				self.Pool_Work.add(oWorker)

			# Return it
			return oWorker
		
		#endwith

	#==========================================================================
	def PutWorker(self, oWorker):	
		
		# Lock the pool
		with self.Pool_Lock:
			
			self.Pool_Work.remove(oWorker)
			self.Pool_Rest.add(oWorker)	
			
		#endwith
		


###############################################################################
class AuthStruct(object):
	"""
	Supports the following properties:
		DSEG				The data segment that this auth token is for
		AuthToken  			The auth token
		SecurityContext 	The security context that has been authenticated
		Duration			The number of seconds this stays alive for
		Expiration			Unix timestamp that this session will expire on
		RequestCount		The number of requests that have been handled by this token
		Disabled			0 if active; unix timestamp if disabled.
	"""
	
	__slots__ = ('Lock', 'DSEG', 'AuthToken', 'SecurityContext', 'Duration', 'Expiration', 'RequestCount', 'Disabled')
	
	def __init__(self, DSEG, SecurityContext, Duration):
		
		self.Lock				= threading.Lock()
		
		self.DSEG 				= DSEG
		self.SecurityContext 	= SecurityContext
		self.Duration			= int(Duration)
		self.Expiration 		= Run_ServerTime + Duration
		self.RequestCount		= 0
		self.Disabled			= False

		# Unique string to hash for the session token
		entropy = str(random.getrandbits(200)) + str(self.Expiration)
		
		self.AuthToken 			= hashlib.sha1(entropy).hexdigest()

	#==========================================================================
	def Disable(self):
		"""
		Use this call to safely disable a session.
		"""
		with self.Lock:
			self.Disabled = True

###############################################################################
class AuthManagerThread(threading.Thread):
	"""
	The authmap is a simple dictionary of 
		AuthToken => AuthStruct object
	
	"""

	CLEANUP_INTERVAL = 100

	#==========================================================================
	def __init__(self):
		threading.Thread.__init__(self)
		
		# this thread should NOT keep the server alive
		self.setDaemon(True)
		
		# Establish variables and locks
		self.AuthMap = {}
		self.AuthMap_Last = "" # Random data for generating auth tokens
		self.AuthMap_Lock = threading.Lock()

		# Set the cleanup count
		self.CleanupCount = 0

	#==========================================================================
	def run(self):
		if DE:BUG(2, "Starting Authentication Manager...")

		while True:
			time.sleep(self.CLEANUP_INTERVAL)
			self.CleanupCount += 1
			if DE:BUG(4, "Running AuthManager cleanup routine (#%i)..." % self.CleanupCount)
	

	#==========================================================================
	def Hit(self, AuthToken):
		"""
		Loads an AuthStruct by AuthToken.

		In the meanwhile, it verifies that the Token is still valid, and 
		increments the Request Count.

		Returns the AuthStruct object.
		"""
		
		if DE:BUG(4, "AuthManager.Hit(%s)" % AuthToken)

		try:
			oAuthStruct = self.AuthMap[AuthToken]
		except KeyError:
			raise AuthError("AuthToken not Found.", 'NotFound')

		# Lock the AuthStruct (not the AuthMap)
		with oAuthStruct.Lock:
			
			nTime = time.time()

			if oAuthStruct.Expiration <= nTime:
				raise AuthError("AuthToken expired.", 'Expired')

			if oAuthStruct.Disabled:
				raise AuthError("AuthToken disabled.", 'Disabled')

			# ok, increment request count, and offset the Expiration
			oAuthStruct.RequestCount += 1
			oAuthStruct.Expiration = nTime + oAuthStruct.Duration
			
			return oAuthStruct

	#==========================================================================
	def Set(self, DSEG, SecurityContext, Duration):
		"""
		Sets/replaces a AuthStruct.
		Returns the new AuthStruct
		"""
		
		# lock the AuthMap before inserting the AuthStruct
		
		oAuthStruct = AuthStruct(DSEG, SecurityContext, Duration)
		if DE:BUG(4, "AuthManager.Set(%s, %s, %s) -> %s" % (DSEG, SecurityContext, Duration, oAuthStruct.AuthToken))
			
		with self.AuthMap_Lock:
			self.AuthMap[oAuthStruct.AuthToken] = oAuthStruct
			
		return oAuthStruct


	
###############################################################################
class ListenerThread(threading.Thread):

	#==========================================================================
	def __init__(self, AS_Type, AS_Address, AS_Port):
		
		threading.Thread.__init__(self)
	
		# this thread should NOT keep the server alive
		self.setDaemon(True)

		# Set defaults
		self.Backlog = 1
		
		# Setup the running and running lock variable
		self.Running = False
		self.Running_Lock = threading.Lock()

		# Create the socket
		if AS_Type == 'AF_UNIX':
			self._Socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
			self.Address = AS_Address
			self._Socket.bind(self.Address)
			os.chmod(self.Address, 0777)
			
			# Register shutdown functions
			def _DeleteSocket():
				os.remove(AS_Address)

			# Need to remove the socket file when python exits
			atexit.register(_DeleteSocket)
				
		elif AS_Type == 'AF_INET':
			self._Socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			self._Socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
			self.Address = (AS_Address, AS_Port)
			self._Socket.bind(self.Address)
		
		else:
			raise ValueError('Invalid value for AS_Type parameter: %s' % AS_Type)

		
		# Tell it to close on exec
		fcntl.fcntl(self._Socket.fileno(), fcntl.F_SETFD, fcntl.FD_CLOEXEC)
		

		# Begin listening!
		self._Socket.listen(self.Backlog)
	
		if DE:BUG(2, "Listener listening on %s" % str(self.Address))
	
	#==========================================================================
	def run(self):
		try:
			with self.Running_Lock:	self.Running = True

			if DE:BUG(2, "Listener waiting for connections on %s" % str(self.Address))
		
			while self.Running:
			
				try:
					# Accept the connection
					conn, addr = self._Socket.accept()

					if DE:BUG(3, "Client accepted: %s, %s" % (conn, str(addr)))

					# Spawn the client 
					ClientThread(conn, addr).start()
				
				except Exception, e:
						
					print; traceback.print_exc(); print
				
					# Format message:
					if DE:BUG(1, "Primary Listener received exception %s: \n%s" % (type(e).__name__, e.message))
				
				finally:
					# Remove these references
					conn = None
					addr = None
		
		finally:
			with self.Running_Lock:	self.Running = False
		

	
###############################################################################
class ClientThread(threading.Thread):

	#==========================================================================
	def __init__(self, conn, addr):
		"""
		Take incoming socket and address.
		Manage all aspects of that client, including death-detection, etc...

		The ClientConnection will be Stack[0]
		"""
		threading.Thread.__init__(self)
		
		
		self.Stack = [ClientConnection(conn, addr)]
		
		

	#==========================================================================
	def run(self):
		pass

		# Loop while there is a stack
		while len(self.Stack):
			
			#------------------------------------------------------------------
			try:
				# Receive a packet from the tip of the stack.
				# Exceptions received during reading of a packet result in an 
				# unconditional closure of that connection
				CloseConnection = True
				oPacketI = self.Stack[-1].RecvPacket()
				
				if oPacketI.Type == 'Request' and oPacketI.Target == '<SERVER>':
					CloseConnection = False
					self.HandleServerRequest(oPacketI)
				
				elif oPacketI.Type == 'Request':
					CloseConnection = False
					self.HandleRequest(oPacketI)

				elif oPacketI.Type == 'Response':
					CloseConnection = True
					self.HandleResponse(oPacketI)

				elif oPacketI.Type == 'Exception':
					CloseConnection = True
					self.HandleException(oPacketI)

				else:
					raise ValueError("Invalid value for Type received in packet: %s" % oPacketI.Type)
			
			
			#------------------------------------------------------------------
			except ConnectionLost, e:
				
				dead = self.Stack.pop()
				
				if DE:BUG(3, "Connection %s lost due to: %s" % (dead, e.message))

				# If the stack has been emptied, then just close the thread
				if len(self.Stack) == 0:
					# Just get out of here, close the thread
					break 
				
				# Reply with an exception packet
				oPacketO = ExceptionPacket()
				oPacketO.ExceptionType = type(e).__name__
				oPacketO.Message = e.message
				self.Stack[-1].SendPacket(oPacketO) # notify next-of-kin
			
			#------------------------------------------------------------------
			except Exception, e:
				
				if not isinstance(e, (AuthError,)):
					# Print exception
					print; traceback.print_exc(); print
				
				# Format message:
				if DE:BUG(3, "Tip-of-stack %s received %s: \n%s" % (self.Stack[-1], type(e).__name__, e.message))
			
				# Close the connection if instructed to do in the Try block aboce
				if CloseConnection:
					# Discard the tip of the stack
					if DE:BUG(3, "Connection %s closed (due to above)" % self.Stack[-1])
					self.Stack.pop().Close()

				# If the stack has been emptied, then just close the thread
				if len(self.Stack) == 0:
					# Just get out of here, close the thread
					break 
				
				# Reply with an exception packet
				oPacketO = ExceptionPacket()
				oPacketO.ExceptionType = type(e).__name__
				oPacketO.Message = e.message
				if hasattr(e, 'Data'):
					oPacketO.Data = e.Data
				self.Stack[-1].SendPacket(oPacketO) # notify next-of-kin
		
			#------------------------------------------------------------------



			#endtry
		
		#endwhile

	#==========================================================================
	def HandleServerRequest(self, oPacketI):
		"""
		This function is called to handle a Server packet.  A Server Packet is 
		one with a Target == <SERVER>
		"""

		#----------------------------------------------------------------------
		if oPacketI.Method == 'Session.Hit':
			
			if not oPacketI.AuthToken:
				raise AuthError("AuthToken not provided.");
			
			# This will raise an AuthError if there is a problem.
			oAuthStruct = AuthManager.Hit(oPacketI.AuthToken)

			# Send it back to the worker who requested it
			oPacketO = ResponsePacket()
			oPacketO.Data = {
				'AuthToken'		: oAuthStruct.AuthToken,
				'DSEG'			: oAuthStruct.DSEG,
				'Duration'		: oAuthStruct.Duration,
				'Expiration'	: oAuthStruct.Expiration,
				'RequestCount'	: oAuthStruct.RequestCount,
				'Disabled'		: oAuthStruct.Disabled,
				}
			self.Stack[-1].SendPacket(oPacketO)

		#----------------------------------------------------------------------
		elif oPacketI.Method == 'Session.Set':
			
			# Get an auth token from the auth manager
			data = oPacketI.Data
			oAuthStruct = AuthManager.Set(oPacketI.DSEG, data['SecurityContext'], data['Duration'])
			
			# Send it back to the worker who requested it
			oPacketO = ResponsePacket()
			oPacketO.Data = {'AuthToken': oAuthStruct.AuthToken}
			self.Stack[-1].SendPacket(oPacketO)
		
		#----------------------------------------------------------------------
		elif oPacketI.Method == 'Session.End':
			
			if not oPacketI.AuthToken:
				raise AuthError("AuthToken not provided.");
			
			# This will raise an AuthError if there is a problem.
			oAuthStruct = AuthManager.Hit(oPacketI.AuthToken)
			oAuthStruct.Disable()

			# Send it back to the worker who requested it
			oPacketO = ResponsePacket()
			oPacketO.Data = {
				'AuthToken'		: oAuthStruct.AuthToken,
				'DSEG'			: oAuthStruct.DSEG,
				'Duration'		: oAuthStruct.Duration,
				'Expiration'	: oAuthStruct.Expiration,
				'RequestCount'	: oAuthStruct.RequestCount,
				'Disabled'		: oAuthStruct.Disabled,
				}
			self.Stack[-1].SendPacket(oPacketO)

		#----------------------------------------------------------------------
		else:
			raise InvalidOperation("Not able to process Server Packet with method '%s'." % oPacketI.Method)


	
	#==========================================================================
	def HandleRequest(self, oPacketI):
		"""
		This function is called to handle a packet.  It assumes that the 
		packet was received on self.Stack[-1]

		Rules:
		
		1. AuthToken (if present) will:
		   a. ALWAYS override DSEG
		
		2. DSEG == 0 means:
		   a. access to ONLY <SELF>
		   b. <GLOBAL> PROJECT security context
		
		3. DSEG > 0 means:
		   a. access to any Target
		   b. <GLOBAL> CLIENT|WORKER security context


		"""
	
		# Sanity check on packet	
		if oPacketI.DevLevel != Run_DevLevel or oPacketI.DevName != Run_DevName:
			raise InvalidOperation("DevLevel and/or DevName mismatch on packet.  Packet=(%s,%s).  Server=(%s,%s)." % (oPacketI.DevLevel, oPacketI.DevName, Run_DevLevel, Run_DevName))

		# If an auth token is passed, then look up the security context
		# Values found will override the ones found on the packet
		if oPacketI.AuthToken:
			oAuthStruct = AuthManager.Hit(oPacketI.AuthToken)
			oPacketI.SecurityContext = oAuthStruct.SecurityContext
			oPacketI.DSEG = oAuthStruct.DSEG

		
		# See #2 in notes above
		elif oPacketI.DSEG == 0:
			oPacketI.SecurityContext =  WB4.SecurityContext.BuildString(
				RELM=oPacketI.ProjectIdentifier, TYPE='PROJECT', DSEG=oPacketI.DSEG, UUID=oPacketI.ProjectIdentifier
				)

		# See #3 in notes above
		elif isinstance(self.Stack[-1], ClientConnection):
			oPacketI.SecurityContext = WB4.SecurityContext.BuildString(
				RELM='<GLOBAL>', TYPE='CLIENT', DSEG=oPacketI.DSEG, UUID=oPacketI.ProjectIdentifier
				)

		# See #3 in notes above
		elif isinstance(self.Stack[-1], WorkerConnection):
			oPacketI.SecurityContext = WB4.SecurityContext.BuildString(
				RELM='<GLOBAL>', TYPE='WORKER', DSEG=oPacketI.DSEG, UUID=oPacketI.ProjectIdentifier
				)
		
		# Should never happen, but if it does...
		else:
			raise TypeError("PANIC! Connection has an invalid type, or DSEG was invalid.  This should not happen!")

		
		# 
		# in any event, at this point we should have a SecurityContext and a DSEG
		#
		
		# If DSEG is zero, then no cross-project requests are allowed.
		if oPacketI.DSEG == 0 and oPacketI.Target != '<SELF>':
			raise InvalidOperation("DSEG == 0 means that Target must be <SELF> instead of: %s.  Hint: DSEG may have come from an AuthStruct." % oPacketI.Target)
		
		
		# Handle the special "<SELF>" target
		if oPacketI.Target == '<SELF>':
			oPacketI.Target = oPacketI.ProjectIdentifier
		

		# Get a handle to the project that this thread is (currently) serving
		oProject = Project.GetByKey(oPacketI.DevLevel, oPacketI.DevName, oPacketI.Target)

		# obtain a worker bound to that project
		oWorker = ProcessManager.GetWorker(oProject)

		# Add it to our stack
		self.Stack.append(oWorker)

		# send the packet, lock, stock, and barrel, to the new worker
		oWorker.SendPacket(oPacketI)


	#==========================================================================
	def HandleResponse(self, oPacketI):
			
		# Ensure that the stack has a depth of more than one.
		if len(self.Stack) < 2:
			raise InvalidOperation("It is not legal for connection %s to send a reply because none was requested!" % self.Stack[1])
			
		# Yank worker off of tip of stack
		oWorker = self.Stack.pop()
		ProcessManager.PutWorker(oWorker)

		# Send the packet, lock, stock, and barrel, to the next guy on the stack
		self.Stack[-1].SendPacket(oPacketI)
		
	#==========================================================================
	# Exactly the same for now
	HandleException = HandleResponse




###############################################################################
class BaseConnection(BlockingPacketConnection):
	
	# Class attributes
	PacketDelimiter = "\0"
	
	_LastID = 0
	_LastID_Lock = threading.Lock()
	
	# Instance attributes
	ID = None
	
	#==========================================================================
	@staticmethod 
	def NextID():
		"""
		Returns the next available ID in an atomic fashion.
		This CANNOT be an instancemethod or classmethod, or else the ID's 
		will not be globally unique.
		"""
		with BaseConnection._LastID_Lock:
			BaseConnection._LastID += 1
			return BaseConnection._LastID

	
	#==========================================================================
	def SendPacket(self, oPacket):
		"""
		Automatically convert from packet objects to packets, and so on...
		"""
		sPacket = oPacket.ToString()
		if DE:BUG(5, "SERVER Sending Packet on %s: \n%s" % (self, sPacket))
		BlockingPacketConnection.SendPacket(self, sPacket)
	
	#==========================================================================
	def RecvPacket(self):
		"""
		Automatically convert from packet objects to packets, and so on...
		"""
		sPacket = BlockingPacketConnection.RecvPacket(self)
		if DE:BUG(5, "SERVER Receiving Packet on %s: \n%s" % (self, sPacket))
		return ParsePacket(sPacket)
	

###############################################################################
class ClientConnection(BaseConnection):

	SOCKET_TIMEOUT = 60

	
	#==========================================================================
	def __init__(self, conn, addr):
		
		# Get the ID
		self.ID = self.NextID()
		
		# Set the timeout
		conn.settimeout(self.SOCKET_TIMEOUT)
		
		# Tell it to close on exec
		fcntl.fcntl(conn.fileno(), fcntl.F_SETFD, fcntl.FD_CLOEXEC)
		
		# Call baseclass constructor
		BaseConnection.__init__(self, conn, addr)

	#==========================================================================
	def __repr__(self):
		return "<ClientConnection #%i>" % self.ID
	


###############################################################################
class WorkerConnection(BaseConnection):
	"""
	Represents a lowly slave that is destined to be reaped and destroyed by a ruthless parent 
	after it has breathed his last breath.
	"""

	SOCKET_TIMEOUT	= 30
	WORKER_TIMEOUT	= 10
	
	# Process ID of child process
	PID	= None 
	
	# Reference to Project Object
	Project	= None

	# Time the worker started
	StartTime = None


	#==========================================================================
	def __init__(self, oProject):

		self.Project = oProject

		self.StartTime = Run_ServerTime

		self.ID = self.NextID()
		
		# Establish the socket pair that will be used for this worker
		ssock, wsock = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
		addr = ("FD #%i" % ssock.fileno(), "from-exec")
	
		# Set some socket options
		ssock.settimeout(self.SOCKET_TIMEOUT)
#		wsock.settimeout(15)

		#----------------------------------------------------------------------
		# Fork
		self.PID = os.fork()
		
		#----------------------------------------------------------------------
		# We are in the child!
		if self.PID == 0:
			
			# Close the server socket
			os.close(ssock.fileno())

			# Exec the worker
			os.execl(
				oProject.WorkerExecutable, 
				"BLANK", #<-- This is because the first parameter to execl is ignored
				"--DebugLevel=%i" % DE,   #ie. the builtin DE used with BUG  
				"--InstancePath=%s" % oProject.InstancePath,
				"--ProjectIdentifier=%s" % oProject.ProjectIdentifier, 
				"--ConnectionID=%i" % self.ID,
				"--SocketFD=%i" % wsock.fileno(),
				)
		
		#----------------------------------------------------------------------
		# We are in the Parent
		else:

			# Close the worker socket
			os.close(wsock.fileno())

			BaseConnection.__init__(self, ssock, addr)
			
		
	#==========================================================================
	def __repr__(self):
		return "<WorkerConnection #%i>" % self.ID


