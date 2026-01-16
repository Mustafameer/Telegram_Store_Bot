<?php 
if($data == "Prices"){
    $BOT->sendCommand('editMessageText', [
        'chat_id' => $chatId,
        'message_id' => $messageId, 
        'text' => $BOT->language("Prices_NowOrLater"), 
        'disable_web_page_preview' => 'true', 
        'reply_markup' => json_encode([
            'inline_keyboard' => [
                [['text' => $BOT->language("N"), 'callback_data' => 'Pay+N'], ['text' => $BOT->language("L"), 'callback_data' => 'Pay+L']],
                [['text' => $BOT->language("Back"), 'callback_data' => 'main']]
            ]
        ]) 
    ]);
}

if (preg_match("/^(Pay)([+])(.*)/s", $data)){
    preg_match("/^(Pay)([+])(.*)/s", $data, $matcha);
    $NowOrLater = $matcha[3];
    $BOT->sendCommand('editMessageText', [
        'chat_id' => $chatId,
        'message_id' => $messageId, 
        'text' => $BOT->language("Prices_text"), 
        'disable_web_page_preview' => 'true', 
        'reply_markup' => json_encode([
            'inline_keyboard' => [
                [['text' => $BOT->language("transfer"), 'callback_data' => 'SP1+transfer+'.$NowOrLater], ['text' => $BOT->language("photos"), 'callback_data' => 'SP1+photos+'.$NowOrLater]],
                [['text' => $BOT->language("Back"), 'callback_data' => 'Prices']]
            ]
        ]) 
    ]);
}

if (preg_match("/^(SP1)([+])(.*)([+])(.*)/s", $data)){
    preg_match("/^(SP1)([+])(.*)([+])(.*)/s", $data, $matcha);
    $TS = $matcha[3];
    $NowOrLater = $matcha[5];
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

            $Ibotton = ["text" => $BOT->language($botton), "callback_data" => 'SP2+'.$TS.'+' . $botton."+".$NowOrLater];
            $keyboard["inline_keyboard"][$i][$j] = $Ibotton;
            $j++;
        }
        $i++;
    }
    $Ibotton = ["text" => $BOT->language("Back"), "callback_data" => 'Pay+'.$NowOrLater];
    $keyboard["inline_keyboard"][$i][] = $Ibotton;
    $reply_markup = json_encode($keyboard);
    $path = $BOT->language($NowOrLater) . " ⬅️ " . $BOT->language($TS);
    $BOT->sendCommand('editMessageText', ['chat_id' => $chatId, 'message_id' => $messageId, 'text' => sprintf($BOT->language("Prices_text_path"),$path), 'reply_markup' => ($reply_markup) ]);
}

if (preg_match("/^(SP2)([+])(.*)([+])(.*)([+])(.*)/s", $data)){
    preg_match("/^(SP2)([+])(.*)([+])(.*)([+])(.*)/s", $data, $matcha);
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

            $Ibotton = ["text" => $botton, "callback_data" => 'SP3+'.$TS.'+'.$company.'+'.$botton."+1+".$NowOrLater];
            $keyboard["inline_keyboard"][$i][$j] = $Ibotton;
            $j++;
        }
        $i++;
    }
    $Ibotton = ["text" => $BOT->language("Back"), "callback_data" => 'SP1+'.$TS."+".$NowOrLater];
    $keyboard["inline_keyboard"][$i][] = $Ibotton;
    $reply_markup = json_encode($keyboard);
    $path = $BOT->language($NowOrLater) . " ⬅️ " . $BOT->language($TS). " ⬅️ " . $BOT->language($company);
    $BOT->sendCommand('editMessageText', ['chat_id' => $chatId, 'message_id' => $messageId, 'text' => sprintf($BOT->language("Prices_text_path"),$path), 'reply_markup' => ($reply_markup) ]);
}

