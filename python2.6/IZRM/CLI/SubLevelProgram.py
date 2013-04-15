import sys
import optparse

#######################################################################################################################
# "Constants"
Exit_Success = 0
Exit_BadCommand = 2
Exit_OtherError = 3
Exit_InternalError = 4

#######################################################################################################################
class OptionParser(optparse.OptionParser):
	
	#=================================================================================================================
	def __init__(self, **args):
	
		# Remove the help option if it is not explicitly turned on
		if not args.has_key("add_help_option"):
			args['add_help_option'] = False
		
		# Let the base class do the rest
		optparse.OptionParser.__init__(self, **args)

	#=================================================================================================================
	def Error(self, msg):
		print msg
		sys.exit(Exit_OtherError)

	error = Error
	#=================================================================================================================
	def Parse(self):
		return self.parse_args(args=sys.argv[2:])



#######################################################################################################################
def _MakeCommandDict(CommandList):
	"""
	Take a CommandList and return a CommandDict

	A CommandList is a list lists.  Each list contains one or more elements:
	[0] 	- string command
	[1]		- alias 1
	[2]		- alias 2
	...
	"""

	dReturn = {}

	for lAlias in CommandList:
		for sAlias in lAlias:
			dReturn[sAlias] = lAlias[0]

	return dReturn;


#######################################################################################################################
def _PrintUnknown(sCommand):
	print "Unknown command: '%s'" % sCommand

#######################################################################################################################
def _PrintUsage(sProgramName):
	print "Type '%s help' for usage." % sProgramName
	
#######################################################################################################################
def _PrintHelp(HelpText, CommandList, ProgramName):
	
	sCommandList = "Available subcommands:\n"

	# Make it pretty
	for lAlias in CommandList:
		if len(lAlias) == 1:
			sCommandList += "    %s\n" % lAlias[0]
		else:
			sCommandList += "    %s (%s)\n" % (lAlias[0], ", ".join(lAlias[1:]))
			
	
	print HelpText % {'CommandList': sCommandList, 'ProgramName': ProgramName}


#######################################################################################################################
def _GetCommandModule(ProgramModule, sRealCommand):
	
	# Calculate the module name.  Remember that it is always a direct submodule of ProgramModule
	sModuleName = "%s.%s" % (ProgramModule.__name__, sRealCommand)
	
	# Import it and get a handle on it
	__import__(sModuleName)
	oModule = sys.modules[sModuleName]

	# Validate that it is "OK":
	# 1. HelpText must be present and a string
	# 2. Parser must be present and a instance OptionParser (in this file)
	# 3. Run must be present and callable


	try:
		# 1. 
		if type(oModule.HelpText) != str:
			raise TypeError, "attribute 'HelpText' must be a string"

		if not isinstance(oModule.Parser, OptionParser):
			raise TypeError, "attribute 'HelpText' must be an instance of %s" % OptionParser

		if not callable(oModule.Run):
			raise TypeError, "attribute 'Run' must be callable"
	
	except (AttributeError, TypeError), e:
		print "For %s, %s." % (oModule, e)
		sys.exit(Exit_InternalError)
	
	# Now, return the module
	return oModule

#######################################################################################################################
def Run(ProgramName, ProgramModule, ArgumentList=sys.argv[1:], CommandList=None, HelpCommand='help'):
	"""
	This is to be called from a command-line script that wishes to operate as a SubLevelProgram, such as `svn`.

	Parameters:
		ProgramName 				- string
		ProgramModule 				- Module object that contains each subcommand.
		ArgumentList 				- sys.argv[1:] by default. note: if passed, only pass arguments!
		CommandList					- An alternate command list (see below for ProgramModule.CommandList)
		HelpCommand					- The command that means "help" - defaults to 'help'

	Requirements:
		ProgramModule.CommandList 	- a List of Lists.  See the docstring on _MakeCommandDict above.
		ProgramModule.HelpText		- a long string of help text.  The following variables are replaced:
		  	%(CommandList)s				- string - a nice list of commands
			%(ProgramName)s				- string - the name of the calling program

	Sub Programs:				- SubProgram modules are within program modules (SomeProgram.SomeCommand.)
		.SubProgram.HelpText		- a long string of help text.  The following variables are replaced:
			%(OptionList)s				- string - a nice list of program options
			%(ProgramName)s				- string - the name of the calling program
			%(CommandName)s				- string - the command name
		.SubProgram.Parser			- an instance of the OptionParser class found in this module
		.SubProgram.Run(dOpt, lArg)	- A function call that "does the work".  Takes options and args as params.
			Parsing the Command Line	- `Opt, Arg = Parser.Parse()` will likely be the first line of Run()
			Raising Option Errors		- Parser.Error("Message")
	"""

	# get a command list - if it is not provided, then fetch it from the ProgramModule
	if CommandList == None:
		CommandList = ProgramModule.CommandList

	# Get a Command Dict for quick lookups
	dCommand = _MakeCommandDict(CommandList)

	# Get the current command
	try:
		sCommand = ArgumentList[0]
	except IndexError:
		sCommand = None


	#== Possibilities ==
	# 1. No command
	# 2. help command
	# 3. Unknown command
	# 4. known command 

	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# 1. No command
	if sCommand == None:
		_PrintUsage(ProgramName)
		sys.exit(Exit_BadCommand)
		
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# 2. Help command
	elif sCommand == HelpCommand or dCommand[sCommand] == HelpCommand:
		
		# Get the help command
		try:
			sHelpCommand = ArgumentList[1]
		except IndexError:
			sHelpCommand = None

		#== Possibilities ==
		# A. No command
		# B. unknown command
		# C. Valid help command

		# .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .
		# A. No Command
		if sHelpCommand == None:
			_PrintHelp(ProgramModule.HelpText, CommandList, ProgramName)
			sys.exit(Exit_Success)

		# .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .
		# B. Unknown command
		elif not dCommand.has_key(sHelpCommand):
			_PrintUnknown(sHelpCommand)
			_PrintUsage(ProgramName)
			sys.exit(Exit_BadCommand)
		
		# .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .
		# C. Known command
		else:
			# Get the module
			oModule = _GetCommandModule(ProgramModule, dCommand[sHelpCommand])
			
			# Format the help
			print oModule.HelpText % {
				'ProgramName': ProgramName,
				'CommandName': dCommand[sHelpCommand],
				'OptionList': oModule.Parser.format_option_help(),
				}

			sys.exit(Exit_Success)
		

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# 3. Unknown command
	elif not dCommand.has_key(sCommand):
		_PrintUnknown(sCommand)
		_PrintUsage(ProgramName)
		sys.exit(Exit_BadCommand)
	
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# 4. Known command
	else:
		# Get a handle to the module
		oModule = _GetCommandModule(ProgramModule, dCommand[sCommand])
		
		# Read in command line options and arguments
		# TODO: Finish
				
		oModule.Run()
		sys.exit(Exit_Success)









