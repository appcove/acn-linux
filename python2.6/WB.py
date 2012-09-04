"""
The WB module exists to do four things:
1. Find the root path of the calling directory
2. Within the calling directory, find its Sub modules
3. Set its __path__ variable
4. Determine the DevLevel it is operating in

Variables:
1. DevLevel - integer development level
2. Path     - string path to the WhiteBoot install root

Notes:
1. In order for this module to work, it must be imported from a directory that is or is a sub-directory to a DevLevel.n directory
2. All project applications will be accessable by:
>>> import WB.appsid

"""

import sys
import re
from os.path import join, abspath 
from os import getcwd


# Global variables
Path 		= None
DevLevel 	= None


def Load():

	global Path, DevLevel, __path__

	# If path is not specified, find it
	if Path == None:

		# Get the calling path
		sCallPath = abspath(getcwd())

		# Now, we will identify the dev level
		found = re.search('.*/DevLevel.[0-9]/[a-zA-Z0-9_]+', sCallPath)

		if found == None:
			raise Exception, "DevLevel.n directory not found in '%s'." % sCallPath

		# Set the RootPath
		Path = found.group(0)


	# If DevLevel is not specified, find it (based on Path)
	if DevLevel == None:
		
		# find the DevLevel
		found = re.search('/DevLevel.([0-9])', Path)
		
		if found == None:
			raise Exception, "DevLevel.n directory not found in '%s'." % sCallPath

		# Set the dev level
		DevLevel = int(found.group(1))



	# SANITY check on DevLevel
	if DevLevel not in (0,1,2,3,4,5,6,7,8,9):
		raise Exception, "Invalid DevLevel: %s" % DevLevel
	
	
	# Modify this module's search path for submodules...
	__path__ = [join(Path, 'WB_Package'), join(Path, 'Project_App')]

	
	# Modify sys.path
	sys.path.insert(1, join(Path, 'Lib_Python'))



