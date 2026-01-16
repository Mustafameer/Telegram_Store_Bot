<?php

if (preg_match("/^(Users)([+])(.*)/s", $data)){
    preg_match("/^(Users)([+])(.*)/s", $data, $matcha);
    $sp = $matcha[3];
    $BOT->states($id,'delete');
    $Users = $BOT->Users('count');
    $keyboard = [];
    $i = 0;
    if($Users != 0){
        $Users = $BOT->Users('view');
        $Pagination = Pagination($sp, $Users, "Users");
        $arrs = $Pagination['items'];
        foreach($arrs as $arr){
            $Ibotton = ["text" =>  $arr['full_name'], "callback_data" => 'settingsUser+'.$arr['id']];
            $keyboard[$i][] = $Ibotton;
            $i++;
        }
        $keyboard[$i] = $Pagination['keyboard'];
        $i++;
        $text = $BOT->language("Users").".";
    }else{
        $text = $BOT->language("NoUsers");
    }
    $keyboard[$i] = [['text' => $BOT->language("Back") , 'callback_data' => 'main']];
    $BOT->sendCommand('editMessageText',[
        'chat_id'=>$chatId,
        'message_id' => $messageId,
        'text'=>$text,
        'parse_mode'=>"Markdown",
     'disable_web_page_preview'=>'true',
     'reply_markup' =>json_encode([
        'inline_keyboard' => $keyboard
    ])
    ]);
}

if (preg_match("/^(settingsUser)([+])(.*)/s", $data)){
    preg_match("/^(settingsUser)([+])(.*)/s", $data, $matcha);
    $User_ID = $matcha[3];
    $BOT->states($id,'delete');
    $UserID = mysqli_fetch_assoc(mysqli_query($db, "SELECT * FROM `users` WHERE `id` ='$User_ID'"));
    $GetChat = $BOT->GetChat($UserID['from_id']);
    $full_name = $GetChat["result"]["first_name"] . " " . $GetChat["result"]["last_name"];
    if($full_name == " "){
        $full_name = $UserID['from_id'];
    }
    $BOT->sendCommand('editMessageText', [
        'chat_id' => $chatId,
        'message_id' => $messageId, 
        'text' => sprintf($BOT->language("settingsUserAdmin"),$full_name),
        'reply_markup' => json_encode([
            'inline_keyboard' => [
                [['text' => $UserID['money'], 'callback_data' => 'changeMoney'."+$User_ID"],['text' => $BOT->language("money"), 'callback_data' => '#']],
                [['text' => $BOT->language("Back"), 'callback_data' => 'Users+1']]
            ]
        ]) 
    ]);
}


if ($BOT->states($id,'Get1') == "changeMoney" and $messageText != "/start" and $messageText != "/main" and !$data){
    $User_ID = $BOT->states($id,'Get2');
    if (preg_match('/[0-9]/', $messageText) && !preg_match('/[A-Za-z]/', $messageText) && !preg_match('/[ء-ي]/', $messageText)){
        $UserID = mysqli_fetch_assoc(mysqli_query($db, "SELECT * FROM `users` WHERE `id` ='$User_ID'"));


        $NewNumber = $UserID['money'];
        $NewNumber -= $messageText;

        mysqli_query($db, "UPDATE users SET `money`='$NewNumber' WHERE `id`='$User_ID'");
    
        $GetChat = $BOT->GetChat($UserID['from_id']);
        $full_name = $GetChat["result"]["first_name"] . " " . $GetChat["result"]["last_name"];
        if($full_name == " "){
            $full_name = $UserID['from_id'];
        }
        $BOT->sendCommand('sendmessage', [
            'chat_id' => $chatId,
            'text' => sprintf($BOT->language("settingsUserAdmin"),$full_name),
            'reply_markup' => json_encode([
                'inline_keyboard' => [
                    [['text' => $NewNumber, 'callback_data' => 'changeMoney'."+$User_ID"],['text' => $BOT->language("money"), 'callback_data' => '#']],
                    [['text' => $BOT->language("Back"), 'callback_data' => 'Users+1']]
                ]
            ]) 
        ]);

        // notifications User
        $BOT->sendCommand('sendmessage', [
            'chat_id' => $UserID['from_id'], 
            'text' => sprintf($BOT->language("notificationsChangeMony"),$messageText, $NewNumber)
        ]);
        
        // notifications OWNER
        $usermarkdown = "[$full_name](tg://user?id=".$UserID['from_id'].") ".$UserID['from_id'];
        $admin = "[$from_name](tg://user?id=$chatId)";
        $BOT->sendCommand('sendmessage', [
            'chat_id' => $owners[0], 
            'text' => sprintf($BOT->language("notificationsOwnerChangeMony"),$usermarkdown, $admin, $UserID['money'], $messageText ), 
            'disable_web_page_preview' => 'true', 
            'parse_mode' => 'Markdown'
        ]);

        $BOT->states($id,'delete');
    }else{
        $BOT->sendCommand('sendmessage', ['chat_id' => $chatId, 'text' => $BOT->language("errorNumbers"), 'reply_markup' => json_encode(['inline_keyboard' => [[['text' => $BOT->language("Cancel"), 'callback_data' => 'settingsUser+'.$User_ID]]]]) ]);
    }
}
if (preg_match("/^(changeMoney)([+])(.*)/s", $data)){
    preg_match("/^(changeMoney)([+])(.*)/s", $data, $matcha);
    $User_ID = $matcha[3];
    $BOT->states($id,'insert','changeMoney',$User_ID);
    $BOT->sendCommand('editMessageText', [
        'chat_id' => $chatId,
        'message_id' => $messageId, 
        'text' => $BOT->language("changeMoney"), 
        'disable_web_page_preview' => 'true', 
        'parse_mode' => 'Markdown', 
        'reply_markup' => json_encode([
            'inline_keyboard' => [
                [['text' => $BOT->language("Cancel"), 'callback_data' => 'settingsUser+'.$User_ID]]
            ]
        ]) 
    ]);
}