if (preg_match("/^(SP3)([+])(.*)([+])(.*)([+])(.*)([+])(.*)([+])(.*)/s", $data)){
    preg_match("/^(SP3)([+])(.*)([+])(.*)([+])(.*)([+])(.*)([+])(.*)/s", $data, $matcha);
    $BOT->states($id,'delete');
    $TS = $matcha[3];
    $company = $matcha[5];
    $Number = $matcha[7];
    $Select = $matcha[9];
    $NowOrLater = $matcha[11];
    $NameTabel = ($matcha[11] == "N") ? "pricesnow" : "priceslater";
    $nextSelect = ($matcha[9] == 1) ? 2 : 1;
    $select_NAME = ($matcha[9] == 1) ? $BOT->language("one") : $BOT->language("two");

    $path = $BOT->language($NowOrLater) . " ⬅️ " . $BOT->language($TS). " ⬅️ " . $BOT->language($company) . " ⬅️ " . $Number  . " ⬅️ " . $select_NAME;
    $price = mysqli_fetch_assoc(mysqli_query($db, "SELECT * FROM `$NameTabel` WHERE `type`='$TS' AND `select`=$Select AND `company`='$company'"));
    $pn = $price[$Number];
    $pn = ($pn == 0) ? $BOT->language("noWork") : $pn;
    
    $price = mysqli_fetch_assoc(mysqli_query($db, "SELECT * FROM `$NameTabel` WHERE `type`='$TS' AND `select`=$Select AND `company`='$company".'_Before'."'"));
    $pb = $price[$Number];

    if($TS == 'photos'){
        $photos = mysqli_fetch_assoc(mysqli_query($db, "SELECT * FROM `photos` WHERE `company`='$company'"));
        $photos = json_decode($photos[$Number],true);
        $ccphoto = count($photos);
        $reply_markup = [
            'inline_keyboard' => [
                [['text' => $select_NAME, 'callback_data' => 'SP3+'.$TS.'+'.$company.'+'.$Number."+$nextSelect"."+".$NowOrLater]],
                [['text' => $pn, 'callback_data' => "CP+".$TS.'+'.$company.'+'.$Number."+$Select+N"."+".$NowOrLater],['text' => $BOT->language("priceNow"), 'callback_data' => "#"]],
                [['text' => $pb, 'callback_data' => "CP+".$TS.'+'.$company.'+'.$Number."+$Select+B"."+".$NowOrLater],['text' => $BOT->language("priceBefore"), 'callback_data' => "#"]],
                [['text' => $BOT->language("addPhoto"), 'callback_data' => "APH+".$TS.'+'.$company.'+'.$Number."+$Select"."+".$NowOrLater]],
                [['text' => $BOT->language("Back"), 'callback_data' => 'SP2+'.$TS.'+' . $company."+".$NowOrLater]]
            ]
        ];
        $BOT->sendCommand('editMessageText', [
            'chat_id' => $chatId,
            'message_id' => $messageId, 
            'text' => sprintf($BOT->language("Prices_text_path"),$path)."\n\n".sprintf($BOT->language("countPhotos"),$ccphoto),
            'reply_markup' => json_encode($reply_markup) 
        ]);

    }else{
        $reply_markup = [
            'inline_keyboard' => [
                [['text' => $select_NAME, 'callback_data' => 'SP3+'.$TS.'+'.$company.'+'.$Number."+$nextSelect"."+".$NowOrLater]],
                [['text' => $pn, 'callback_data' => "CP+".$TS.'+'.$company.'+'.$Number."+$Select+N"."+".$NowOrLater],['text' => $BOT->language("priceNow"), 'callback_data' => "#"]],
                [['text' => $pb, 'callback_data' => "CP+".$TS.'+'.$company.'+'.$Number."+$Select+B"."+".$NowOrLater],['text' => $BOT->language("priceBefore"), 'callback_data' => "#"]],
                [['text' => $BOT->language("Back"), 'callback_data' => 'SP2+'.$TS.'+' . $company."+".$NowOrLater]]
            ]
        ];
        $BOT->sendCommand('editMessageText', [
            'chat_id' => $chatId,
            'message_id' => $messageId, 
            'text' => sprintf($BOT->language("Prices_text_path"),$path),
            'reply_markup' => json_encode($reply_markup) 
        ]);
    }
}

