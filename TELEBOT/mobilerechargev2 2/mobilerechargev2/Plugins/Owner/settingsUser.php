<?php 

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
    $select = ($UserID['select'] == 1) ? $BOT->language("one") : $BOT->language("two");
    $limit = ($UserID['limit'] == 0) ? $BOT->language("NoLimit") : $UserID['limit'];
    $BOT->sendCommand('editMessageText', [
        'chat_id' => $chatId,
        'message_id' => $messageId, 
        'text' => sprintf($BOT->language("text_settingsUser"),$full_name),
        'reply_markup' => json_encode([
            'inline_keyboard' => [
                [['text' => $select, 'callback_data' => 'changeSelect'."+$User_ID"]],
                [['text' => $UserID['money'], 'callback_data' => 'changeMoney'."+$User_ID"],['text' => $BOT->language("money"), 'callback_data' => '#']],
                [['text' => $limit, 'callback_data' => 'changeLimit'."+$User_ID"],['text' => $BOT->language("limit"), 'callback_data' => '#']],
                [['text' => $UserID['allmoney'], 'callback_data' => '#'],['text' => $BOT->language("allmoney"), 'callback_data' => '#']],
                [['text' => "🗑", 'callback_data' => 'deleteUser'."+$User_ID"],['text' => $BOT->language("report"), 'callback_data' => 'reportUser'."+$User_ID"]],
                [['text' => $BOT->language("Back"), 'callback_data' => 'listUsers+1']]
            ]
        ]) 
    ]);
}



if (preg_match("/^(reportUser)([+])(.*)/s", $data)){
    preg_match("/^(reportUser)([+])(.*)/s", $data, $matcha);
    $User_ID = $matcha[3];
    $UserID = mysqli_fetch_assoc(mysqli_query($db, "SELECT * FROM `users` WHERE `id` ='$User_ID'"));

    $reports = json_decode($UserID['report'],true);
    $res = "";
    foreach ($reports as $report=>$value){
        if(is_array($value) and count($value) != 0){
            $res .= $BOT->language($report)." : \n";
            foreach($value as $n => $t){
                $res .= "• $n:$t\n";
            }
        }else{
            if(!is_array($value)){
                $total = $value;
            }
        }
    }
    $BOT->sendCommand('editMessageText', [
        'chat_id' => $chatId,
        'message_id' => $messageId, 
        'text' => sprintf($BOT->language("reportUser_text"),$total,$res),
        'reply_markup' => json_encode([
            'inline_keyboard' => [
                [['text' => $BOT->language("Back"), 'callback_data' => 'settingsUser+'.$User_ID]]
            ]
        ]) 
    ]);

}

if ($BOT->states($id,'Get1') == "changeLimit" and $messageText != "/start" and $messageText != "/main" and !$data){
    $User_ID = $BOT->states($id,'Get2');
    if (preg_match('/[0-9]/', $messageText) && !preg_match('/[A-Za-z]/', $messageText) && !preg_match('/[ء-ي]/', $messageText)){
        $UserID = mysqli_fetch_assoc(mysqli_query($db, "SELECT * FROM `users` WHERE `id` ='$User_ID'"));
        mysqli_query($db, "UPDATE users SET `limit`='$messageText' WHERE `id`='$User_ID'");
    
        $GetChat = $BOT->GetChat($UserID['from_id']);
        $full_name = $GetChat["result"]["first_name"] . " " . $GetChat["result"]["last_name"];
        if($full_name == " "){
            $full_name = $UserID['from_id'];
        }
        $select = ($UserID['select'] == 1) ? $BOT->language("one") : $BOT->language("two");
        $limit = ($messageText == 0) ? $BOT->language("NoLimit") : $messageText;
        $BOT->sendCommand('sendmessage', [
            'chat_id' => $chatId,
            'text' => sprintf($BOT->language("text_settingsUser"),$full_name),
            'reply_markup' => json_encode([
                'inline_keyboard' => [
                    [['text' => $select, 'callback_data' => 'changeSelect'."+$User_ID"]],
                    [['text' => $UserID['money'], 'callback_data' => 'changeMoney'."+$User_ID"],['text' => $BOT->language("money"), 'callback_data' => '#']],
                    [['text' => $limit, 'callback_data' => 'changeLimit'."+$User_ID"],['text' => $BOT->language("limit"), 'callback_data' => '#']],
                    [['text' => $UserID['allmoney'], 'callback_data' => '#'],['text' => $BOT->language("allmoney"), 'callback_data' => '#']],
                    [['text' => "🗑", 'callback_data' => 'deleteUser'."+$User_ID"],['text' => $BOT->language("report"), 'callback_data' => 'reportUser'."+$User_ID"]],
                    [['text' => $BOT->language("Back"), 'callback_data' => 'listUsers+1']]
                ]
            ]) 
        ]);
        $BOT->states($id,'delete');
    }else{
        $BOT->sendCommand('sendmessage', ['chat_id' => $chatId, 'text' => $BOT->language("errorNumbers"), 'reply_markup' => json_encode(['inline_keyboard' => [[['text' => $BOT->language("Cancel"), 'callback_data' => 'settingsUser+'.$User_ID]]]]) ]);
    }
}
if (preg_match("/^(changeLimit)([+])(.*)/s", $data)){
    preg_match("/^(changeLimit)([+])(.*)/s", $data, $matcha);
    $User_ID = $matcha[3];
    $BOT->states($id,'insert','changeLimit',$User_ID);
    $BOT->sendCommand('editMessageText', [
        'chat_id' => $chatId,
        'message_id' => $messageId, 
        'text' => $BOT->language("changeLimit"), 
        'disable_web_page_preview' => 'true', 
        'parse_mode' => 'Markdown', 
        'reply_markup' => json_encode([
            'inline_keyboard' => [
                [['text' => $BOT->language("Cancel"), 'callback_data' => 'settingsUser+'.$User_ID]]
            ]
        ]) 
    ]);
}

