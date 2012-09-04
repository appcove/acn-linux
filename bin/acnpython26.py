# vim:encoding=utf-8:ts=2:sw=2:expandtab

# WARNING: these may be used in scripts that import * from this script

import sys
from os.path import abspath, dirname, join, exists, isdir

#==============================================================================
# Add THIS acn-linux's python26 directory to the near-beginning of sys.path

Path = dirname(abspath(sys.path[0]))
PythonPath = join(Path, 'python2.6')

try:
  sys.path.remove(PythonPath)
except ValueError:
  pass

sys.path.insert(1, PythonPath)