if ($BOT->states($id,'Get1') == "changeprice" and $messageText != "/start" and $messageText != "/main" and !$data){
    $dataRegex = $BOT->states($id,'Get2');
    preg_match("/^(CP)([+])(.*)([+])(.*)([+])(.*)([+])(.*)([+])(.*)([+])(.*)/s", $dataRegex, $matcha);
    $TS = $matcha[3];
    $company = $matcha[5];
    $Number = $matcha[7];
    $Select = $matcha[9];
    $NB = $matcha[11];
    $NowOrLater = $matcha[13];
    if (preg_match('/[0-9]/', $messageText) && !preg_match('/[A-Za-z]/', $messageText) && !preg_match('/[ء-ي]/', $messageText)){
        $NameTabel = ($matcha[13] == "N") ? "pricesnow" : "priceslater";

        if($NB == "N"){
            mysqli_query($db, "UPDATE `$NameTabel` SET `$Number`=$messageText WHERE `type`='$TS' AND `select`=$Select AND `company`='$company'");
            $pn = $messageText;
            $pn = ($pn == 0) ? $BOT->language("noWork") : $pn;
            $price = mysqli_fetch_assoc(mysqli_query($db, "SELECT * FROM `$NameTabel` WHERE `type`='$TS' AND `select`=$Select AND `company`='$company".'_Before'."'"));
            $pb = $price[$Number];
        }
        if($NB == "B"){
            mysqli_query($db, "UPDATE `$NameTabel` SET `$Number`=$messageText WHERE `type`='$TS' AND `select`=$Select AND `company`='$company".'_Before'."'");
            $price = mysqli_fetch_assoc(mysqli_query($db, "SELECT * FROM `$NameTabel` WHERE `type`='$TS' AND `select`=$Select AND `company`='$company'"));
            $pb = $messageText;
            $pn = $price[$Number];
            $pn = ($pn == 0) ? $BOT->language("noWork") : $pn;
        }

        $nextSelect = ($matcha[9] == 1) ? 2 : 1;
        $select_NAME = ($matcha[9] == 1) ? $BOT->language("one") : $BOT->language("two");
        $path = $BOT->language($NowOrLater) . " ⬅️ " . $BOT->language($TS). " ⬅️ " . $BOT->language($company) . " ⬅️ " . $Number  . " ⬅️ " . $select_NAME;
        
        if($TS == 'photos'){
            $photos = mysqli_fetch_assoc(mysqli_query($db, "SELECT * FROM `photos` WHERE `company`='$company'"));
            $photos = json_decode($photos[$Number],true);
            $ccphoto = count($photos);
            $reply_markup = [
                'inline_keyboard' => [
                    [['text' => $select_NAME, 'callback_data' => 'SP3+'.$TS.'+'.$company.'+'.$Number."+$nextSelect"."+".$NowOrLater]],
                    [['text' => $pn, 'callback_data' => "CP+".$TS.'+'.$company.'+'.$Number."+$Select+N"."+".$NowOrLater],['text' => $BOT->language("priceNow"), 'callback_data' => "#"]],
                    [['text' => $pb, 'callback_data' => "CP+".$TS.'+'.$company.'+'.$Number."+$Select+B"."+".$NowOrLater],['text' => $BOT->language("priceBefore"), 'callback_data' => "#"]],
                    [['text' => $BOT->language("addPhoto"), 'callback_data' => "APH+".$TS.'+'.$company.'+'.$Number."+$Select"."+".$NowOrLater]],
                    [['text' => $BOT->language("Back"), 'callback_data' => 'SP2+'.$TS.'+' . $company."+".$NowOrLater]]
                ]
            ];
            $BOT->sendCommand('sendmessage', [
                'chat_id' => $chatId,
                'text' => sprintf($BOT->language("Prices_text_path"),$path)."\n\n".sprintf($BOT->language("countPhotos"),$ccphoto),
                'reply_markup' => json_encode($reply_markup) 
            ]);
    
        }else{
            $reply_markup = [
                'inline_keyboard' => [
                    [['text' => $select_NAME, 'callback_data' => 'SP3+'.$TS.'+'.$company.'+'.$Number."+$nextSelect"."+".$NowOrLater]],
                    [['text' => $pn, 'callback_data' => "CP+".$TS.'+'.$company.'+'.$Number."+$Select+N"."+".$NowOrLater],['text' => $BOT->language("priceNow"), 'callback_data' => "#"]],
                    [['text' => $pb, 'callback_data' => "CP+".$TS.'+'.$company.'+'.$Number."+$Select+B"."+".$NowOrLater],['text' => $BOT->language("priceBefore"), 'callback_data' => "#"]],
                    [['text' => $BOT->language("Back"), 'callback_data' => 'SP2+'.$TS.'+' . $company."+".$NowOrLater]]
                ]
            ];
            $BOT->sendCommand('sendmessage', [
                'chat_id' => $chatId,
                'text' => sprintf($BOT->language("Prices_text_path"),$path),
                'reply_markup' => json_encode($reply_markup) 
            ]);
        }
        $BOT->states($id,'delete');
    }else{
        $BOT->sendCommand('sendmessage', ['chat_id' => $chatId, 'text' => $BOT->language("errorNumbers"), 'reply_markup' => json_encode(['inline_keyboard' => [[['text' => $BOT->language("Cancel"), 'callback_data' => 'SP3+'.$TS.'+'.$company.'+'.$Number."+$Select+$NowOrLater"]]]]) ]);
    }
}
if (preg_match("/^(CP)([+])(.*)([+])(.*)([+])(.*)([+])(.*)([+])(.*)([+])(.*)/s", $data)){
    preg_match("/^(CP)([+])(.*)([+])(.*)([+])(.*)([+])(.*)([+])(.*)([+])(.*)/s", $data, $matcha);
    $TS = $matcha[3];
    $company = $matcha[5];
    $Number = $matcha[7];
    $Select = $matcha[9];
    $NB = $matcha[11];
    $NowOrLater = $matcha[13];
    $BOT->states($id,'insert','changeprice',"CP+".$TS.'+'.$company.'+'.$Number."+$Select+$NB+$NowOrLater");

    $select_NAME = ($matcha[9] == 1) ? $BOT->language("one") : $BOT->language("two");
    $path = $BOT->language($NowOrLater) . " ⬅️ " . $BOT->language($TS). " ⬅️ " . $BOT->language($company) . " ⬅️ " . $Number  . " ⬅️ " . $select_NAME;

    $BOT->sendCommand('editMessageText', [
        'chat_id' => $chatId,
        'message_id' => $messageId, 
        'text' => sprintf($BOT->language("changePrice"),$path), 
        'disable_web_page_preview' => 'true', 
        'parse_mode' => 'Markdown', 
        'reply_markup' => json_encode([
            'inline_keyboard' => [
                [['text' => $BOT->language("Cancel"), 'callback_data' => 'SP3+'.$TS.'+'.$company.'+'.$Number."+$Select+$NowOrLater"]]
            ]
        ]) 
    ]);
}

