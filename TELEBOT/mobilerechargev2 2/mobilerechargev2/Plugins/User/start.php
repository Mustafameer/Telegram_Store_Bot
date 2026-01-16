<?php

if ($messageText == "/start"){
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
}
if($data == "start"){
        $BOT->states($id,'delete');
        $BOT->sendCommand('editMessageText', [
            'chat_id' => $chatId,
            'message_id' => $messageId, 
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
}