<?php 

if ($data == "addphotos"){
    $TS = 'photos';
    $NowOrLater = "N";
    $rows = $BOT->Prices($TS,'List'.$NowOrLater);
    $rows = array_chunk($rows, 2);
    $i = 0;
    $keyboard = [];
    $keyboard["inline_keyboard"] = [];
    foreach ($rows as $row)
    {
        $j = 0;
        $keyboard["inline_keyboard"][$i] = [];
        $bottons = $row;
        foreach ($bottons as $botton)
        {

            $Ibotton = ["text" => $BOT->language($botton), "callback_data" => 'AD1+'.$TS.'+' . $botton."+".$NowOrLater];
            $keyboard["inline_keyboard"][$i][$j] = $Ibotton;
            $j++;
        }
        $i++;
    }
    $Ibotton = ["text" => $BOT->language("Back"), "callback_data" => 'main'];
    $keyboard["inline_keyboard"][$i][] = $Ibotton;
    $reply_markup = json_encode($keyboard);
    $path = $BOT->language($TS);
    $BOT->sendCommand('editMessageText', ['chat_id' => $chatId, 'message_id' => $messageId, 'text' => sprintf($BOT->language("settingsaddphotos"),$path), 'reply_markup' => ($reply_markup) ]);
}

if (preg_match("/^(AD1)([+])(.*)([+])(.*)([+])(.*)/s", $data)){
    preg_match("/^(AD1)([+])(.*)([+])(.*)([+])(.*)/s", $data, $matcha);
    $BOT->states($id,'delete');
    $TS = $matcha[3];
    $company = $matcha[5];
    $NowOrLater = $matcha[7];
    $rows = $BOT->Prices($TS,'List'.$NowOrLater,$company);
    $rows = array_chunk($rows, 3);
    $i = 0;
    $keyboard = [];
    $keyboard["inline_keyboard"] = [];
    foreach ($rows as $row)
    {
        $j = 0;
        $keyboard["inline_keyboard"][$i] = [];
        $bottons = $row;
        foreach ($bottons as $botton)
        {

            $Ibotton = ["text" => $botton, "callback_data" => "APH+".$TS.'+'.$company.'+'.$botton."+".$NowOrLater];
            
            $keyboard["inline_keyboard"][$i][$j] = $Ibotton;
            $j++;
        }
        $i++;
    }
    $Ibotton = ["text" => $BOT->language("Back"), "callback_data" => 'addphotos'];
    $keyboard["inline_keyboard"][$i][] = $Ibotton;
    $reply_markup = json_encode($keyboard);
    $path = $BOT->language($TS). " ⬅️ " . $BOT->language($company);
    $BOT->sendCommand('editMessageText', ['chat_id' => $chatId, 'message_id' => $messageId, 'text' => sprintf($BOT->language("settingsaddphotos"),$path), 'reply_markup' => ($reply_markup) ]);
}

if ($BOT->states($id,'Get1') == "addphoto" and $photo and !$data){
    $dataRegex = $BOT->states($id,'Get2');
    preg_match("/^(APH)([+])(.*)([+])(.*)([+])(.*)([+])(.*)/s", $dataRegex, $matcha);
    $TS = $matcha[3];
    $company = $matcha[5];
    $Number = $matcha[7];
    $NowOrLater = $matcha[9];
    $NameTabel = ($matcha[9] == "N") ? "pricesnow" : "priceslater";

    $path = $BOT->language($TS). " ⬅️ " . $BOT->language($company) . " ⬅️ " . $Number;
    
    $photos = mysqli_fetch_assoc(mysqli_query($db, "SELECT * FROM `photos` WHERE `company`='$company'"));
    $photos = json_decode($photos[$Number],true);
    $photos[] = $photo_id;
    $arrnew = json_encode($photos, JSON_UNESCAPED_UNICODE);
    $arrnew = mysqli_real_escape_string($db, $arrnew);
    mysqli_query($db, "UPDATE `photos` SET `$Number`='$arrnew' WHERE `company`='$company'");

    $ccphoto = count($photos);
    $reply_markup = [
        'inline_keyboard' => [
            [['text' => $BOT->language("Cancel"), 'callback_data' => 'AD1+'.$TS.'+'.$company.'+'.$NowOrLater]]
        ]
    ];

    $Arrays = json_decode($BOT->bot("step", "Get") , true);
    if(isset($messageData['media_group_id'])){
        if($Arrays['Group'] != $messageData['media_group_id']){
            $Arrays['Group'] = $messageData['media_group_id'];
            $BOT->sendCommand('sendmessage', [
                'chat_id' => $chatId,
                'text' => sprintf($BOT->language("settingsaddphotos"),$path)."\n\n".sprintf($BOT->language("countPhotos"),$ccphoto),
                'reply_markup' => json_encode($reply_markup) 
            ]);
        
            // notifications OWNER
            $admin = "[$from_name](tg://user?id=$chatId)";
            $BOT->sendCommand('sendmessage', [
                'chat_id' => $owners[0], 
                'text' => sprintf($BOT->language("notificationsOwnerADDPH"),$path, $admin, date("Y-m-d h:i")), 
                'disable_web_page_preview' => 'true', 
                'parse_mode' => 'Markdown'
            ]);
            $arrnew = json_encode($Arrays, JSON_UNESCAPED_UNICODE);
            $arrnew = mysqli_real_escape_string($db, $arrnew);
            $BOT->bot("step", "Set", $arrnew);
        }
    }else{
        $BOT->sendCommand('sendmessage', [
            'chat_id' => $chatId,
            'text' => sprintf($BOT->language("settingsaddphotos"),$path)."\n\n".sprintf($BOT->language("countPhotos"),$ccphoto),
            'reply_markup' => json_encode($reply_markup) 
        ]);
    
        // notifications OWNER
        $admin = "[$from_name](tg://user?id=$chatId)";
        $BOT->sendCommand('sendmessage', [
            'chat_id' => $owners[0], 
            'text' => sprintf($BOT->language("notificationsOwnerADDPH"),$path, $admin, date("Y-m-d h:i")), 
            'disable_web_page_preview' => 'true', 
            'parse_mode' => 'Markdown'
        ]);
    }
}

if (preg_match("/^(APH)([+])(.*)([+])(.*)([+])(.*)([+])(.*)/s", $data)){
    preg_match("/^(APH)([+])(.*)([+])(.*)([+])(.*)([+])(.*)/s", $data, $matcha);
    $TS = $matcha[3];
    $company = $matcha[5];
    $Number = $matcha[7];
    $NowOrLater = $matcha[9];
    $BOT->states($id,'insert','addphoto',"APH+".$TS.'+'.$company.'+'.$Number."+$NowOrLater");
    $path = $BOT->language($TS). " ⬅️ " . $BOT->language($company) . " ⬅️ " . $Number;

    $BOT->sendCommand('editMessageText', [
        'chat_id' => $chatId,
        'message_id' => $messageId, 
        'text' => sprintf($BOT->language("addPhoto_text"),$path), 
        'disable_web_page_preview' => 'true', 
        'parse_mode' => 'Markdown', 
        'reply_markup' => json_encode([
            'inline_keyboard' => [
                [['text' => $BOT->language("Cancel"), 'callback_data' => 'AD1+'.$TS.'+'.$company.'+'.$NowOrLater]]
            ]
        ]) 
    ]);
}