<?php 

if ($messageText == "/main"){
    $BOT->states($id,'delete');
    $status = json_decode($BOT->bot("status", "Get") , true);
    $Ok = $status['ok'];
    if ($Ok)
    {
        $OFFON = "✅";
    }
    else
    {
        $OFFON = "❎";
    }
    $BOT->sendCommand('sendmessage', [
        'chat_id' => $chatId, 
        'text' => $BOT->language("text_main"), 
        'disable_web_page_preview' => 'true', 
        'parse_mode' => 'Markdown', 
        'reply_markup' => json_encode([
            'inline_keyboard' => [
                [['text' => $OFFON, 'callback_data' => 'statusOFFON'],['text' => $BOT->language("key_status"), 'callback_data' => '#']],
                [['text' => $BOT->language("Users"), 'callback_data' => 'Users'],['text' => $BOT->language("Admins"), 'callback_data' => 'Admins']],
                [['text' => $BOT->language("Prices"), 'callback_data' => 'Prices'],['text' => $BOT->language("profit"), 'callback_data' => 'Profit']],
                [['text' => $BOT->language("statsPhotos"), 'callback_data' => 'statsPhotos']]
            ]
        ])
    ]);
}

if($data == "main"){
    $BOT->states($id,'delete');
    $status = json_decode($BOT->bot("status", "Get") , true);
    $Ok = $status['ok'];
    if ($Ok)
    {
        $OFFON = "✅";
    }
    else
    {
        $OFFON = "❎";
    }
    $BOT->sendCommand('editMessageText', [
        'chat_id' => $chatId,
        'message_id' => $messageId, 
        'text' => $BOT->language("text_main"), 
        'disable_web_page_preview' => 'true', 
        'parse_mode' => 'Markdown', 
        'reply_markup' => json_encode([
            'inline_keyboard' => [
                [['text' => $OFFON, 'callback_data' => 'statusOFFON'],['text' => $BOT->language("key_status"), 'callback_data' => '#']],
                [['text' => $BOT->language("Users"), 'callback_data' => 'Users'],['text' => $BOT->language("Admins"), 'callback_data' => 'Admins']],
                [['text' => $BOT->language("Prices"), 'callback_data' => 'Prices'],['text' => $BOT->language("profit"), 'callback_data' => 'Profit']],
                [['text' => $BOT->language("statsPhotos"), 'callback_data' => 'statsPhotos']]
            ]
        ])
    ]);
}