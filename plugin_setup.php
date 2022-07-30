<?php
include_once "/opt/fpp/www/common.php"; //Alows use of FPP Functions
$pluginName = basename(dirname(__FILE__));
$pluginConfigFile = $settings['configDirectory'] ."/plugin." .$pluginName; //gets path to configuration files for plugin
    
if (file_exists($pluginConfigFile)) {
	$pluginSettings = parse_ini_file($pluginConfigFile);
}

$madeChange = false;

if (strlen(urldecode($pluginSettings['press2play_volume']))<1){
	WriteSettingToFile("press2play_volume","70",$pluginName);
	$madeChange = true;
}

if (strlen(urldecode($pluginSettings['press2play_playername']))<1){
	WriteSettingToFile("press2play_playername","FPP",$pluginName);
	$madeChange = true;
}

if (strlen(urldecode($pluginSettings['press2play_mqtt_hostname']))<1){
	WriteSettingToFile("press2play_mqtt_hostname","localhost",$pluginName);
	$madeChange = true;
}

if (strlen(urldecode($pluginSettings['press2play_mqtt_portnumber']))<1){
	WriteSettingToFile("press2play_mqtt_portnumber","1883",$pluginName);
	$madeChange = true;
}

if (strlen(urldecode($pluginSettings['press2play_gpio_buttonpin']))<1){
	WriteSettingToFile("press2play_gpio_buttonpin","26",$pluginName);
	$madeChange = true;
}

if (strlen(urldecode($pluginSettings['press2play_gpio_ledpin']))<1){
	WriteSettingToFile("press2play_gpio_ledpin","18",$pluginName);
	$madeChange = true;
}

if (strlen(urldecode($pluginSettings['press2play_gpio_debounce']))<1){
	WriteSettingToFile("press2play_gpio_debounce","0.3",$pluginName);
	$madeChange = true;
}

if ($madeChange) {
	$pluginSettings = parse_ini_file($pluginConfigFile);
}

$button_gpio_list = Array(3, 5, 7, 8, 10, 11, 12, 13, 15, 16, 17, 18, 19, 21, 22, 23, 24, 25, 26, 27, 28, 29, 31, 32, 33, 34, 35, 36, 37, 38, 40);
$led_gpio_list = Array(12, 13, 18)

?>


<!DOCTYPE html>
<html>
<head>

</head>
<body>
<div class="pluginBody" style="margin-left: 1em;">
	<div class="title">
		<h1>Press2Play</h1>
		<h4></h4>
	</div>

<p>Press F1 for setup instructions</p>
<table cellspacing="5">

<tr>
	<th style="text-align: left">Volume</th>
<td>
<?
//function PrintSettingTextSaved($setting, $restart = 1, $reboot = 0, $maxlength = 32, $size = 32, $pluginName = "", $defaultValue = "", $callbackName = "", $changedFunction = "", $inputType = "text", $sData = Array())
	PrintSettingTextSaved("press2play_volume", $restart = 1, $reboot = 0, $maxlength = 100, $size = 1, $inputType = "number", $pluginName = $pluginName, $defaultValue = "70");
?>
</td>
</tr>

<tr>
	<th style="text-align: left">FPP Player hostname</th>
<td>
<?
//function PrintSettingPasswordSaved($setting, $restart = 1, $reboot = 0, $maxlength = 32, $size = 32, $pluginName = "", $defaultValue = "", $callbackName = "", $changedFunction = "")
	PrintSettingPasswordSaved("press2play_playername", $restart = 1, $reboot = 0, $maxlength = 50, $size = 32, $pluginName = $pluginName, $defaultValue = "FPP");
?>
</td>
</tr>


<tr>
	<th style="text-align: left">MQTT broker</th>
<td>
<?
//function PrintSettingTextSaved($setting, $restart = 1, $reboot = 0, $maxlength = 32, $size = 32, $pluginName = "", $defaultValue = "", $callbackName = "", $changedFunction = "", $inputType = "text", $sData = Array())
	PrintSettingTextSaved("press2play_mqtt_hostname", $restart = 1, $reboot = 0, $maxlength = 32, $size = 32, $pluginName = $pluginName, $defaultValue = "localhost");
?>
</td>
</tr>

<tr>
	<th style="text-align: left">MQTT port number</th>
<td>
<?
//function PrintSettingTextSaved($setting, $restart = 1, $reboot = 0, $maxlength = 32, $size = 32, $pluginName = "", $defaultValue = "", $callbackName = "", $changedFunction = "", $inputType = "text", $sData = Array())
	PrintSettingTextSaved("press2play_mqtt_portnumber", $restart = 1, $reboot = 0, $maxlength = 10000, $size = 1, $inputType = "number", $pluginName = $pluginName, $defaultValue = "1883");
?>
</td>
</tr>


<tr>
	<th style="text-align: left">Button GPIO pin</th>
<td>
<?
//function PrintSettingTextSaved($setting, $restart = 1, $reboot = 0, $maxlength = 32, $size = 32, $pluginName = "", $defaultValue = "", $callbackName = "", $changedFunction = "", $inputType = "text", $sData = Array())
	PrintSettingSelect("Button GPIO pin", "button_gpio_list", $restart = 1, $reboot = 0, "26", $playlists, $pluginName);	
?>
</td>
</tr>

<tr>
	<th style="text-align: left">Button debounce time (s)</th>
<td>
<?
	// function PrintSettingSelect($title, $setting, $restart = 1, $reboot = 0, $defaultValue, $values, $pluginName = "", $callbackName = "", $changedFunction = "", $sData = Array())
	PrintSettingTextSaved("press2play_gpio_debounce", $restart = 1, $reboot = 0, $maxlength = 1, $size = 0, $inputType = "number", $pluginName = $pluginName, $defaultValue = "0.3");
?>
</td>
</tr>

<tr>
	<th style="text-align: left">LED GPIO pin</th>
<td>
<?
	PrintSettingSelect("LED GPIO pin", "led_gpio_list", $restart = 1, $reboot = 0, "18", $playlists, $pluginName);
?>
</td>
</tr>

</table>



</body>
</html>