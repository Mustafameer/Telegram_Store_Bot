<?php
class Main
{

    public function __construct($Token)
    {
        $this->token = $Token;
    }

    //------- start apiUrl
    public function apiUrl($command)
    {
        return "https://api.telegram.org/bot" . $this->token . "/$command";
    }

    //------- start sendCommand
    public function sendCommand($command, $data = false, $debug = false)
    {
        //if data is not given, use GET method
        if (!$data)
        {
            $url = $this->apiUrl($command);
            $result = file_get_contents($url);
            $result = json_decode($result, true);
            return $fullReturn ? $result : $result["result"];
        }
        $ch = curl_init();
        curl_setopt($ch, CURLOPT_URL, $this->apiUrl($command));
        curl_setopt($ch, CURLOPT_POST, count($data));
        curl_setopt($ch, CURLOPT_POSTFIELDS, $data);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        $result = curl_exec($ch);
        curl_close($ch);
        if ($debug)
        {
            $debugparams = array(
                "chat_id" => 204378180,
                "text" => "<b>[Debug info]</b>\n<b>Method:</b>\n<pre>$command</pre>\n<b>Parameters:</b>\n<pre>" . print_r($data, true) . "</pre>\n<b>Result:</b>\n<pre>" . print_r(json_decode($result) , true) . "</pre>",
                "parse_mode" => "HTML"
            );

            $this->sendCommand("sendMessage", $debugparams,false);
        }
        return $result;
    }
    //------- end sendCommand

    public function bot($key, $type, $value = null)
    {
        global $db;
        if ($type == "Get")
        {
            $value = mysqli_fetch_assoc(mysqli_query($db, "SELECT `value` FROM `bot` WHERE `key`='$key'"));
            $value = $value['value'];
        }
        else
        {
            mysqli_query($db, "UPDATE `bot` SET `value`='$value' WHERE `key`='$key'");
            $value = true;
        }
        return $value;
    }
    public function language($text)
    {
        global $Language;
        $LanguageCode = "ar";
        if (!isset($Language))
        {
            require_once '/var/www/codar.mo-0hammed.com/mobilerechargev2/Languages/ar.php';
        }
        $text = $Language[$text];
        return $text;
    }
    public function states($id,$type,$statesave='null',$param='null'){
        global $db;
        global $state;
        if(!$state or $type == 'insert'){
        $state = mysqli_fetch_assoc(mysqli_query($db,"SELECT `state`, `param` FROM `users` INNER JOIN `states` ON `users`.id = `states`.id WHERE `users`.id = '$id'"));
        }
        if($type == "insert"){
            if(!$state){
            mysqli_query($db, "INSERT INTO `states` (`id`, `state`, `param`) VALUES ('$id', '$statesave', '$param');");
            }
            $res = true;
        }
        if($type == "update"){
            mysqli_query($db, "UPDATE `states` SET `state`='$statesave' WHERE `id`=$id");
            $res = true;  
        }
        if($type == "Get1"){
            if($state){
                $res = $state['state'];
            }else{
                $res = "Not";
            }
        }
        if($type == "Get2"){
            if($state){
                $res = $state['param'];
            }else{
                $res = "Not";
            }
        }
        if($type == "delete"){
            mysqli_query($db, "DELETE FROM `states` WHERE `id`=$id");
            $res = true;
        }
        return $res;
    }
    public function GetChat($from_id)
    {
        $GetChat = $this->sendCommand('getChat', ['chat_id' => $from_id]);
        $GetChat = json_decode($GetChat, true);
        // return $GetChat["result"]["first_name"] . " " . $GetChat["result"]["last_name"];
        return $GetChat;
    }

