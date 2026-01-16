<?php 

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