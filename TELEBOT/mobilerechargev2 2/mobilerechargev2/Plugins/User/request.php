<?php 

if (preg_match("/^(User)([+])(.*)/s", $data)){
    preg_match("/^(User)([+])(.*)/s", $data, $matcha);
    $NowOrLater = $matcha[3];
    $BOT->sendCommand('editMessageText', [
        'chat_id' => $chatId,
        'message_id' => $messageId, 
        'text' => $BOT->language("REQ_text"), 
        'disable_web_page_preview' => 'true', 
        'reply_markup' => json_encode([
            'inline_keyboard' => [
                [['text' => $BOT->language("transfer"), 'callback_data' => 'REQ1+transfer+'.$NowOrLater], ['text' => $BOT->language("photos"), 'callback_data' => 'REQ1+photos+'.$NowOrLater]],
                [['text' => $BOT->language("Back"), 'callback_data' => 'start']]
            ]
        ]) 
    ]);
}

if (preg_match("/^(REQ1)([+])(.*)([+])(.*)/s", $data)){
    preg_match("/^(REQ1)([+])(.*)([+])(.*)/s", $data, $matcha);
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

            $Ibotton = ["text" => $BOT->language($botton), "callback_data" => 'REQ2+'.$TS.'+' . $botton."+".$NowOrLater];
            $keyboard["inline_keyboard"][$i][$j] = $Ibotton;
            $j++;
        }
        $i++;
    }
    $Ibotton = ["text" => $BOT->language("Back"), "callback_data" => 'User+'.$NowOrLater];
    $keyboard["inline_keyboard"][$i][] = $Ibotton;
    $reply_markup = json_encode($keyboard);
    $path = $BOT->language($NowOrLater) . " ⬅️ " . $BOT->language($TS);
    $BOT->sendCommand('editMessageText', ['chat_id' => $chatId, 'message_id' => $messageId, 'text' => sprintf($BOT->language("REQ_text_path"),$path), 'reply_markup' => ($reply_markup) ]);
}


if (preg_match("/^(REQ2)([+])(.*)([+])(.*)([+])(.*)/s", $data)){
    preg_match("/^(REQ2)([+])(.*)([+])(.*)([+])(.*)/s", $data, $matcha);
    $BOT->states($id,'delete');
    $TS = $matcha[3];
    $company = $matcha[5];
    $NowOrLater = $matcha[7];
    $NameTabel = ($matcha[7] == "N") ? "pricesnow" : "priceslater";
    $select = (int)$user['select'];
    $rows = $BOT->PricesUser($TS,$select,$NameTabel,$company);
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

            $Ibotton = ["text" => $botton['text'], "callback_data" => 'REQ3+'.$TS.'+'.$company.'+'.$botton['data']."+".$NowOrLater];
            $keyboard["inline_keyboard"][$i][$j] = $Ibotton;
            $j++;
        }
        $i++;
    }
    $Ibotton = ["text" => $BOT->language("Back"), "callback_data" => 'REQ1+'.$TS."+".$NowOrLater];
    $keyboard["inline_keyboard"][$i][] = $Ibotton;
    $reply_markup = json_encode($keyboard);
    $path = $BOT->language($NowOrLater) . " ⬅️ " . $BOT->language($TS). " ⬅️ " . $BOT->language($company);
    if($company != "netzain" and $company != "netasiacell"){
        $text= $BOT->language('REQ_text_path');
    }else{
        $text= $BOT->language('REQ_textNet_path');
    }
    $BOT->sendCommand('editMessageText', ['chat_id' => $chatId, 'message_id' => $messageId, 'text' => sprintf($text,$path), 'reply_markup' => ($reply_markup) ]);
}

