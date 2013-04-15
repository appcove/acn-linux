<?php


/*
Symbols defined once WB4 is imported:

	WB4_StartTime 	(constant)
	WB4 			(class)
	WB4_App			(class)

Symbols defined once WB4::Load() is called: 	
	
	WB4_LoadTime	(constant)
	
	WB4_DevLevel	(constant)
	WB4_DevName		(constant)
	WB4_Path		(constant)

	WB4_CLI			(constant)
	WB4_CWF			(constant)
	WB4_CWD			(constant)

	WB4_App::$Identifier 
	WB4_App::$Path

*/


//Define the application start time
define('WB4_StartTime', microtime(1));

###################################################################################################
class WB4
{
	public static $Loaded = False;
	public static $Loaded_Auto = False;
	public static $Loaded_Init = False;
	public static $Loaded_Exec = False;
	
	protected static $_Init = array();
	protected static $_Exec = array();

	// Returns an array of _Init files in their include order
	public static function GetInit() {return self::$_Init;}

	// Returns an array of _Exec files in their include order
	public static function GetExec() {return array_reverse(self::$_Exec);}

	// ============================================================================================
	// Pass an alternate start point (file path) to this function if desired.
	public static function Load($sPath = NULL)
	{
		if(self::$Loaded)
			return;
		self::$Loaded = True;

		//If the constant WB4_CWF (current working file) has been defined, then we 
		//don't need to auto-determine the current value of the executing php script
		if($sPath)
		{
			if(! is_file($sPath))
				throw new Exception("WB4 Startup failed. If you define the WB4_CWF constant, then it must point to a valid php file: $sPath");
			
			define('WB4_CLI', php_sapi_name() == 'cli');
			define('WB4_CWF', $sPath);
		}
		else switch(php_sapi_name())
		{
			case 'apache':
			case 'apache2handler':
				define('WB4_CLI', FALSE);
				define('WB4_CWF', $_SERVER['SCRIPT_FILENAME']);			//Symbolic Links supported
				break;
			
			case 'cli':
				define('WB4_CLI', TRUE);
				define('WB4_CWF', realpath($_SERVER['SCRIPT_FILENAME']));	//Symbolic Links not supported
				break;
			
			case 'cgi':
				if(! isset($_SERVER['argv'][0]))
					throw new Exception("WB4 Startup failed. You are using the cgi sapi.  The register_argc_argv ini setting must be 'on' in order to use WB4 with the this sapi.");
				
				define('WB4_CLI', FALSE);
				define('WB4_CWF', realpath($_SERVER['argv'][0]));			//Symbolic Links not supported
				break;
			
			default:
				throw new Exception
				(
					"WB4 Startup failed. You are using the " . php_sapi_name() . " sapi, which is not ".
					"supported by WB4. Either change to a supported sapi ('apache', 'apache2handler', ".
					"'cli', 'cgi'), or pass a path to the WB4::Load() function."
				);
		}

		//Define the current working directory constant - that is, the directory of the called script
		define('WB4_CWD', $sCWD = dirname(WB4_CWF));
		
		//Traverse the directory structure back to the WB4_WebPath directory
		$sOldCWD = '';
		$i = 0;
		$sRoot = NULL;
			
		while(1)
		{
			//If WB4_InitFileName is not false, then check to see if WB4_InitFileName exists in the current directory
			if(file_exists($sCWD . '/_Init.php'))
				self::$_Init[] = $sCWD . '/_Init.php';
			
			if(file_exists($sCWD . '/_Exec.php'))
				self::$_Exec[] = $sCWD . '/_Exec.php';
			
			if(file_exists($sCWD . '/_Root.php'))
			{
				$sRoot = $sCWD . '/_Root.php';
				break;
			}
			
			//Go to the next parent dir (saving the value of the the current CWD in $sOldCWD)
			$sCWD = dirname($sOldCWD = $sCWD);
			
			if(($sCWD == $sOldCWD) || ($i++ > 64))
				throw new Exception("WB4 Startup failed. _Root.php not found in $i directories starting with '".WB4_CWF."'.");
		}
	
		//Include the _Root file...
		require($sRoot);

		if(! defined('WB4_Path'))
			throw new Exception("Constant WB4_Path must be defined in/by: $sRoot");
		if(! defined('WB4_DevLevel'))
			throw new Exception("Constant WB4_DevLevel must be defined in/by: $sRoot");
		if(! in_array(WB4_DevLevel, array(0,1,2,3,4,5,6,7,8,9), True))
			throw new Exception("Constant WB4_DevLevel has an invalid value: ".WB4_DevLevel);
		if(! defined('WB4_DevName'))
			throw new Exception("Constant WB4_DevName must be defined in/by: $sRoot");
		if(is_null(WB4_App::$Identifier))
			throw new Exception('Static Variable WB4_App::$Identifier must be defined in/by: '.$sRoot);
		if(is_null(WB4_App::$Path))
			throw new Exception('Static Variable WB4_App::$Identifier must be defined in/by: '.$sRoot);


		// Ensure that Root defined requred constants
		define('WB4_LoadTime', microtime(1) - WB4_StartTime);
	}

	
	// ============================================================================================
	public static function Auto($sPath)
	{
		self::$Loaded_Auto = True;
		require($sPath);
	}
	
