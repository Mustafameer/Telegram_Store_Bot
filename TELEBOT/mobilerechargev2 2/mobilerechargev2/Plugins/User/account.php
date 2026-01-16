<?php 

if($data == "Account"){
    $select = (int)$user['select'];
    $select_NAME = ($select == 1) ? $BOT->language("one") : $BOT->language("two");
    $BOT->sendCommand('editMessageText', [
        'chat_id' => $chatId,
        'message_id' => $messageId, 
        'text' => sprintf($BOT->language("account_text"),$select_NAME,$user['money'],$user['allmoney'],$user['limit']), 
        'disable_web_page_preview' => 'true', 
        'reply_markup' => json_encode([
            'inline_keyboard' => [
                [['text' => $BOT->language("Back"), 'callback_data' => 'start']]
            ]
        ])
    ]);
}