if ($BOT->states($id,'Get1') == "addphoto" and $photo and !$data){
    $dataRegex = $BOT->states($id,'Get2');
    preg_match("/^(APH)([+])(.*)([+])(.*)([+])(.*)([+])(.*)([+])(.*)/s", $dataRegex, $matcha);
    $TS = $matcha[3];
    $company = $matcha[5];
    $Number = $matcha[7];
    $Select = $matcha[9];
    $NowOrLater = $matcha[11];
    $NameTabel = ($matcha[11] == "N") ? "pricesnow" : "priceslater";

    $price = mysqli_fetch_assoc(mysqli_query($db, "SELECT * FROM `$NameTabel` WHERE `type`='$TS' AND `select`=$Select AND `company`='$company'"));
    $pn = $price[$Number];
    $pn = ($pn == 0) ? $BOT->language("noWork") : $pn;
    
    $price = mysqli_fetch_assoc(mysqli_query($db, "SELECT * FROM `$NameTabel` WHERE `type`='$TS' AND `select`=$Select AND `company`='$company".'_Before'."'"));
    $pb = $price[$Number];

    $nextSelect = ($matcha[9] == 1) ? 2 : 1;
    $select_NAME = ($matcha[9] == 1) ? $BOT->language("one") : $BOT->language("two");
    $path = $BOT->language($NowOrLater) . " ⬅️ " . $BOT->language($TS). " ⬅️ " . $BOT->language($company) . " ⬅️ " . $Number  . " ⬅️ " . $select_NAME;
    
    $photos = mysqli_fetch_assoc(mysqli_query($db, "SELECT * FROM `photos` WHERE `company`='$company'"));
    $photos = json_decode($photos[$Number],true);
    $photos[] = $photo_id;
    $arrnew = json_encode($photos, JSON_UNESCAPED_UNICODE);
    $arrnew = mysqli_real_escape_string($db, $arrnew);
    mysqli_query($db, "UPDATE `photos` SET `$Number`='$arrnew' WHERE `company`='$company'");

    $ccphoto = count($photos);
    $reply_markup = [
        'inline_keyboard' => [
            [['text' => $select_NAME, 'callback_data' => 'SP3+'.$TS.'+'.$company.'+'.$Number."+$nextSelect"."+".$NowOrLater]],
            [['text' => $pn, 'callback_data' => "CP+".$TS.'+'.$company.'+'.$Number."+$Select+N"."+".$NowOrLater],['text' => $BOT->language("priceNow"), 'callback_data' => "#"]],
            [['text' => $pb, 'callback_data' => "CP+".$TS.'+'.$company.'+'.$Number."+$Select+B"."+".$NowOrLater],['text' => $BOT->language("priceBefore"), 'callback_data' => "#"]],
            [['text' => $BOT->language("addPhoto"), 'callback_data' => "APH+".$TS.'+'.$company.'+'.$Number."+$Select"."+".$NowOrLater]],
            [['text' => $BOT->language("Back"), 'callback_data' => 'SP2+'.$TS.'+' . $company."+".$NowOrLater]]
        ]
    ];
    $Arrays = json_decode($BOT->bot("step", "Get") , true);
    if(isset($messageData['media_group_id'])){
        if($Arrays['Group'] != $messageData['media_group_id']){
            $Arrays['Group'] = $messageData['media_group_id'];
            $BOT->sendCommand('sendmessage', [
                'chat_id' => $chatId,
                'text' => sprintf($BOT->language("Prices_text_path"),$path)."\n\n".sprintf($BOT->language("countPhotos"),$ccphoto),
                'reply_markup' => json_encode($reply_markup) 
            ]);
            $arrnew = json_encode($Arrays, JSON_UNESCAPED_UNICODE);
            $arrnew = mysqli_real_escape_string($db, $arrnew);
            $BOT->bot("step", "Set", $arrnew);
        }
    }else{
        $BOT->sendCommand('sendmessage', [
            'chat_id' => $chatId,
            'text' => sprintf($BOT->language("Prices_text_path"),$path)."\n\n".sprintf($BOT->language("countPhotos"),$ccphoto),
            'reply_markup' => json_encode($reply_markup) 
        ]);
    }
}