	// ============================================================================================
	public static function Scan()
	{
		self::ScanInit();
		self::ScanExec();
	}
	
	// ============================================================================================
	public static function ScanInit()
	{
		self::$Loaded_Init = True;		
		
		//Include the _init.php files
		foreach(self::$_Init as $sFile)
		{
			require($sFile);
		}
	}
		
	// ============================================================================================
	public static function ScanExec()
	{
		self::$Loaded_Exec = True;		
		
		//Include the _exec.php files
		foreach(array_reverse(self::$_Exec) as $sFile)
		{
			require($sFile);
		}
	}
	
	// A convenient dump of relevant WB4 data
	// Easy to override if needed to extend it
	public static function Dump($Return=False)
	{
		$RVAL = array
		(
			'WB4_Path'				=> defined('WB4_Path') 			? WB4_Path 		: '*UNDEFINED*',
			'WB4_DevLevel'			=> defined('WB4_DevLevel') 		? WB4_DevLevel 	: '*UNDEFINED*',
			'WB4_DevName'			=> defined('WB4_DevName') 		? WB4_DevName 	: '*UNDEFINED*',
			
			'WB4_StartTime'			=> defined('WB4_StartTime') 	? WB4_StartTime : '*UNDEFINED*',
			'WB4_LoadTime'			=> defined('WB4_LoadTime') 		? WB4_LoadTime 	: '*UNDEFINED*',
			
			'WB4_CWF'				=> defined('WB4_CWF') 			? WB4_CWF 		: '*UNDEFINED*',
			'WB4_CWD'				=> defined('WB4_CWD') 			? WB4_CWD 		: '*UNDEFINED*',

			'WB4_CLI'				=> defined('WB4_CLI') 			? WB4_CLI 		: '*UNDEFINED*',
			
			'WB4_App::$Identifier'	=> is_null(WB4_App::$Identifier)? '*NULL*' 		: WB4_App::$Identifier,
			'WB4_App::$Path'		=> is_null(WB4_App::$Path)		? '*NULL*' 		: WB4_App::$Path,
		);

		if($Return)
			return $RVAL;
		
		print_r($RVAL);
	}
}


###################################################################################################
class WB4_App
{
	
	public static $Identifier 	= NULL;
	public static $Path 		= NULL;
	
	// A map of ID => Path of where to find Extruct
	public static $Extruct 		= array();

	// A map of ID => Spec object of preloaded Extruct
	public static $_Extruct		= array();

	// A Map of ID => array(FunctionCall, Extruct_Request, Extruct_Response)
	public static $API 		= array();
	
	// An array of mysql connection info
	public static $MySQL 		= NULL;

	// The application server object
	public static $AS = NULL;
	
	// The address and port to connect to 
	public static $AS_Type = NULL;
	public static $AS_Address = NULL;
	public static $AS_Port = NULL;
	
	// The Data Segment that this code is running UNDER.  Must come from 
	// a "secure" source
	public static $DSEG = FALSE;
	
	// The remote address that is talking to this app - defaults to $_SERVER['REMOTE_ADDR']
	public static $ADDR = NULL;
	
