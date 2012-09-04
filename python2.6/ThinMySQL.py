

import _mysql

import re

from decimal import Decimal


class FIELD_TYPE(object):
	DECIMAL = 0			# Decimal
	TINY = 1			# int
	SHORT = 2			# int
	LONG = 3			# int
	FLOAT = 4			# float
	DOUBLE = 5			# float
	NULL = 6			# lambda value: None
	TIMESTAMP = 7		# 
	LONGLONG = 8		# int
	INT24 = 9			# int
	DATE = 10			# 
	TIME = 11			# 
	DATETIME = 12		# 
	YEAR = 13			#
	NEWDATE = 14		# 
	VARCHAR = 15		# 
	BIT = 16			# int
	NEWDECIMAL = 246	# Decimal
	ENUM = 247			# 
	SET = 248			# 
	TINY_BLOB = 249		# 
	MEDIUM_BLOB = 250	# 
	LONG_BLOB = 251		# 
	BLOB = 252			# 
	VAR_STRING = 253	# 
	STRING = 254		# 
	GEOMETRY = 255		# 


# This "function" will split a query by data values, including the data values...
SplitQuery = re.compile("\{\{([a-zA-Z0-9_/]+:[a-zA-Z0-9_]+)\}\}").split




# DataNotFound
class DataNotFound(Exception):
	pass

# Connection class
class Connection(object):

	KWMAP = {
		'Host'		: 'host',
		'Port'		: 'port',
		'Username'	: 'user',
		'Password'	: 'passwd',
		'Database'	: 'db',
		}


	def __init__(self, **kwargs):
		
		# Argument remapping
		for one,two in self.KWMAP.items():
			if one in kwargs:
				kwargs[two] = kwargs[one]
				del(kwargs[one])
		
		# Create the connection	
		self.CONN = _mysql.connection(**kwargs)
		
		# Establish MySQL to Python conversions
		self.CONN.converter = {
			FIELD_TYPE.DECIMAL:		Decimal,
			FIELD_TYPE.TINY:		int,
			FIELD_TYPE.SHORT:		int,
			FIELD_TYPE.LONG:		int,
			FIELD_TYPE.FLOAT:		float,
			FIELD_TYPE.DOUBLE:		float,
			FIELD_TYPE.NULL:		lambda value: None,
			FIELD_TYPE.LONGLONG:	int,
			FIELD_TYPE.INT24:		int,
			FIELD_TYPE.BIT:		 	int,
			FIELD_TYPE.NEWDECIMAL:	Decimal,
			}
		

		QSL = self.CONN.string_literal

		# Establish Python to SQL conversions
		# ie. {{conv:varname}}
		self.CONV = {
			'bool'			: lambda v: "1" if v else "0",
			'bool/null'		: lambda v: 'NULL' if v == None else ("1" if v else "0"),
			
			'int'			: lambda v: str(int(v)),
			'int/list'		: lambda v: str.join(', ', [str(int(s)) for s in v]) if len(v) else 'NULL',
			'int/null'		: lambda v: 'NULL' if v == None else str(int(v)),
			
			'float'			: lambda v: str(float(v)),
			'float/list'	: lambda v: str.join(', ', [str(float(s)) for s in v]) if len(v) else 'NULL',
			'float/null'	: lambda v: 'NULL' if v == None else str(float(v)),
			
			'string'		: lambda v: self.CONN.string_literal(str(v)),
			'string/list'	: lambda v: str.join(', ', [QSL(str(s)) for s in v]) if len(v) else 'NULL',
			'string/null'	: lambda v: 'NULL' if v == None else QSL(str(v)),
			
			'decimal'		: lambda v: str(Decimal(v)),
			'decimal/list'	: lambda v: str.join(', ', [str(Decimal(s)) for s in v]) if len(v) else 'NULL',
			'decimal/null'	: lambda v: 'NULL' if v == None else str(Decimal(v)),
			
			'sql'			: lambda v: str(v),
			}
		
		# Will hold the last 20 queries
		self.QueryHist = []

		# Will hold the query count
		self.QueryCount = 0

		# Stack of transaction objects
		self.TransactionStack = []
		


	def Execute(self, Query, Data):
		"""
		Executes a query and returns the result object or 
		NULL if there was no result
		"""
		sql = self._EscapeQuery(Query, Data)
		
		self.QueryHist.append(sql)
		
		if len(self.QueryHist) > 20:
			self.QueryHist.pop(0) 
		
		self.QueryCount += 1
		
		self.CONN.query(sql)
		return self.CONN.store_result()


	def ExecuteNonQuery(self, Query, Data):
		"""
		Executes a query.  Ensure that this query DOES NOT have
		a result set, or bad things may happen later.
		"""
		sql = self._EscapeQuery(Query, Data)
		
		self.QueryHist.append(sql)
		
		if len(self.QueryHist) > 20:
			self.QueryHist.pop(0) 
		
		self.QueryCount += 1
		
		self.CONN.query(sql)
		


	def RowList(self, Query, Data, RowFormat=1):
		"""
		Returns a sequence of dicts - one dict for each row.
		"""
		oResult = self.Execute(Query, Data)
		return oResult.fetch_row(oResult.num_rows(), RowFormat)

	
	def TRowList(self, Query, Data):
		"""
		Return a sequence of tuples - one tuple for each row.
		"""
		oResult = self.Execute(Query, Data)
		return oResult.fetch_row(oResult.num_rows(), 0)
	

	def ValueList(self, Query, Data, Conversion=None):
		"""
		Returns a list of values.  The values are obtained from the [0]th
		element of each row.

		Conversion is an optional keyword parameter which specifies a
		function to pass each value through.
		"""
		if Conversion:
			return [Conversion(row[0]) for row in self.TRowList(Query, Data)]	
		else:
			return [row[0] for row in self.TRowList(Query, Data)]	
			
	
	def KeyValueDict(self, Query, Data, Conversion=None):
		"""
		Returns a dictionary of [col1] mapped to [col2]

		Conversion is an optional keyword parameter which specifies a
		function to pass each (key,value) through.  This function must 
		accept a 2-tuple (key,value) as a parameter, and return a 2-tuple.
		"""
		if Conversion:
			return dict((Conversion((row[0], row[1])) for row in self.TRowList(Query, Data)))
		else:
			return dict(((row[0], row[1]) for row in self.TRowList(Query, Data)))
	
		
	
	def Row(self, Query, Data, RaiseError=True):
		oResult = self.Execute(Query, Data)
		
		nRows = oResult.num_rows()
		if nRows == 1:	
			return oResult.fetch_row(nRows, 1)[0]
		else:
			if RaiseError:
				raise DataNotFound("Exactly 1 record was expected, but %i were returned." % nRows)
			else:
				return False

	def TRow(self, Query, Data, RaiseError=True):
		oResult = self.Execute(Query, Data)
		
		nRows = oResult.num_rows()
		if nRows == 1:	
			return oResult.fetch_row(nRows, 0)[0]
		else:
			if RaiseError:
				raise DataNotFound("Exactly 1 record was expected, but %i were returned." % nRows)
			else:
				return False


	def Value(self, Query, Data, RaiseError=True):
		v = self.TRow(Query, Data, RaiseError)
		#workaround for unsubscriptable boolean balue when RaiseError is False
		return v[0] if v else False  
		
	def Bool(self, Query, Data, RaiseError=True):
		v = self.TRow(Query, Data, RaiseError)
		#workaround for unsubscriptable boolean balue when RaiseError is False
		return (v[0] not in ('', '0', 0, 0.00, False, None)) if v else False  

	
	def Transaction(self):
		return _Transaction(self)

	def Rollback(self):
		raise _Transaction_Rollback()
	
	
	def _EscapeQuery(self, Query, Data):
		"""
		Uses a custom replacement syntax to correctly handle
		type conversions and quoting, etc...

		Within the query, VarDefs will look like:
			{{type:name}}

		They can occur anywhere, and there is no (currently) suitable way to escape them.

		see self.CONV for a list of valid types...
		
		`name` refers to a key in the Data mapping.  If the name appears to be
		an integer, it will be converted to an integer prior to lookup.  This allows
		for lists or tuples to be used as the data mapping.

		"""

		# Split the query into tokens.
		# The list will look like:
		#   [SQL, (VarDef, SQL)*]
		Tokens = SplitQuery(Query)

		# Just care about the odd tokens (the VarDef ones)
		for i in range(1, len(Tokens), 2):
			
			typecode, name = Tokens[i].split(':')

			# integer names are converted to integer
			if name.isdigit():
				name = int(name)

			try:
				# Get value from mapping:
				value = Data[name]
			except (KeyError, IndexError):
				raise KeyError("Query contained {{%s:%s}} -- name `%s` not found in Data %s." % (typecode, name, name, type(Data)))
	
			Tokens[i] = self.CONV[typecode](value)
	
		
		
		# Join the tokens back together to form a safe query string
		return str.join("", Tokens)
		