if (preg_match("/^(APH)([+])(.*)([+])(.*)([+])(.*)([+])(.*)([+])(.*)/s", $data)){
    preg_match("/^(APH)([+])(.*)([+])(.*)([+])(.*)([+])(.*)([+])(.*)/s", $data, $matcha);
    $TS = $matcha[3];
    $company = $matcha[5];
    $Number = $matcha[7];
    $Select = $matcha[9];
    $NowOrLater = $matcha[11];
    $BOT->states($id,'insert','addphoto',"APH+".$TS.'+'.$company.'+'.$Number."+$Select+$NowOrLater");

    $select_NAME = ($matcha[9] == 1) ? $BOT->language("one") : $BOT->language("two");
    $path = $BOT->language($NowOrLater) . " ⬅️ " . $BOT->language($TS). " ⬅️ " . $BOT->language($company) . " ⬅️ " . $Number  . " ⬅️ " . $select_NAME;

    $BOT->sendCommand('editMessageText', [
        'chat_id' => $chatId,
        'message_id' => $messageId, 
        'text' => sprintf($BOT->language("addPhoto_text"),$path), 
        'disable_web_page_preview' => 'true', 
        'parse_mode' => 'Markdown', 
        'reply_markup' => json_encode([
            'inline_keyboard' => [
                [['text' => $BOT->language("Cancel"), 'callback_data' => 'SP3+'.$TS.'+'.$company.'+'.$Number."+$Select+".$NowOrLater]]
            ]
        ]) 
    ]);
}