	// The AuthToken to send to the AppServer
	public static $AuthToken = FALSE;
	
	
	//============================================================================================
	// Convert Extruct, but look up registered xdata files to load the spec from
	public static function Convert($ID, $DATA, $ConversionType='Native>>Native')
	{
		# If the ID is found in the ID=>Path map, but not found in the cached Extruct...
		if(isset(self::$Extruct[$ID]) and (! isset(self::$_Extruct[$ID])))
			foreach(Extruct::ParseFile(self::$Extruct[$ID]) as $oSpec)
				self::$_Extruct[$oSpec->Name] = $oSpec;
		
		if(! isset(self::$_Extruct[$ID]))
			throw new KeyError("Extruct Spec not found: ".$ID);

		return self::$_Extruct[$ID]->Convert($DATA, $ConversionType);
	}



	//============================================================================================
	public static function Connect()
	{
		if(! WB4::$Loaded)
			throw new InvalidOperation("WB4::Load() must be called prior to connecting to the application server.");
		
		self::$AS = new WB4_AppServer_Connection(self::$AS_Type, self::$AS_Address, self::$AS_Port);
	}

	//============================================================================================
	// CallAPI must pass either a DSEG or AuthToken.  The DSEG must be > 0 if passed.
	public static function CallAPI($ID, $DATA, $Target = '<SELF>')
	{
		if(empty(self::$AuthToken) and (! intval(self::$DSEG)))
			throw new InvalidOperation('WB4_App::$DSEG and/or WB4_App::$AuthToken must be set in order to contact the applications server.');

		# Connect if we are not connected		
		if(! self::$AS)
			self::Connect();
		
		# Form the request packet
		$oPacketO = new WB4_AppServer_RequestPacket();
		$oPacketO->SetDevLevel(WB4_DevLevel);
		$oPacketO->SetDevName(WB4_DevName);
		$oPacketO->SetProjectIdentifier(self::$Identifier);
		$oPacketO->SetDSEG(self::$DSEG);
		$oPacketO->SetADDR(self::$ADDR);
		$oPacketO->SetAuthToken(self::$AuthToken);
		$oPacketO->SetTarget($Target);
		$oPacketO->SetMethod($ID);
		$oPacketO->SetDataType('ExtructSerialize');
		$oPacketO->SetData($DATA);
		
		# Send the packet, receive the response
		self::$AS->SendPacket($oPacketO);
		$oPacketI = self::$AS->RecvPacket();

		# Return the "returned" data.
		return $oPacketI->GetData();
	}
	
	//============================================================================================
	// SelfAPI assumes Target = <SELF>, and DSEG = 0, and AuthToken = NULL
	public static function SelfAPI($ID, $DATA)
	{
		# Connect if we are not connected		
		if(! self::$AS)
			self::Connect();
		
		# Form the request packet
		$oPacketO = new WB4_AppServer_RequestPacket();
		$oPacketO->SetDevLevel(WB4_DevLevel);
		$oPacketO->SetDevName(WB4_DevName);
		$oPacketO->SetProjectIdentifier(self::$Identifier);
		$oPacketO->SetDSEG(0);
		$oPacketO->SetADDR(self::$ADDR);
		$oPacketO->SetTarget('<SELF>');
		$oPacketO->SetMethod($ID);
		$oPacketO->SetDataType('ExtructSerialize');
		$oPacketO->SetData($DATA);
		
		# Send the packet, receive the response
		self::$AS->SendPacket($oPacketO);
		$oPacketI = self::$AS->RecvPacket();

		# Return the "returned" data.
		return $oPacketI->GetData();
	}
}

# Default values
if(isset($_SERVER['REMOTE_ADDR']))
	WB4_App::$ADDR = $_SERVER['REMOTE_ADDR'];


###################################################################################################

class WB4_AppServer_Exception extends Exception{}
class WB4_AppServer_ConnectionLost extends Exception{}
class WB4_AppServer_PacketError extends Exception {}


###################################################################################################
class WB4_AppServer_Connection
{
	const Version = 1;
	
	const Status_New = 1;
	const Status_Active = 2;
	const Status_Closed = 4;
	
