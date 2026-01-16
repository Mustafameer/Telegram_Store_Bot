<?php 

if ($data == "Profit")
{
    $profits = json_decode($BOT->bot("profit", "Get") , true);
    $profitText = "";
    foreach($profits as $c => $n){
        $profitText .= $BOT->language($c) . " : $n IQD\n";
    }
    $BOT->sendCommand('editMessageText', [
        'chat_id' => $chatId,
        'message_id' => $messageId, 
        'text' => $BOT->language("profit").".\n".$profitText, 
        'disable_web_page_preview' => 'true', 
        'parse_mode' => 'Markdown', 
        'reply_markup' => json_encode([
            'inline_keyboard' => [
                [['text' => $BOT->language("Back"), 'callback_data' => 'main']]
            ]
        ]) 
    ]);
}