if (preg_match("/^(DoneREQ)([+])(.*)/s", $data)){
    preg_match("/^(DoneREQ)([+])(.*)/s", $data, $matcha);
    $idREQ = $matcha[3];
    $REQ = mysqli_fetch_assoc(mysqli_query($db, "SELECT * FROM `request` WHERE `id`=$idREQ"));


    if($REQ['message_id_cancel'] != 0){
        $BOT->sendCommand('deleteMessage', [
            'chat_id' => $chatId,
            'message_id' => $REQ['message_id_cancel']
        ]);    
    }

    $userREQ = mysqli_fetch_assoc(mysqli_query($db, "SELECT * FROM `users` WHERE `from_id` ='".$REQ['from_id']."'"));


    $TS = $REQ['ts'];
    $company = $REQ['company'];
    $Number = $REQ['number'];
    $NowOrLater = $REQ['nol'];
    $NameTabel = ($REQ['nol'] == "N") ? "pricesnow" : "priceslater";
    $select = (int)$userREQ['select'];
    $priceN = mysqli_fetch_assoc(mysqli_query($db, "SELECT * FROM `$NameTabel` WHERE `type`='$TS' AND `select`=$select AND `company`='$company'"));
    $pn = $priceN[$Number];
    $money = $userREQ['money'] + $pn;

    // ADD MONEY
    $allmoney = $userREQ['allmoney'] + $pn;

    $priceB = mysqli_fetch_assoc(mysqli_query($db, "SELECT * FROM `$NameTabel` WHERE `type`='$TS' AND `select`=$select AND `company`='$company".'_Before'."'"));
    $pb = $priceB[$Number];
    
    $profit = json_decode($BOT->bot("profit", "Get") , true);
    $profitNumber = $pn - $pb;
    $profitNumber = $profit[$company] + $profitNumber;
    $profit[$company] = $profitNumber;
    $arrnewP = json_encode($profit, JSON_UNESCAPED_UNICODE);
    $arrnewP = mysqli_real_escape_string($db, $arrnewP);
    $BOT->bot("profit", "Set", $arrnewP);

    //REPORT 
    $report = json_decode($userREQ['report'] , true);
    if(isset($report[$company][$Number])){
        $report[$company][$Number] = $report[$company][$Number] + 1;
    }else{
        $report[$company][$Number] = 1;
    }
    $report['total'] = $report['total'] + $pn;
    $arrnewR = json_encode($report, JSON_UNESCAPED_UNICODE);
    $arrnewR = mysqli_real_escape_string($db, $arrnewR);
    mysqli_query($db, "UPDATE users SET `money`='$money', `allmoney`='$allmoney', `report`='$arrnewR' WHERE `from_id`='".$REQ['from_id']."'");
    $path = $BOT->language($NowOrLater) . " ⬅️ " . $BOT->language($TS). " ⬅️ " . $BOT->language($company) . " ⬅️ " . $Number ;

    //NOTIFICATIONS OWNER
    $GetChat = $BOT->GetChat($REQ['from_id']);
    $full_name = $GetChat["result"]["first_name"] . " " . $GetChat["result"]["last_name"];
    $BOT->sendCommand('editMessageText', [
        'chat_id' => $chatId,
        'message_id' => $messageId, 
        'text' => sprintf($BOT->language("notificationsOwnerTS"),$BOT->language($TS),$BOT->language($company),$full_name,$REQ['from_id'], $REQ['from_id'], $path, $REQ['req_number'], $pn, $money, $allmoney), 
        'disable_web_page_preview' => 'true', 
        'parse_mode' => 'Markdown'
    ]);

    //NOTIFICATIONS USER
    $BOT->sendCommand('editMessageText', [
        'chat_id' => $REQ['from_id'],
        'message_id' => $REQ['message_id'], 
        'text' => sprintf($BOT->language("notificationsUserTS"),$BOT->language($TS),$BOT->language($company),$REQ['from_id'], $REQ['req_number'], $path, $pn, $money, $allmoney), 
    ]);
    $BOT->sendCommand('sendmessage', [
        'chat_id' => $REQ['from_id'], 
        'reply_to_message_id' => $REQ['message_id'],
        'text' => $BOT->language("notificationsDONETS")
    ]);

    //START
    $BOT->sendCommand('sendmessage', [
        'chat_id' => $REQ['from_id'], 
        'text' => $BOT->language("userStart"), 
        'disable_web_page_preview' => 'true', 
        'parse_mode' => 'Markdown', 
        'reply_markup' => json_encode([
            'inline_keyboard' => [
                [['text' => $BOT->language("N"), 'callback_data' => 'User+N'],['text' => $BOT->language("L"), 'callback_data' => 'User+L']],
                [['text' => $BOT->language("account"), 'callback_data' => 'Account']]
            ]
        ])
    ]);
    mysqli_query($db, "DELETE FROM `request` WHERE `id`=$idREQ");
}