	public $PacketDelimiter = "\0";
	public $Type;
	public $Address;
	public $Port;
	public $Status;

	protected $_Socket;
	protected $_Buffer = '';

	#==============================================================================================
	public function __construct($sType, $sAddress, $nPort)
	{
		$this->Status = self::Status_Active;
		
		$this->Type = $sType;
		$this->Address = $sAddress;
		$this->Port = $nPort;

		//Creating socket
		switch($sType)
		{
			case 'AF_UNIX':	
				$this->_Socket = socket_create(AF_UNIX, SOCK_STREAM, 0);		
				break;
				
			case 'AF_INET':
				$this->_Socket = socket_create(AF_INET, SOCK_STREAM, SOL_TCP);		
				break;

			default:
				throw new ValueError("Invalid value '$sType' for socket type.");
		}

		if(! $this->_Socket)
			throw new OSError("socket_create() failed. " . socket_strerror(socket_last_error()));

		
		//Attempting to connect to $this->Address on port $this->Port...
		if(! @socket_connect($this->_Socket, $this->Address, $this->Port)) 
			throw new OSError("socket_connect() failed. " . socket_strerror(socket_last_error()));

		$this->Status = self::Status_Active;
	}


	#==============================================================================================
	// This is a blocking call to send a packet.
	public function SendPacket($oPacket)
	{
		//Ensure our connection is active
		if($this->Status != self::Status_Active)
			throw new InvalidState("The connection status must be Active.");

		$sPacket = $oPacket->ToString();		
		
		if(strpos($this->PacketDelimiter, $sPacket) !== FALSE)
			throw new ValueError("The packet must not contain the packet delimiter.");

		$sPacket .= $this->PacketDelimiter;

		$nLen = strlen($sPacket);
		$nPos = 0;
		$i = 0;
			
		while($nPos < $nLen and $i++ < 1000) //The $i++ is a sanity check
		{
			$nPut = socket_write($this->_Socket, substr($sPacket, $nPos));

			if($nPut === FALSE)
				throw new OSError("socket_write() failed. " . socket_strerror(socket_last_error()));

			$nPos += $nPut;
			
		}

		return $nLen;
	}
	
	#==============================================================================================
	//Receives a packet and returns it
	public function RecvPacket()
	{
		$i = 0;

		//Loop until we have a packet
		while($i++ < 1000) //The $i++ is a sanity check
		{
			# Why is this at the top of the loop?  What if extra data was fetched last time...
			# Perhaps 2 packets were received last time...
			if(($pos = strpos($this->_Buffer, $this->PacketDelimiter)) !== FALSE)
			{
				$sPacket = substr($this->_Buffer, 0, $pos);
				$this->_Buffer = substr($this->_Buffer, $pos+strlen($this->PacketDelimiter));
				break;
			}
			
			#$data = socket_read($this->_Socket, 65536, PHP_BINARY_READ);
			$data = NULL;
			$len = 65536;
			$bytes = socket_recv($this->_Socket, $data, $len, 0);

			if($bytes === FALSE)
				throw new OSError("socket_read() failed. " . socket_strerror(socket_last_error()));

			if($bytes === 0)
			{
				$this->Close();			
				throw new WB4_AppServer_ConnectionLost("Packet read failed due to empty read.");	
			}
				
			$this->_Buffer .= $data;
		}

		
		$oPacket = WB4_AppServer_ParsePacket($sPacket);

		if($oPacket->GetType() == 'Exception')
		{
			switch($oPacket->GetExceptionType())
			{
				case 'GeneralError':
					throw new GeneralError($oPacket->GetMessage(), $oPacket->GetData());
				case 'InvalidOperation':
					throw new InvalidOperation($oPacket->GetMessage());
				case 'ValueError':
					throw new ValueError($oPacket->GetMessage());
				case 'TypeError':
					throw new TypeError($oPacket->GetMessage());
				case 'AuthError':
					throw new AuthError($oPacket->GetMessage());
				case 'SecurityError':
					throw new SecurityError($oPacket->GetMessage());
				case 'ValidationError':
					throw new ValidationError($oPacket->GetData());
				default:
					throw new Exception("Exception received via packet: " . $oPacket->GetExceptionType() . ": " . $oPacket->GetMessage());
			}
		}

		return $oPacket;
	}

