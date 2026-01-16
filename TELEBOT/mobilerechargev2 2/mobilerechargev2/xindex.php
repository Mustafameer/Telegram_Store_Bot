<?php

function is_telegram(){
  if (isset($_SERVER['HTTP_CF_CONNECTING_IP'])) { 
      $ip = $_SERVER['HTTP_CF_CONNECTING_IP'];
  } else {
      $ip = $_SERVER['REMOTE_ADDR'];
  }
  if (($ip >= '149.154.160.0' && $ip <= '149.154.175.255') || ($ip >= '91.108.4.0' && $ip <= '91.108.7.255')) {
      return true;
  } else {
      return false;
  }
}

if (is_telegram() === false) {
  http_response_code(403);
  echo '403 - You are not Telegram';
  return 'Not Telegram';
}

/* Updates */
$update = file_get_contents("php://input");
$updateData = json_decode($update,true);
$updebug = $updateData;
$messageData = isset($updateData["callback_query"]) ? $updateData["callback_query"] : $updateData["message"];
$messageTime = $messageData["date"];

$chatId = isset($updateData["callback_query"]) ? $updateData["callback_query"]["message"]["chat"]["id"] : $updateData["message"]["chat"]["id"];
$chatName = isset($updateData["callback_query"]) ? $updateData["callback_query"]["message"]["chat"]["title"] : $updateData["message"]["chat"]["title"];
$chatType = isset($updateData["callback_query"]) ? $updateData["callback_query"]["message"]["chat"]["type"] : $updateData["message"]["chat"]["type"];

$messageId = isset($updateData["callback_query"]) ? $updateData["callback_query"]["message"]["message_id"] : $updateData["message"]["message_id"];

$messageText = $messageData["text"];

$reply = $messageData["reply_to_message"];
$replyID = $messageData["reply_to_message"]["from"]["id"];

$data = $updateData["callback_query"]["data"];
$from_id = $messageData["from"]["id"];
$from_name = $messageData["from"]["first_name"] . " " . $messageData["from"]["last_name"];
$from_username = $messageData["from"]["username"];

$forwardFromChat = $messageData["forward_from_chat"];

// Media
$caption = $messageData['caption'];

$sticker = $messageData["sticker"];
$sticker_id = $messageData["sticker"]["file_id"];
$voice = $messageData["voice"];
$voice_id = $messageData["voice"]["file_id"];
$file = $messageData["document"];
$file_id = $messageData["document"]["file_id"];
$audio = $messageData["audio"];
$audio_id = $messageData["audio"]["file_id"];
$video = $messageData["video"];
$video_id = $messageData["video"]["file_id"];
$photo = $messageData["photo"];
$photo_id = end($messageData["photo"])["file_id"];
$videonote = $messageData["video_note"];
$videonote_id = $messageData["video_note"]["file_id"];


$inlineqt = $updateData['inline_query']['query'];
$inlineid = $updateData['inline_query']['id'];
$callbackid = $updateData['callback_query']['id'];
$inline_message_id = $updateData['callback_query']['inline_message_id'];
/* EndUpdates */

// Control
require_once 'config.php';
require_once 'Control/main.class.php';
require_once 'Control/pagination/vendor/autoload.php';
use TelegramBot\InlineKeyboardPagination\InlineKeyboardPagination;

$BOT = new Main(API_KEY);
function Pagination($selected_page, $items, $commandset)
{
    $command = 'Pagination';
    $labels = ['default' => '%d', 'first' => '« %d', 'previous' => '‹ %d', 'current' => '· %d ·', 'next' => '%d ›', 'last' => '%d »', ];
    $callback_data_format = $commandset . '+{NEW_PAGE}';
    $ikp = new InlineKeyboardPagination($items, $command);
    $ikp->setMaxButtons(7, true);
    $ikp->setLabels($labels);
    $ikp->setCallbackDataFormat($callback_data_format);
    return $ikp->getPagination($selected_page);
}

$status = json_decode($BOT->bot("status", "Get") , true);
$Ok = $status['ok'];
if(!$Ok){
if($updateData['inline_query']['from']['id'] != $Admin and $from_id != $Admin){
  $Replymessage = "تحت الصيانة 🚫
🚫 Under maintenance";
if($data){
  $BOT->sendCommand('editMessageText',[
   'chat_id'=>$chatId,
    'message_id'=>$messageId,
   'text'=>$Replymessage,
   'parse_mode'=>'Markdown'
     ]);
}else{
  $BOT->sendCommand('sendmessage',[
   'chat_id'=>$chatId,
   'text'=>$Replymessage,
   'parse_mode'=>'Markdown'
     ]);
}
return false;
}
}


$owners = json_decode($BOT->bot("owners", "Get") , true);
$admins = json_decode($BOT->bot("admins", "Get") , true);

if(in_array($from_id,$owners) or in_array($from_id,$admins)){
  $user = mysqli_fetch_assoc(mysqli_query($db, "SELECT * FROM `users` WHERE `from_id` ='$from_id'"));
  $id = $user['id'];
  $status = $user['status'];
}else{
  $user = mysqli_fetch_assoc(mysqli_query($db, "SELECT * FROM `users` WHERE `from_id` ='$from_id' AND `status`=1"));
  $id = $user['id'];
  $status = 1;
}

if($user){
  if(($user and $status) or in_array($from_id,$owners)){
  foreach(glob("Plugins/User/*.php") as $plugin){
      include_once $plugin;
  }
  }else{
    if ($messageText == "/start" and in_array($from_id,$admins)){
          $BOT->sendCommand('sendmessage', ['chat_id' => $chatId, 'text' => $BOT->language("StartUAdmin")]); 
    }
  }

  if(in_array($from_id,$owners)){
    foreach(glob("Plugins/Owner/*.php") as $plugin){
      include_once $plugin;
    }
  }

  if(in_array($from_id,$admins)){
    foreach(glob("Plugins/Admin/*.php") as $plugin){
      include_once $plugin;
    }
  }
}else{
  if($chatId != ""){
    $BOT->sendCommand('sendmessage', ['chat_id' => $chatId, 'text' => $BOT->language("notfounduser")]); 
    
    //NOTIFICATIONS OWNERS
    foreach($owners as $owner){
      $BOT->sendCommand('sendmessage', [
          'chat_id' => $owner, 
          'text' => sprintf($BOT->language("notfounduserowner"),$from_name,$chatId, $chatId), 
          'disable_web_page_preview' => 'true', 
          'parse_mode' => 'Markdown'
      ]);
    }
  }
}

// $BOT->sendCommand('sendmessage', [
//   "chat_id" => 204378180,
//   "text" => json_encode($updebug),
// ],false);

?>