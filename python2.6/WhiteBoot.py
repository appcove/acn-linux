import sys
import re
import os.path


FileVersion = 1

# Now, we will identify the dev level
found = re.search('(.*/DevLevel.([0-9])/[a-zA-Z0-9_]+)', os.path.abspath(sys.path[0]))

if found == None:
	raise Exception, "DevLevel.n directory not found in os.path.abspath(sys.path[0]) ('%s')." % os.path.abspath(sys.path[0])


# Set the RootPath
Path = found.groups(0)[0]

# Set the dev level
DevLevel = int(found.groups(0)[1])

# Modify sys.path
sys.path.insert(0, os.path.join(Path, 'zcore', 'Python'))