	#==============================================================================================
	//Close this connection
	public function Close()
	{
		socket_close($this->_Socket);
		$this->Status = self::Status_Closed;
	}


}


###################################################################################################
function WB4_AppServer_ParsePacket($DATA)
{
	// Second parameter causes json_decode to return assoc arrays
	$DATA = json_decode($DATA, true);

	if(is_null($DATA))
		throw new WB4_AppServer_PacketError("Cannot decode JSON.");
	
	if(! isset($DATA['Type']))
		throw new WB4_AppServer_PacketError("Packet does not have a valid Type attribute.");

	switch($DATA['Type'])
	{
		case 'Response':
			return new WB4_AppServer_ResponsePacket($DATA);
		case 'Exception':
			return new WB4_AppServer_ExceptionPacket($DATA);
		case 'Request':
			throw new WB4_AppServer_PacketError("Reading 'Request' packets is not supported on this platform.");
		default:
			throw new WB4_AppServer_PacketError("Packet does not have a valid Type: $Type");
	}
}

###################################################################################################
class WB4_AppServer_BasePacket
{
	public static $_DataType = array('Native', 'BinaryString', 'ExtructSerialize');
	public static $_Version = 4;
	
	#==============================================================================================
	public function __construct($DATA=NULL)
	{
		$this->_Data = array('Version' => self::$_Version);

		if($DATA)
		{
			if(! isset($DATA['Version']))
				throw new WB4_AppServer_PacketError("Missing key 'Version'.");
			elseif($DATA['Version'] != self::$_Version)
				throw new PacketError("Packet version ".$DATA['Version']." does not match class version ".self::$_Version.".");
				
			if(! isset($DATA['DataType']))
				throw new WB4_AppServer_PacketError("Missing key 'DataType'.");
			else
				$this->_Data['DataType'] = $DATA['DataType'];
			
			if(! isset($DATA['Data']))
				throw new WB4_AppServer_PacketError("Missing key 'Data'.");
			else
				$this->_Data['Data'] = $DATA['Data'];
		}
		else
		{
			$this->_Data['DataType'] 			= 'Native';
			$this->_Data['Data'] 				= array();
		}
	}

	#==============================================================================================
	public function ToString()
	{
		return json_encode($this->_Data);
	}
	
	#==============================================================================================
	public function GetVersion()
	{
		return self::$_Version;
	}
	
	#==============================================================================================
	public function GetType()
	{
		return $this->_Data['Type'];
	}

	#==============================================================================================
	public function GetDataType()
	{
		return (string) $this->_Data['DataType'];
	}
	
	public function SetDataType($value)
	{
		# Warning!  If the datatype is set, the data value will be truncated

		if(! in_array($value, self::$_DataType))
			throw new ValueError("Invalid DataType: " . $value);
		
		$this->_Data['Data'] = '';
		$this->_Data['DataType'] = $value;
	}

	#==============================================================================================
	public function GetData()
	{
		switch($this->GetDataType())
		{
			case 'Native':
				return $this->_Data['Data'];
			case 'ExtructSerialize':
				return Extruct::Unserialize($this->_Data['Data']);
			case 'BinaryString':
				return base64_decode((string) $this->_Data['Data']);
			default:
				throw new ValueError("PANIC: Invalid type for /Packet/Data/Type: " . $this->GetDataType());
		}
	}
	
	public function SetData($value)
	{
		switch($this->GetDataType())
		{
			case 'Native':
				$this->_Data['Data'] = $value;
				break;
			case 'ExtructSerialize':
				$this->_Data['Data'] = Extruct::Serialize($value);
				break;
			case 'BinaryString':
				$this->_Data['Data'] = base64_encode((string) $value);
				break;
			default:
				throw new ValueError("PANIC: Invalid type for /Packet/Data/Type: " . $this->GetDataType());
		}
	}		
}