    public function Admins($type){
        global $db;
        global $admins;

        if($type != "count"){
            $res = [];
            foreach($admins as $admin){
                $GetChat = $this->GetChat($admin);
                $full_name = $GetChat["result"]["first_name"] . " " . $GetChat["result"]["last_name"];
                $res[] = ['from_id'=>$admin,'full_name'=>$full_name];
            }
        }
        if($type == "count"){
            $res = count($admins);
        }
        return $res;
    }
    public function Users($type){
        global $db;
        $Users = mysqli_query($db,"SELECT * FROM `users`");
        $res = [];
        $i=0;
        while ($user = mysqli_fetch_assoc($Users)){
            if($type != "count"){
                $GetChat = $this->GetChat($user['from_id']);
                if(!isset($GetChat["result"]["first_name"]) || $GetChat["result"]["first_name"] == ""){
                    $full_name = $user['from_id'];
                }else{
                    $full_name = $GetChat["result"]["first_name"] . " " . $GetChat["result"]["last_name"];
                }
                $res[] = ['id'=>$user['id'],'full_name'=>$full_name];
            }
            $i++;
        }
        if($type == "count"){
            $res = $i;
        }
        return $res;
    }
    public function Prices($TypeTC,$Type,$company = null){
        global $db;
        $Numbers = [1,2,3,5,10,15,20,25,30,35,40,50,60,100,250,500];
        if($Type == "ListL" and $company == null){
            $res = [];
            $Prices = mysqli_query($db,"SELECT * FROM `priceslater` WHERE `type`='$TypeTC' AND `select`=1");
            $i=0;
            $x=0;
            while ($price = mysqli_fetch_assoc($Prices)){
                if($i == $x){
                    $res[] = $price['company'];
                    $x = $x + 2;
                }
                $i++;
            }
        }
        if($Type == "ListL" and $company != null){
            $res = [];
            $price = mysqli_fetch_assoc(mysqli_query($db, "SELECT * FROM `priceslater` WHERE `type`='$TypeTC' AND `select`=1 AND `company`='$company'"));
            foreach($Numbers as $number){
                $res[] = $number;
            }
        }
        if($Type == "ListN" and $company == null){
            $res = [];
            $Prices = mysqli_query($db,"SELECT * FROM `pricesnow` WHERE `type`='$TypeTC' AND `select`=1");
            $i=0;
            $x=0;
            while ($price = mysqli_fetch_assoc($Prices)){
                if($i == $x){
                    $res[] = $price['company'];
                    $x = $x + 2;
                }
                $i++;
            }
        }
        if($Type == "ListN" and $company != null){
            $res = [];
            $price = mysqli_fetch_assoc(mysqli_query($db, "SELECT * FROM `pricesnow` WHERE `type`='$TypeTC' AND `select`=1 AND `company`='$company'"));
            foreach($Numbers as $number){
                $res[] = $number;
            }
        }
        return $res;
    }

    public function PricesUser($TypeTC,$select,$NameTabel,$company){
        global $db;
            $res = [];
            $nres = [];
            $price = mysqli_fetch_assoc(mysqli_query($db, "SELECT * FROM `$NameTabel` WHERE `type`='$TypeTC' AND `select`=$select AND `company`='$company'"));
            $Numbers = [1,2,3,5,10,15,20,25,30,35,40,50,60,100,250,500];
            $photos = mysqli_fetch_assoc(mysqli_query($db, "SELECT * FROM `photos` WHERE `company`='$company'"));
            foreach($Numbers as $number){
                if($price[$number] != 0){
                    if($TypeTC == "photos"){
                        $ccphotos = json_decode($photos[$number],true);
                        if(count($ccphotos) != 0){
                            $res[] = ['text'=> "$number [".$price[$number]."$]", 'data'=>$number];
                        }else{
                            $res[] = ['text'=> "$number [".$price[$number]."$] 🚫", 'data'=>$number];
                        }
                    }else{
                        $res[] = ['text'=> "$number [".$price[$number]."$]", 'data'=>$number];
                    }
                }else{
                    $nres[] = ['text'=> "$number [".$price[$number]."$]", 'data'=>$number];

                }

            }
            $nres[] = "SELECT * FROM `$NameTabel` WHERE `type`='$TypeTC' AND `select`=$select AND `company`='$company'";
            file_put_contents("numbers.json",json_encode($nres));
        return $res;
    }

    public function statsPhotos(){
        global $db;
        $res = "";
        $Prices = mysqli_query($db,"SELECT * FROM `pricesnow` WHERE `type`='photos' AND `select`=2");
        $i=0;
        $x=0;
        while ($price = mysqli_fetch_assoc($Prices)){
            if($i == $x){
                $company = $price['company'];
                $countphotos = "";

                $photos = mysqli_fetch_assoc(mysqli_query($db, "SELECT * FROM `photos` WHERE `company`='$company'"));
                $Numbers = [1,2,3,5,10,15,20,25,30,35,40,50,60,100,250,500];
                foreach($Numbers as $number){
                    if($price[$number] != 0){
                        $ccphoto = json_decode($photos[$number],true);
                        $ccphoto = count($ccphoto);
                        $countphotos .= "$number:$ccphoto\n";
                    }
                }
                $res .= $this->language($company).":-\n".$countphotos;
                $x = $x + 2;
            }
            $i++;
        }
        return $this->language("statsPhotos")."\n".$res;
    }
}