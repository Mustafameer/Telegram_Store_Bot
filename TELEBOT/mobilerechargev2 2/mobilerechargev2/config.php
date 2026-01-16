<?php
date_default_timezone_set("Asia/Baghdad");
mysqli_query("SET NAMES utf8");
mysqli_query("SET CHARACTER SET utf8");

define('API_KEY', "1127341833:AAHHpf_rrxrsr70g07Xxz4flDSPWcJZ4eEg");
$API_KEYVAR = API_KEY;
define('IDBot', explode(":", API_KEY) [0]);

$Host = "localhost";
$UserName = "root";
$PassWord = '';
$DBName = "mr";
$db = mysqli_connect($Host, $UserName, $PassWord, $DBName);