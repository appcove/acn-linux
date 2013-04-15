from __future__ import absolute_import


from Extruct import NativeToNative_Convertor
from Extruct import _ConversionError

from xml.etree import cElementTree as ElementTree


Element = ElementTree.Element
Debug = False

###################################################################################################
class NativeToXML_Convertor(NativeToNative_Convertor):
	

	#==============================================================================================
	def Convert(self, DATA):
		"""
		DATA is a python dictionary.  
		Returns an XML stream.
		"""
		oXML =  NativeToNative_Convertor.Convert(self, DATA)
		return ElementTree.tostring(oXML)

	#==============================================================================================
	def _Bool(self, oNode, DATA):
		DATA =  NativeToNative_Convertor._Int(self, oNode, DATA)
		elem = Element(oNode.Name)
		elem.text = "1" if DATA else "0"
		return elem

	#==============================================================================================
	def _Int(self, oNode, DATA):
		DATA =  NativeToNative_Convertor._Int(self, oNode, DATA)
		elem = Element(oNode.Name)
		elem.text = str(DATA)
		return elem

	#==============================================================================================
	_Int_Key =  NativeToNative_Convertor._Int
	
	#==============================================================================================
	def _Float(self, oNode, DATA):
		DATA =  NativeToNative_Convertor._Float(self, oNode, DATA)
		elem = Element(oNode.Name)
		elem.text = str(DATA)
		return elem

	#==============================================================================================
	def _Decimal(self, oNode, DATA):
		DATA =  NativeToNative_Convertor._Decimal(self, oNode, DATA)
		elem = Element(oNode.Name)
		elem.text = str(DATA)
		return elem

	#==============================================================================================
	def _String(self, oNode, DATA):
		DATA =  NativeToNative_Convertor._String(self, oNode, DATA)
		elem = Element(oNode.Name)
		elem.text = str(DATA)
		return elem

	#==============================================================================================
	def _Unicode(self, oNode, DATA):
		raise _ConversionError(oNode, DATA, "Unsupported data type %s" % type(DATA))

	#==============================================================================================
	def _Binary(self, oNode, DATA):
		DATA =  NativeToNative_Convertor._Binary(self, oNode, DATA)
		elem = Element(oNode.Name)
		elem.text = str(DATA)
		return elem

	#==============================================================================================
	def _List(self, oNode, DATA):
		DATA =  NativeToNative_Convertor._List(self, oNode, DATA)
		elem = Element(oNode.Name)
		
		for child in DATA:
			elem.append(child)
		
		return elem

	#==============================================================================================
	def _Dict(self, oNode, DATA):
		DATA =  NativeToNative_Convertor._Dict(self, oNode, DATA)
		elem = Element(oNode.Name)
		
		for key, value in DATA.items():
			#key will be an element as returned by _String or _Int
			key = key.text
			
			value.attrib[oNode.Key.Name] = key
			elem.append(value)
		
		return elem
	
	#==============================================================================================
	def _Struct(self, oNode, DATA):
		DATA =  NativeToNative_Convertor._Struct(self, oNode, DATA)
		elem = Element(oNode.Name)
		
		for key in DATA:
			
			try:
				elem.append(DATA[key])

			except TypeError, e:
				pass

		return elem


