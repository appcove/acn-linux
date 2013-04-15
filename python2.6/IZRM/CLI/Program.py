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
	
#	#=================================================================================================================
#	def __init__(self, **args):
#	
#		# Remove the help option if it is not explicitly turned on
#		if not args.has_key("add_help_option"):
#			args['add_help_option'] = False
#		
#		# Let the base class do the rest
#		optparse.OptionParser.__init__(self, **args)
#
	#=================================================================================================================
	def Error(self, msg):
		print msg
		sys.exit(Exit_OtherError)

	error = Error
	
	#=================================================================================================================
	Parse = optparse.OptionParser.parse_args


#######################################################################################################################
def Error(Message, ExitCode = Exit_OtherError):
	print "Error:", Message
	sys.exit(ExitCode)