if (preg_match("/^(DoneREQCANCEL)([+])(.*)/s", $data)){
    preg_match("/^(DoneREQCANCEL)([+])(.*)/s", $data, $matcha);
    $idREQ = $matcha[3];
    $REQ = mysqli_fetch_assoc(mysqli_query($db, "SELECT * FROM `request` WHERE `id`=$idREQ"));

    $BOT->sendCommand('deleteMessage', [
        'chat_id' => $chatId,
        'message_id' => $messageId
    ]);
    
    $BOT->sendCommand('deleteMessage', [
        'chat_id' => $owners[0], 
        'message_id' => $REQ['message_id_req']
    ]);

    $path = $BOT->language($REQ['nol']) . " ⬅️ " . $BOT->language($REQ['ts']). " ⬅️ " . $BOT->language($REQ['company']) . " ⬅️ " . $REQ['number'];

    $BOT->sendCommand('editMessageText', [
        'chat_id' => $REQ['from_id'], 
        'message_id' => $REQ['message_id'],
        'text' => sprintf($BOT->language("DoneCancel_text"),$REQ['req_number'],$path,$idREQ)
    ]);

    mysqli_query($db, "DELETE FROM `request` WHERE `id`=$idREQ");
}

if (preg_match("/^(CancelREQ)([+])(.*)/s", $data)){
    preg_match("/^(CancelREQ)([+])(.*)/s", $data, $matcha);
    $idREQ = $matcha[3];
    $REQ = mysqli_fetch_assoc(mysqli_query($db, "SELECT * FROM `request` WHERE `id`=$idREQ"));
    $path = $BOT->language($REQ['nol']) . " ⬅️ " . $BOT->language($REQ['ts']). " ⬅️ " . $BOT->language($REQ['company']) . " ⬅️ " . $REQ['number'];

    $BOT->sendCommand('editMessageText', [
        'chat_id' => $chatId, 
        'message_id' => $messageId,
        'text' => sprintf($BOT->language("REQSMS_textUser_Cnacel"),$REQ['req_number'],$path,$idREQ), 
        'disable_web_page_preview' => 'true',
        'parse_mode' => 'Markdown'
    ]);

    $message_idR = $REQ['message_id_req'];

    $MessageC = $BOT->sendCommand('sendmessage', [
        'chat_id' => $owners[0], 
        'reply_to_message_id' => $message_idR,
        'text' => sprintf($BOT->language("REQCANCEL"),$idREQ),
        'reply_markup' => json_encode([
            'inline_keyboard' => [
                [['text' => $BOT->language("DoneCancel"), 'callback_data' => "DoneREQCANCEL+$idREQ"]]
            ]
        ])
    ]);
    $message_idC = json_decode($MessageC, true);
    $message_idC = $message_idC['result']['message_id'];
    mysqli_query($db, "UPDATE `request` SET `message_id_cancel`=$message_idC WHERE `id`='$idREQ'");
}