###################################################################################################
class WB4_AppServer_RequestPacket extends WB4_AppServer_BasePacket
{
	#==============================================================================================
	# PHP does not support loading a request packet because it should never RECEIVE one.
	public function __construct()
	{
		parent::__construct(NULL);
		$this->_Data['Type'] = 'Request';

		$this->_Data['DevLevel'] 			= NULL;
		$this->_Data['DevName'] 			= NULL;
		$this->_Data['ProjectIdentifier'] 	= NULL;
		$this->_Data['DSEG'] 				= NULL;
		$this->_Data['ADDR'] 		= NULL;
		$this->_Data['AuthToken'] 			= NULL;
		$this->_Data['Target'] 				= NULL;
		$this->_Data['Method'] 				= NULL;
		$this->_Data['SecurityContext'] 	= NULL;
	}

	#==============================================================================================
	public function GetDevLevel()
	{
		return $this->_Data['DevLevel'];
	}
	
	public function SetDevLevel($value)
	{
		$this->_Data['DevLevel'] = intval($value);
	}
		
	#==============================================================================================
	public function GetDevName()
	{
		return $this->_Data['DevName'];
	}
	
	public function SetDevName($value)
	{
		$this->_Data['DevName'] = $value;
	}
		
	#==============================================================================================
	public function GetProjectIdentifier()
	{
		return $this->_Data['ProjectIdentifier'];
	}
	
	public function SetProjectIdentifier($value)
	{
		$this->_Data['ProjectIdentifier'] = $value;
	}
		
	#==============================================================================================
	public function GetDSEG()
	{
		return $this->_Data['DSEG'];
	}
	
	public function SetDSEG($value)
	{
		$this->_Data['DSEG'] = (integer) $value;
	}
		
	#==============================================================================================
	public function GetADDR()
	{
		return $this->_Data['ADDR'];
	}
	
	public function SetADDR($value)
	{
		$this->_Data['ADDR'] = $value;
	}
		
	#==============================================================================================
	public function GetAuthToken()
	{
		return $this->_Data['AuthToken'];
	}
	
	public function SetAuthToken($value)
	{
		$this->_Data['AuthToken'] = $value;
	}
	
	#==============================================================================================
	public function GetTarget()
	{
		return $this->_Data['Target'];
	}
	
	public function SetTarget($value)
	{
		$this->_Data['Target'] = (string) $value;
	}
		
	#==============================================================================================
	public function GetMethod()
	{
		return $this->_Data['Method'];
	}
	
	public function SetMethod($value)
	{
		$this->_Data['Method'] = (string) $value;
	}
		
	#==============================================================================================
	public function GetSecurityContext()
	{
		throw new NotImplementedError("Not available on this platform.");
	}
	
	public function SetSecurityContext($value)
	{
		throw new NotImplementedError("Not available on this platform.");
	}
}


###################################################################################################

class WB4_AppServer_ResponsePacket extends WB4_AppServer_BasePacket
{
	#==============================================================================================
	public function __construct($DATA=NULL)
	{
		parent::__construct($DATA);
		$this->_Data['Type'] = 'Response';
	}
}



###################################################################################################

class WB4_AppServer_ExceptionPacket extends WB4_AppServer_BasePacket
{
	public static $Type = 'Response';
	
	#==============================================================================================
	public function __construct($DATA=NULL)
	{
		parent::__construct($DATA);
		$this->_Data['Type'] = 'Exception';

		if($DATA)
		{
			if(! isset($DATA['ExceptionType']))
				throw new WB4_AppServer_PacketError("Missing key 'ExceptionType'.");
			else
				$this->_Data['ExceptionType'] = $DATA['ExceptionType'];
			
			if(! isset($DATA['Message']))
				throw new WB4_AppServer_PacketError("Missing key 'Message'.");
			else
				$this->_Data['Message'] = $DATA['Message'];
		}
		else
		{
			$this->_Data['ExceptionType'] 	= NULL;
			$this->_Data['Message']			 = NULL;
		}
	}

	#==============================================================================================
	public function GetExceptionType()
	{
		return $this->_Data['ExceptionType'];
	}
	
	public function SetExceptionType($value)
	{
		$this->_Data['ExceptionType'] = (string) $value;
	}
		
	#==============================================================================================
	public function GetMessage()
	{
		return base64_decode((string) $this->_Data['Message']);
	}

	public function SetMessage($value)
	{
		$this->_Data['Message'] = base64_encode((string) $value);
	}

}




