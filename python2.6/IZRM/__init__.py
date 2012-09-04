"""
IonZoft Resource Management
Copyright 2001-2007 IonZoft, Inc.  All Rights Reserved.
"""

# Imports
import sys
from os.path import join, realpath, dirname
import socket


# Determine the path to IZRM.  The inner realpath is necessary incase __file__ was symlinked to...
Path = dirname(dirname(dirname(realpath(__file__))))

#TODO: Clean this up

# The official list of server IDs
ServerList = ['FIRE', 'OPEN', 'AP00', 'AP01', 'DB00', 'DB01', 'NEON', 'GATE', 'WIRE', 'IRON']

# Determine the ServerID
ServerID = socket.gethostname()[0:4].upper()

# Validate the ServerID
#if ServerID not in ServerList:
#	raise RuntimeError("Server ID '%s' not in the ServerList %s" % (ServerID, ServerList))

# This points to the config path of THIS SERVER
ServerConfigPath = join(Path, 'ServerConfig', ServerID)


# Cleanup
del(sys, join, realpath, dirname, socket)