if ($BOT->states($id,'Get1') == "changeMoney" and $messageText != "/start" and $messageText != "/main" and !$data){
    $User_ID = $BOT->states($id,'Get2');
    if (preg_match('/[0-9-+]/', $messageText) && !preg_match('/[A-Za-z]/', $messageText) && !preg_match('/[ء-ي]/', $messageText)){
        $UserID = mysqli_fetch_assoc(mysqli_query($db, "SELECT * FROM `users` WHERE `id` ='$User_ID'"));

        $NewNumber = $UserID['money'];
        $NewNumber -= $messageText;

        // notifications User
        $BOT->sendCommand('sendmessage', [
            'chat_id' => $UserID['from_id'], 
            'text' => sprintf($BOT->language("notificationsChangeMony"),$messageText, $NewNumber)
        ]);
        mysqli_query($db, "UPDATE users SET `money`='$NewNumber' WHERE `id`='$User_ID'");
    
        $GetChat = $BOT->GetChat($UserID['from_id']);
        $full_name = $GetChat["result"]["first_name"] . " " . $GetChat["result"]["last_name"];
        if($full_name == " "){
            $full_name = $UserID['from_id'];
        }
        $select = ($UserID['select'] == 1) ? $BOT->language("one") : $BOT->language("two");
        $limit = ($UserID['limit'] == 0) ? $BOT->language("NoLimit") : $UserID['limit'];
        $BOT->sendCommand('sendmessage', [
            'chat_id' => $chatId,
            'text' => sprintf($BOT->language("text_settingsUser"),$full_name),
            'reply_markup' => json_encode([
                'inline_keyboard' => [
                    [['text' => $select, 'callback_data' => 'changeSelect'."+$User_ID"]],
                    [['text' => $NewNumber, 'callback_data' => 'changeMoney'."+$User_ID"],['text' => $BOT->language("money"), 'callback_data' => '#']],
                    [['text' => $limit, 'callback_data' => 'changeLimit'."+$User_ID"],['text' => $BOT->language("limit"), 'callback_data' => '#']],
                    [['text' => $UserID['allmoney'], 'callback_data' => '#'],['text' => $BOT->language("allmoney"), 'callback_data' => '#']],
                    [['text' => "🗑", 'callback_data' => 'deleteUser'."+$User_ID"],['text' => $BOT->language("report"), 'callback_data' => 'reportUser'."+$User_ID"]],
                    [['text' => $BOT->language("Back"), 'callback_data' => 'listUsers+1']]
                ]
            ]) 
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

if (preg_match("/^(changeSelect)([+])(.*)/s", $data)){
    preg_match("/^(changeSelect)([+])(.*)/s", $data, $matcha);
    $User_ID = $matcha[3];

    $UserID = mysqli_fetch_assoc(mysqli_query($db, "SELECT * FROM `users` WHERE `id` ='$User_ID'"));
    $ToSelect = ($UserID['select'] == 1) ? 2 : 1;
    mysqli_query($db, "UPDATE users SET `select`='$ToSelect' WHERE `id`='$User_ID'");

    $GetChat = $BOT->GetChat($UserID['from_id']);
    $full_name = $GetChat["result"]["first_name"] . " " . $GetChat["result"]["last_name"];
    if($full_name == " "){
        $full_name = $UserID['from_id'];
    }
    $select = ($ToSelect == 1) ? $BOT->language("one") : $BOT->language("two");

    $limit = ($UserID['limit'] == 0) ? $BOT->language("NoLimit") : $UserID['limit'];
    $BOT->sendCommand('editMessageText', [
        'chat_id' => $chatId,
        'message_id' => $messageId, 
        'text' => sprintf($BOT->language("text_settingsUser"),$full_name),
        'reply_markup' => json_encode([
            'inline_keyboard' => [
                [['text' => $select, 'callback_data' => 'changeSelect'."+$User_ID"]],
                [['text' => $UserID['money'], 'callback_data' => 'changeMoney'."+$User_ID"],['text' => $BOT->language("money"), 'callback_data' => '#']],
                [['text' => $limit, 'callback_data' => 'changeLimit'."+$User_ID"],['text' => $BOT->language("limit"), 'callback_data' => '#']],
                [['text' => $UserID['allmoney'], 'callback_data' => '#'],['text' => $BOT->language("allmoney"), 'callback_data' => '#']],
                [['text' => "🗑", 'callback_data' => 'deleteUser'."+$User_ID"],['text' => $BOT->language("report"), 'callback_data' => 'reportUser'."+$User_ID"]],
                [['text' => $BOT->language("Back"), 'callback_data' => 'listUsers+1']]
            ]
        ]) 
    ]);
}

if (preg_match("/^(deleteUser)([+])(.*)/s", $data)){
    preg_match("/^(deleteUser)([+])(.*)/s", $data, $matcha);
    $User_ID = $matcha[3];
    mysqli_query($db, "DELETE FROM `users` WHERE `id`='$User_ID'");

    $Users = $BOT->Users('count');
    $keyboard = [];
    $i = 0;
    if($Users != 0){
        $Users = $BOT->Users('view');
        $Pagination = Pagination(1, $Users, "listUsers");
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
    $keyboard[$i] = [['text' => $BOT->language("Back") , 'callback_data' => 'Users']];
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