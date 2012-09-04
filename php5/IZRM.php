<?php
/*
Environment Manipulations...

IZRM_PATH, if defined, will override the location of this file.


*/
if(isset($_SERVER['IZRM_PATH']) and ! defined('IZRM_Relocated'))
{
	define('IZRM_Relocated', 1);
	require($_SERVER['IZRM_PATH'] . '/Server/IZRM.php');
}
else
{
	# Standard PHP extentions
	class AttributeError extends Exception{}
	class IOError extends Exception{}
	class ImportError extends Exception{}
	class IndexError extends Exception{}
	class KeyError extends Exception{}
	class NameError extends Exception{}
	class NotImplementedError extends Exception{}
	class OSError extends Exception{}
	class TypeError extends Exception{}
	class ValueError extends Exception{}

	class InvalidOperation extends Exception{}
	class AuthError extends Exception{}
	class SecurityError extends Exception{}

	class ValidationError extends Exception
	{
		public function __construct($aErrors)
		{
			$this->Error = $aErrors;
			parent::__construct('Data validation error.');
		}
	}

	class GeneralError extends Exception
	{
		public function __construct($sMessage, $eData)
		{
			$this->Data = $eData;
			parent::__construct($sMessage);
		}
	}


	class Import
	{
		public static $_AutoLoad = array();
		public static $_Imported = array();

		public static function Load($sName)
		{
			if(! isset(self::$_AutoLoad[$sName]))
				throw new ImportError("Cannot import module with name '$sName'.");

			if(! isset(self::$_Imported[$sName]))
			{
				self::$_Imported[$sName] = True;
				require(self::$_AutoLoad[$sName]);
			}
		}

		public static function Push($sName, $sPath)
		{
			self::$_AutoLoad[$sName] = $sPath;
		}

		public static function Auto()
		{
			function __autoload($sClass)
			{
				Import::Load($sClass);
			}
		}
	}


	# IZRM extentions
	class IZRM
	{
		public static $Path;

	}

	IZRM::$Path = dirname(__FILE__);
	
	Import::Push('Extruct', IZRM::$Path . '/Extruct/__init__.php');
	Import::Push('WB4', IZRM::$Path . '/WB4/__init__.php');
}

