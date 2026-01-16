<?php 


if ($data == "Users")
{
    $BOT->states($id,'delete');
    $BOT->sendCommand('editMessageText', [
        'chat_id' => $chatId,
        'message_id' => $messageId, 
        'text' => $BOT->language("Users").".", 
        'disable_web_page_preview' => 'true', 
        'parse_mode' => 'Markdown', 
        'reply_markup' => json_encode([
            'inline_keyboard' => [
                [['text' => '➕', 'callback_data' => 'addUser'], ['text' => $BOT->language("Users"), 'callback_data' => 'listUsers+1']],
                [['text' => $BOT->language("Back"), 'callback_data' => 'main']]
            ]
        ]) 
    ]);
}
if ($BOT->states($id,'Get1') == "addUser" and $messageText != "/start" and $messageText != "/main" and !$data){
    if (preg_match('/[0-9]/', $messageText) && !preg_match('/[A-Za-z]/', $messageText) && !preg_match('/[ء-ي]/', $messageText)){
        $messageText = (int)$messageText;
        $GetChat = $BOT->GetChat($messageText);
        if($GetChat['ok']){
            $full_name = $GetChat["result"]["first_name"] . " " . $GetChat["result"]["last_name"];

            $CheckUser = mysqli_fetch_assoc(mysqli_query($db, "SELECT * FROM `users` WHERE `from_id` ='$messageText'"));
            if(!$CheckUser){
                $report = '{"asiacell":{},"zain":{},"korek":{},"iraqsell":{},"alkafil":{},"creditrequest":{},"others":{},"netzain":{},"netasiacell":{},"total":"0"}';
                $report = mysqli_real_escape_string($db, $report);

                mysqli_query($db, "INSERT INTO `users` (`id`, `status`, `from_id`, `select`, `money`, `allmoney`, `limit`, `report`) VALUES (NULL, 1, '$messageText', '1', '0', '0', '0', '$report');");
                $id = mysqli_insert_id($db);
            }else{
                $idU = $CheckUser['id'];
                mysqli_query($db, "UPDATE `users` SET `status`='1' WHERE `id`='$idU'");
            }
            $BOT->sendCommand('sendmessage', [
                'chat_id' => $chatId,
                'text' => sprintf($BOT->language("doneAddUser"),$full_name), 
                'disable_web_page_preview' => 'true', 
                'parse_mode' => 'Markdown', 
                'reply_markup' => json_encode([
                    'inline_keyboard' => [
                        [['text' => $BOT->language("settingsUser"), 'callback_data' => 'settingsUser+'.$id]],
                        [['text' => '➕', 'callback_data' => 'addUser'], ['text' => $BOT->language("Users"), 'callback_data' => 'listUsers+1']],
                        [['text' => $BOT->language("Back"), 'callback_data' => 'main']]
                    ]
                ]) 
            ]);
            $BOT->states($id,'delete');
        }else{
            $BOT->sendCommand('sendmessage', ['chat_id' => $chatId, 'text' => $BOT->language("erroraddUser2"), 'reply_markup' => json_encode(['inline_keyboard' => [[['text' => $BOT->language("Cancel"), 'callback_data' => 'Users']]]]) ]);
        }
    }else{
        $BOT->sendCommand('sendmessage', ['chat_id' => $chatId, 'text' => $BOT->language("erroraddUser1"), 'reply_markup' => json_encode(['inline_keyboard' => [[['text' => $BOT->language("Cancel"), 'callback_data' => 'Users']]]]) ]);
    }
}
if($data == "addUser"){
    $BOT->states($id,'insert','addUser');
    $BOT->sendCommand('editMessageText', [
        'chat_id' => $chatId,
        'message_id' => $messageId, 
        'text' => $BOT->language("addUser"), 
        'disable_web_page_preview' => 'true', 
        'parse_mode' => 'Markdown', 
        'reply_markup' => json_encode([
            'inline_keyboard' => [
                [['text' => $BOT->language("Cancel"), 'callback_data' => 'Users']]
            ]
        ]) 
    ]);
}

if (preg_match("/^(listUsers)([+])(.*)/s", $data)){
    preg_match("/^(listUsers)([+])(.*)/s", $data, $matcha);
    $sp = $matcha[3];
    $BOT->states($id,'delete');
    $Users = $BOT->Users('count');
    $keyboard = [];
    $i = 0;
    if($Users != 0){
        $Users = $BOT->Users('view');
        $Pagination = Pagination($sp, $Users, "listUsers");
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