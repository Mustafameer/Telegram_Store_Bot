<?php 

require_once 'config.php';
require_once 'Control/main.class.php';
$BOT = new Main(API_KEY);


// reports
$Users = mysqli_query($db,"SELECT * FROM `users`");
$reportsTxt = "";
while ($user = mysqli_fetch_assoc($Users)){
    $reports = json_decode($user['report'],true);
    $res = "";
    foreach ($reports as $report=>$value){
        if(is_array($value) and count($value) != 0){
            $res .= $BOT->language($report)." : \n";
            foreach($value as $n => $t){
                $res .= "• $n:$t\n";
            }
        }else{
            if(!is_array($value)){
                $total = $value;
            }
        }
    }
    $GetChat = $BOT->GetChat($user['from_id']);
    $full_name = $GetChat["result"]["first_name"] . " " . $GetChat["result"]["last_name"];
    $reportsTxt .= $BOT->language("name")." : $full_name\n";
    $reportsTxt .= $BOT->language("id")." : ".$user['from_id']."\n";
    $reportsTxt .= sprintf($BOT->language("reportUser_text"),$total,$res) . "\n";
    $reportsTxt .= "===============\n";
}
$owners = json_decode($BOT->bot("owners", "Get") , true);
file_put_contents("reports.txt",$reportsTxt);
$BOT->sendCommand('sendDocument', ['chat_id' => $owners[0], 'document' => new CURLFile("reports.txt"),'caption'=>date("Y-m-d") ]);
unlink("reports.txt");

$report = '{"asiacell":{},"zain":{},"korek":{},"iraqsell":{},"alkafil":{},"creditrequest":{},"others":{},"netzain":{},"netasiacell":{},"total":"0"}';
$report = mysqli_real_escape_string($db, $report);
mysqli_query($db, "UPDATE `users` SET `report`='$report'");


// profits
$profits = json_decode($BOT->bot("profit", "Get") , true);
$profitText = "";
foreach($profits as $c => $n){
    $profitText .= $BOT->language($c) . " : $n IQD\n";
}
$BOT->sendCommand('sendmessage', ['chat_id' => $owners[0], 'text' => $BOT->language("profit").".\n".$profitText ]);
$profit = '{"asiacell":0,"zain":0,"korek":0,"iraqsell":0,"alkafil":0,"creditrequest":0,"others":0,"netzain":0,"netasiacell":0}';
$profit = mysqli_real_escape_string($db, $profit);
$BOT->bot("profit", "Set", $profit);