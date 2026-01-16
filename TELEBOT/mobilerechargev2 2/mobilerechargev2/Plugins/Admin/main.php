<?php 


if ($messageText == "/main"){
    $BOT->states($id,'delete');
    $BOT->sendCommand('sendmessage', [
        'chat_id' => $chatId, 
        'text' => $BOT->language("text_main"), 
        'disable_web_page_preview' => 'true', 
        'parse_mode' => 'Markdown', 
        'reply_markup' => json_encode([
            'inline_keyboard' => [
                [['text' => $BOT->language("Users"), 'callback_data' => 'Users+1'],['text' => $BOT->language("addphotos"), 'callback_data' => 'addphotos']],
                [['text' => $BOT->language("statsPhotos"), 'callback_data' => 'statsPhotos']]
            ]
        ])
    ]);
}


if($data == "main"){
    $BOT->states($id,'delete');
    $BOT->sendCommand('editMessageText', [
        'chat_id' => $chatId,
        'message_id' => $messageId, 
        'text' => $BOT->language("text_main"), 
        'disable_web_page_preview' => 'true', 
        'parse_mode' => 'Markdown', 
        'reply_markup' => json_encode([
            'inline_keyboard' => [
                [['text' => $BOT->language("Users"), 'callback_data' => 'Users+1'],['text' => $BOT->language("addphotos"), 'callback_data' => 'addphotos']],
                [['text' => $BOT->language("statsPhotos"), 'callback_data' => 'statsPhotos']]
            ]
        ])
    ]);
}

if($data == "statsPhotos"){
    $BOT->sendCommand('editMessageText', [
        'chat_id' => $chatId,
        'message_id' => $messageId, 
        'text' => $BOT->statsPhotos(), 
        'disable_web_page_preview' => 'true', 
        'reply_markup' => json_encode([
            'inline_keyboard' => [
                [['text' => $BOT->language("Back"), 'callback_data' => 'main']]
            ]
        ])
    ]);
}