if ($BOT->states($id,'Get1') == "REQSMS" and $messageText != "/start" and $messageText != "/main" and !$data){
    $dataRegex = $BOT->states($id,'Get2');
    preg_match("/^(REQ)([+])(.*)([+])(.*)([+])(.*)([+])(.*)/s", $dataRegex, $matcha);
    $TS = $matcha[3];
    $company = $matcha[5];
    $Number = $matcha[7];
    $NowOrLater = $matcha[9];
    if (preg_match('/[0-9]/', $messageText) && !preg_match('/[A-Za-z]/', $messageText) && !preg_match('/[ء-ي]/', $messageText)){
        $NameTabel = ($matcha[9] == "N") ? "pricesnow" : "priceslater";
        $path = $BOT->language($NowOrLater) . " ⬅️ " . $BOT->language($TS). " ⬅️ " . $BOT->language($company) . " ⬅️ " . $Number;

        $req_number = mysqli_real_escape_string($db, $messageText);
        mysqli_query($db, "INSERT INTO `request` (`id`, `ts`, `company`, `number`, `nol`, `req_number`, `from_id`, `message_id`, `message_id_req`, `message_id_cancel`) VALUES (NULL, '$TS', '$company', '$Number', '$NowOrLater', '$req_number', '$chatId', '0', '0', '0')");
        $idREQ = mysqli_insert_id($db);
        // MESSAGE
        $Message = $BOT->sendCommand('sendmessage', [
            'chat_id' => $chatId, 
            'text' => sprintf($BOT->language("REQSMS_textUser"),$messageText,$path,$idREQ), 
            'disable_web_page_preview' => 'true',
            'parse_mode' => 'Markdown',
            'reply_markup' => json_encode([
                'inline_keyboard' => [
                    [['text' => $BOT->language("REQ_CANCEL"), 'callback_data' => 'CancelREQ+'.$idREQ]]
                ]
            ])
        ]);
        $message_idM = json_decode($Message, true);
        $message_idM = $message_idM['result']['message_id'];

        //MESSAGE REQ
        $MessageREQ = $BOT->sendCommand('sendmessage', [
            'chat_id' => $owners[0], 
            'text' => sprintf($BOT->language("REQSMS_text"),$BOT->language($TS),$BOT->language($company),$from_name,$chatId, $chatId, $path, $messageText,$idREQ), 
            'disable_web_page_preview' => 'true',
            'parse_mode' => 'Markdown',
            'reply_markup' => json_encode([
                'inline_keyboard' => [
                    [['text' => $BOT->language("Done"), 'callback_data' => "DoneREQ+$idREQ"]]
                ]
            ])
        ]);
        $message_idR = json_decode($MessageREQ, true);
        $message_idR = $message_idR['result']['message_id'];

        mysqli_query($db, "UPDATE `request` SET `message_id`=$message_idM, `message_id_req`=$message_idR WHERE `id`='$idREQ'");

        $BOT->states($id,'delete');
    }else{
        $BOT->sendCommand('sendmessage', ['chat_id' => $chatId, 'text' => $BOT->language("errorNumbers"), 'reply_markup' => json_encode(['inline_keyboard' => [[['text' => $BOT->language("Cancel"), 'callback_data' => 'REQ2+'.$TS.'+'.$company."+$NowOrLater"]]]]) ]);
    }
}


