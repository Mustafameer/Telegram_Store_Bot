<?php 

if($data == "Admins"){
    $BOT->states($id,'delete');
    $BOT->sendCommand('editMessageText', [
        'chat_id' => $chatId,
        'message_id' => $messageId, 
        'text' => $BOT->language("Admins").".", 
        'disable_web_page_preview' => 'true', 
        'parse_mode' => 'Markdown', 
        'reply_markup' => json_encode([
            'inline_keyboard' => [
                [['text' => '➕', 'callback_data' => 'addAdmin'], ['text' => $BOT->language("Admins"), 'callback_data' => 'listAdmins+1']],
                [['text' => $BOT->language("Back"), 'callback_data' => 'main']]
            ]
        ]) 
    ]);
}

if (preg_match("/^(deleteAdmin)([+])(.*)/s", $data)){
    preg_match("/^(deleteAdmin)([+])(.*)/s", $data, $matcha);
    $from_idAdmin = $matcha[3];

    $CheckUser = mysqli_fetch_assoc(mysqli_query($db, "SELECT * FROM `users` WHERE `from_id` ='$from_idAdmin'"));
    if($CheckUser){
        if($CheckUser['status'] == 0){
            mysqli_query($db, "DELETE FROM `users` WHERE `from_id`='$from_idAdmin'");
        }
    }

    if(in_array($from_idAdmin,$admins)){
        $key = array_search($from_idAdmin, $admins);
        if ($key !== false) {
            unset($admins[$key]);
            $admins = array_values($admins);
            $arrnew = json_encode($admins, JSON_UNESCAPED_UNICODE);
            $arrnew = mysqli_real_escape_string($db, $arrnew);
            $BOT->bot("admins", "Set", $arrnew);
        }
    }

    $Users = $BOT->Admins('count');
    $keyboard = [];
    $i = 0;
    if($Users != 0){
        $Users = $BOT->Admins('view');
        $Pagination = Pagination(1, $Users, "listAdmins");
        $arrs = $Pagination['items'];
        foreach($arrs as $arr){
            $Ibotton = ["text" =>  $arr['full_name'], "callback_data" => 'deleteAdmin+'.$arr['from_id']];
            $keyboard[$i][] = $Ibotton;
            $i++;
        }
        $keyboard[$i] = $Pagination['keyboard'];
        $i++;
        $text = $BOT->language("listAdmins");
    }else{
        $text = $BOT->language("NoAdmins");
    }
    $keyboard[$i] = [['text' => $BOT->language("Back") , 'callback_data' => 'Admins']];
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

if (preg_match("/^(listAdmins)([+])(.*)/s", $data)){
    preg_match("/^(listAdmins)([+])(.*)/s", $data, $matcha);
    $sp = $matcha[3];
    $BOT->states($id,'delete');
    $Users = $BOT->Admins('count');
    $keyboard = [];
    $i = 0;
    if($Users != 0){
        $Users = $BOT->Admins('view');
        $Pagination = Pagination($sp, $Users, "listAdmins");
        $arrs = $Pagination['items'];
        foreach($arrs as $arr){
            $Ibotton = ["text" =>  $arr['full_name'], "callback_data" => 'deleteAdmin+'.$arr['from_id']];
            $keyboard[$i][] = $Ibotton;
            $i++;
        }
        $keyboard[$i] = $Pagination['keyboard'];
        $i++;
        $text = $BOT->language("listAdmins");
    }else{
        $text = $BOT->language("NoAdmins");
    }
    $keyboard[$i] = [['text' => $BOT->language("Back") , 'callback_data' => 'Admins']];
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

if ($BOT->states($id,'Get1') == "addAdmin" and $messageText != "/start" and $messageText != "/main" and !$data){
    if (preg_match('/[0-9]/', $messageText) && !preg_match('/[A-Za-z]/', $messageText) && !preg_match('/[ء-ي]/', $messageText)){
        $messageText = (int)$messageText;
        $GetChat = $BOT->GetChat($messageText);
        if($GetChat['ok']){
            $full_name = $GetChat["result"]["first_name"] . " " . $GetChat["result"]["last_name"];

            $CheckUser = mysqli_fetch_assoc(mysqli_query($db, "SELECT * FROM `users` WHERE `from_id` ='$messageText'"));
            if(!$CheckUser){
                $report = '{"asiacell":{},"zain":{},"korek":{},"iraqsell":{},"alkafil":{},"creditrequest":{},"others":{},"netzain":{},"netasiacell":{},"total":"0"}';
                $report = mysqli_real_escape_string($db, $report);

                mysqli_query($db, "INSERT INTO `users` (`id`, `status`, `from_id`, `select`, `money`, `allmoney`, `limit`, `report`) VALUES (NULL, 0, '$messageText', '1', '0', '0', '0', '$report');");
                $id = mysqli_insert_id($db);
            }

            if(!in_array($messageText,$admins)){
                $admins[] = $messageText;
                $arrnew = json_encode($admins, JSON_UNESCAPED_UNICODE);
                $arrnew = mysqli_real_escape_string($db, $arrnew);
                $BOT->bot("admins", "Set", $arrnew);
            }

            $BOT->sendCommand('sendmessage', [
                'chat_id' => $chatId,
                'text' => sprintf($BOT->language("doneAddAdmin"),$full_name), 
                'disable_web_page_preview' => 'true', 
                'parse_mode' => 'Markdown', 
                'reply_markup' => json_encode([
                    'inline_keyboard' => [
                        [['text' => '➕', 'callback_data' => 'addAdmin'], ['text' => $BOT->language("Admins"), 'callback_data' => 'listAdmins+1']],
                        [['text' => $BOT->language("Back"), 'callback_data' => 'main']]
                    ]
                ]) 
            ]);
            $BOT->states($id,'delete');
        }else{
            $BOT->sendCommand('sendmessage', ['chat_id' => $chatId, 'text' => $BOT->language("erroraddUser2"), 'reply_markup' => json_encode(['inline_keyboard' => [[['text' => $BOT->language("Cancel"), 'callback_data' => 'Admins']]]]) ]);
        }
    }else{
        $BOT->sendCommand('sendmessage', ['chat_id' => $chatId, 'text' => $BOT->language("erroraddUser1"), 'reply_markup' => json_encode(['inline_keyboard' => [[['text' => $BOT->language("Cancel"), 'callback_data' => 'Admins']]]]) ]);
    }
}

if($data == "addAdmin"){
    $BOT->states($id,'insert','addAdmin');
    $BOT->sendCommand('editMessageText', [
        'chat_id' => $chatId,
        'message_id' => $messageId, 
        'text' => $BOT->language("addAdmin"), 
        'disable_web_page_preview' => 'true', 
        'parse_mode' => 'Markdown', 
        'reply_markup' => json_encode([
            'inline_keyboard' => [
                [['text' => $BOT->language("Cancel"), 'callback_data' => 'Admins']]
            ]
        ]) 
    ]);
}