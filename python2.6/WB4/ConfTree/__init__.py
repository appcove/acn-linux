"""
WB4 ConfTree
"""
__all__ = ('Tree', 'TreeException', 'Struct')

from os import makedirs, symlink
from os.path import abspath, join, exists, isdir, dirname
from xml.etree import ElementTree

import shutil
import sys

import WB4
from WB4.ConfTree import Struct

import ConfTree
TreeException = ConfTree.TreeException

import Extruct
InstanceSpec, = Extruct.ParseFile(join(dirname(__file__), 'Extruct.xml'))

class Tree(ConfTree.Tree):
	def __init__(self, sPath):
		
		# Call base class first
		ConfTree.Tree.__init__(self)
		
		# Log activity
		self.Log.append("Loading with path: %s" % sPath)

		# Parse the path out...
		self.PI = WB4.PathInfo(sPath)
		
		if not exists(self.PI.ConfFile):
			raise Exception("No configuration file found: %s" % self.PI.ConfFile)
		
		# Create the Instance object and initialize it
		self.Instance = Struct.Instance()

		self.Instance.Path 		= self.PI.Instance
		self.Instance.DevLevel 	= self.PI.DevLevel
		self.Instance.DevName 	= self.PI.DevName

		# Set a reference on the instance for the instance to use internally...
		self.Instance.PathInfo 	= self.PI

		# Make "Instance" available as a global within the twig files
		self.SetVars(Instance=self.Instance, FileWriter=ConfTree.FileWriter)

	def Load(self):
		self.Include(self.PI.ConfFile)

	def VarDump(self):
		return self.Instance.VarDump()
	
	def ToNative(self):
		RVAL = {}
		self.Instance.ToNative(RVAL)
		return InstanceSpec.Convert(RVAL)
	
	def Save(self):
		# Build XML
		oNode = ElementTree.Element('Instance')
		self.Instance.ToXML(oNode)
		
		# Write XML
		oTree = ElementTree.ElementTree(oNode)
		oTree.write(self.PI.DataFile)

		# Remove and rewrite Package dir links
		ProjectDir = join(self.PI.Package, 'Project')
		if exists(ProjectDir):
			shutil.rmtree(ProjectDir)
		makedirs(ProjectDir)
		
		f = open(join(ProjectDir, '__init__.py'), 'w')
		f.write("# Placeholder placed by ConfTree\n")
		f.close()
		
		for app in (p.App for p in self.Instance.Project.values() if p.App != None):
			linkpath = join(ProjectDir, app.ModuleName)
			symlink(app.Path, linkpath)

		# Build AutoConf files
		self.RunAutoConf()