if (preg_match("/^(REQ3)([+])(.*)([+])(.*)([+])(.*)([+])(.*)/s", $data)){
    preg_match("/^(REQ3)([+])(.*)([+])(.*)([+])(.*)([+])(.*)/s", $data, $matcha);
    $TS = $matcha[3];
    $company = $matcha[5];
    $Number = $matcha[7];
    $NowOrLater = $matcha[9];
    $NameTabel = ($matcha[9] == "N") ? "pricesnow" : "priceslater";
    $select = (int)$user['select'];
    $priceN = mysqli_fetch_assoc(mysqli_query($db, "SELECT * FROM `$NameTabel` WHERE `type`='$TS' AND `select`=$select AND `company`='$company'"));
    $pn = $priceN[$Number];
    $money = $user['money'] + $pn;
    if($user['limit'] >= $money or $user['limit'] == 0){
        if($TS == "photos"){

            // SEND PHOTO
            $photos = mysqli_fetch_assoc(mysqli_query($db, "SELECT * FROM `photos` WHERE `company`='$company'"));
            $photos = json_decode($photos[$Number],true);
            if(count($photos) != 0){
                $BOT->sendCommand('sendphoto', ['chat_id' => $chatId, 'photo' => $photos[0] ]);
                array_splice($photos, 0,1);
                $arrnew = json_encode($photos, JSON_UNESCAPED_UNICODE);
                $arrnew = mysqli_real_escape_string($db, $arrnew);
                mysqli_query($db, "UPDATE `photos` SET `$Number`='$arrnew' WHERE `company`='$company'");
            
                // ADD MONEY
                $allmoney = $user['allmoney'] + $pn;

                $priceB = mysqli_fetch_assoc(mysqli_query($db, "SELECT * FROM `$NameTabel` WHERE `type`='$TS' AND `select`=$select AND `company`='$company".'_Before'."'"));
                $pb = $priceB[$Number];
                
                $profit = json_decode($BOT->bot("profit", "Get") , true);
                $profitNumber = $pn - $pb;
                $profitNumber = $profit[$company] + $profitNumber;
                $profit[$company] = $profitNumber;
                $arrnewP = json_encode($profit, JSON_UNESCAPED_UNICODE);
                $arrnewP = mysqli_real_escape_string($db, $arrnewP);
                $BOT->bot("profit", "Set", $arrnewP);

                //REPORT 
                $report = json_decode($user['report'] , true);
                if(isset($report[$company][$Number])){
                    $report[$company][$Number] = $report[$company][$Number] + 1;
                }else{
                    $report[$company][$Number] = 1;
                }
                $report['total'] = $report['total'] + $pn;
                $arrnewR = json_encode($report, JSON_UNESCAPED_UNICODE);
                $arrnewR = mysqli_real_escape_string($db, $arrnewR);
                mysqli_query($db, "UPDATE users SET `money`='$money', `allmoney`='$allmoney', `report`='$arrnewR' WHERE `id`='$id'");
                $path = $BOT->language($NowOrLater) . " ⬅️ " . $BOT->language($TS). " ⬅️ " . $BOT->language($company) . " ⬅️ " . $Number ;
            
                //NOTIFICATIONS OWNERS
                foreach($owners as $owner){
                    $BOT->sendCommand('sendmessage', [
                        'chat_id' => $owner, 
                        'text' => sprintf($BOT->language("notificationsOwner"),$BOT->language($TS),$BOT->language($company),$from_name,$chatId, $chatId, $path, $pn, $money, $allmoney), 
                        'disable_web_page_preview' => 'true', 
                        'parse_mode' => 'Markdown'
                    ]);
                }

                //NOTIFICATIONS USER
                $BOT->sendCommand('editMessageText', [
                    'chat_id' => $chatId,
                    'message_id' => $messageId, 
                    'text' => sprintf($BOT->language("notificationsUser"),$BOT->language($TS),$BOT->language($company),$chatId, $path, $pn, $money, $allmoney), 
                ]);

                //START
                $BOT->sendCommand('sendmessage', [
                    'chat_id' => $chatId, 
                    'text' => $BOT->language("userStart"), 
                    'disable_web_page_preview' => 'true', 
                    'parse_mode' => 'Markdown', 
                    'reply_markup' => json_encode([
                        'inline_keyboard' => [
                            [['text' => $BOT->language("N"), 'callback_data' => 'User+N'],['text' => $BOT->language("L"), 'callback_data' => 'User+L']],
                            [['text' => $BOT->language("account"), 'callback_data' => 'Account']]
                        ]
                    ])
                ]);
            }else{
                $BOT->sendCommand('editMessageText', [
                    'chat_id' => $chatId,
                    'message_id' => $messageId, 
                    'text' => $BOT->language("noPhotos"), 
                    'disable_web_page_preview' => 'true', 
                    'parse_mode' => 'Markdown', 
                    'reply_markup' => json_encode([
                        'inline_keyboard' => [
                            [['text' => $BOT->language("Back"), 'callback_data' => 'REQ2+'.$TS.'+'.$company."+$NowOrLater"]]
                        ]
                    ]) 
                ]);
            }
        }else{
            $BOT->states($id,'insert','REQSMS',"REQ+".$TS.'+'.$company.'+'.$Number."+$NowOrLater");
            $path = $BOT->language($NowOrLater) . " ⬅️ " . $BOT->language($TS). " ⬅️ " . $BOT->language($company) . " ⬅️ " . $Number;
        
            $BOT->sendCommand('editMessageText', [
                'chat_id' => $chatId,
                'message_id' => $messageId, 
                'text' => sprintf($BOT->language("REQSMS"),$path), 
                'disable_web_page_preview' => 'true', 
                'parse_mode' => 'Markdown', 
                'reply_markup' => json_encode([
                    'inline_keyboard' => [
                        [['text' => $BOT->language("Cancel"), 'callback_data' => 'REQ2+'.$TS.'+'.$company."+$NowOrLater"]]
                    ]
                ]) 
            ]);
        }
    }else{
        $BOT->sendCommand('editMessageText', [
            'chat_id' => $chatId,
            'message_id' => $messageId, 
            'text' => $BOT->language("overlimit"), 
            'disable_web_page_preview' => 'true', 
            'parse_mode' => 'Markdown', 
            'reply_markup' => json_encode([
                'inline_keyboard' => [
                    [['text' => $BOT->language("Back"), 'callback_data' => 'REQ2+'.$TS.'+'.$company."+$NowOrLater"]]
                ]
            ]) 
        ]);
    }
}