###################################################################################################
class XMLToNative_Convertor( NativeToNative_Convertor):
	
	
	#==============================================================================================
	def Convert(self, DATA):
		"""
		Takes XML stream and transforms it 
		into a native python data structure

		"""
		oXML = ElementTree.fromstring(DATA)	
		return  NativeToNative_Convertor.Convert(self, oXML)

	#==============================================================================================
	def _Bool(self, oNode, DATA):
		"""
		DATA is an xml node containing a string that represents a Boolean
		"""
		if DATA.text == None:
			return None
		else:
			return  NativeToNative_Convertor._Bool(self, oNode, DATA.text)

	#==============================================================================================
	def _Int(self, oNode, DATA):
		"""
		DATA is an xml node containing a string that represents an integer
		"""
		if DATA.text == None:
			return None
		else:
			return  NativeToNative_Convertor._Int(self, oNode, DATA.text)
	
	#==============================================================================================
	def _String(self, oNode, DATA):
		"""
		DATA is an xml node containing a string
		"""
		if DATA.text == None:
			return None
		else:
			return NativeToNative_Convertor._String(self, oNode, DATA.text)
			
	#==============================================================================================
	def _Float(self, oNode, DATA):
		"""
		DATA is an XML node containing a string
		"""
		if DATA.text == None:
			return None
		else:
			return  NativeToNative_Convertor._Float(self, oNode, DATA.text)

	#==============================================================================================
	def _Decimal(self, oNode, DATA):
		"""
		DATA is an XML node containing a string
		"""
		if DATA.text == None:
			return None
		else:
			return  NativeToNative_Convertor._Decimal(self, oNode, DATA.text)
		
	#==============================================================================================
	def _List(self, oNode, DATA):
		"""
		DATA RECEIVED WILL BE A XML NODE.  Each Child node is a list item.
		"""
		try:
			oValueNode = oNode.Value
			oValueFunc = getattr(self, "_"+oValueNode.Type)
			
			RVAL = []
			for oChild in DATA:
				RVAL.append(oValueFunc(oValueNode, oChild))

			return RVAL
		
		except _ConversionError, e:
			e.InsertStack(oNode, i)
			raise

		except Exception, e:
			if Debug: raise
			raise _ConversionError(oNode, DATA, "%s: %s" % (e.__class__.__name__, e.message))

	
	#==============================================================================================
	def _Dict(self, oNode, DATA):
		"""
		DATA RECEIVED WILL BE AN XML NODE.
		"""

		try:
			oKeyNode = oNode.Key
			
			oKeyFunc = getattr( NativeToNative_Convertor, "_"+oKeyNode.Type)

			oValueNode = oNode.Value
			oValueFunc = getattr(self, "_"+oValueNode.Type)
			
			RVAL = {}

			for oChild in DATA:
				key = oChild.attrib[oKeyNode.Name]
				
				key = oKeyFunc(self, oKeyNode, key)
				RVAL[key] = oValueFunc(oValueNode, oChild)

			return RVAL

		except _ConversionError, e:
			e.InsertStack(oNode, key)
			raise

		except Exception, e:
			if Debug: raise
			raise _ConversionError(oNode, DATA, "%s: %s" % (e.__class__.__name__, e.message))

	#==============================================================================================
	def _Struct(self, oNode, DATA):
		"""
		DATA RECEIVED WILL BE AN XML NODE.
		"""
		try:
		
			TDATA = {}
			for oChild in DATA:
				TDATA[oChild.tag] = oChild
			
			RVAL = {}
			for oPropNode in oNode.Prop:
				oFunc = getattr(self, "_"+oPropNode.Type)
				
				try:
						
					if oPropNode.Name in TDATA:	
						value = TDATA[oPropNode.Name]				
						rValue = oFunc(oPropNode, value)
					
						if rValue == None and oPropNode.Default:
							RVAL[oPropNode.Name] = oPropNode.Default
						
						elif rValue == None and not oPropNode.Default and oPropNode.Nullable:
							RVAL[oPropNode.Name] = rValue
								
						elif rValue != None:							
							RVAL[oPropNode.Name] = rValue
				
						elif rValue == None and not oPropNode.Default and not oPropNode.Nullable:
							raise KeyError("[%s] must be set, Nullable or Defaulted" % oPropNode.Name)

						else:
							raise KeyError("[%s] must be set, Nullable or Defaulted" % oPropNode.Name)
						
					elif oPropNode.Name not in TDATA and oPropNode.Nullable and oPropNode.Default:
						TDATA[oPropNode.Name] = ElementTree.Element(oPropNode.Name)
						RVAL[oPropNode.Name] = oPropNode.Default
				
					elif oPropNode.Name not in TDATA and oPropNode.Nullable and not oPropNode.Default:
						TDATA[oPropNode.Name] = ElementTree.Element(oPropNode.Name)
						RVAL[oPropNode.Name] = None

					elif oPropNode.Name not in TDATA and not oPropNode.Nullable and oPropNode.Default:
						TDATA[oPropNode.Name] = ElementTree.Element(oPropNode.Name)
						RVAL[oPropNode.Name] = oPropNode.Default

					elif oPropNode.Name not in TDATA and not oPropNode.Nullable and not oPropNode.Default:
						raise KeyError("[%s] must be set, Nullable or Defaulted" % oPropNode.Name)
					
					else: 
						raise KeyError("[%s] must be set, Nullable or Defaulted" % oPropNode.Name)
											
				except _ConversionError, e:
					e.InsertStack(oNode, e)
					raise

				except Exception, e:
					if Debug: raise
					raise _ConversionError(oNode, DATA, "%s: %s" % (e.__class__.__name__, e.message))

			return RVAL

		except _ConversionError, e:
			e.InsertStack(oNode, e)
			raise

		except Exception, e:
			if Debug: raise
			raise _ConversionError(oNode, DATA, "%s: %s" % (e.__class__.__name__, e.message))

	###################################################################################################