class _Transaction_Rollback(Exception):
	pass


class _Transaction(object):
	"""
	WARNING! WARNING! WARNING!
	Do not mix this with SQL START/ROLLBACK/COMMIT commands...

	Makes heavy use of MySQL SAVEPOINTS:
	http://dev.mysql.com/doc/refman/5.1/en/savepoints.html

	"""
	
	def __init__(self, Conn):
		self.Conn = Conn
	
	
	def __enter__(self):
		SPN = len(self.Conn.TransactionStack)
		self.Conn.TransactionStack.append(self)

		# If at the beginning of the stack, then start a transaction
		if SPN == 0:
			self.Conn.ExecuteNonQuery("START TRANSACTION", None)
		
		# Otherwise, just set a savepoint
		else:
			self.Conn.ExecuteNonQuery("SAVEPOINT `SP%i`" % SPN, None)
	

	def __exit__(self, exc_type, exc_val, exc_tb):
		self.Conn.TransactionStack.pop()
		SPN = len(self.Conn.TransactionStack)

	
		# If there is an exception, we need to rollback
		if exc_type:
	
			# If back to the beginning of the stack, then commit the trans
			if SPN == 0:
				self.Conn.ExecuteNonQuery("ROLLBACK", None)
			
			# Otherwise clear the savepoint
			else:
				self.Conn.ExecuteNonQuery("ROLLBACK TO SAVEPOINT `SP%i`" % SPN, None)
				# Releasing the savepoint is not needed because MySQL will 
				# replace the savepoint if the same name is re-used
				# http://dev.mysql.com/doc/refman/5.1/en/savepoints.html
		
			
			# Returning true will supress this exception
			return exc_type == _Transaction_Rollback

		
		# Otherwise, we should commit
		else:
				
			# If back to the beginning of the stack, then commit the trans
			if SPN == 0:
				self.Conn.ExecuteNonQuery("COMMIT", None)
			
			# Otherwise clear the savepoint
			else:
				self.Conn.ExecuteNonQuery("RELEASE SAVEPOINT `SP%i`" % SPN, None)
	
			# Default return value of __exit__
			return False

	
	
	def Rollback(self):
		"""
		Raises a special exception which 
		"""
		raise _Transaction_Rollback()	






