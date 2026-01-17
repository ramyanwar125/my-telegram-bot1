<?php
/*
تعديل البيانات الأساسية
*/
$API_KEY = "8220448877:AAF8mDyfUgnUWKX5B3VBozRz6Yjac5a34SQ";
$sudo = 7349033289; 

define('API_KEY',$API_KEY);
define("IDBot", explode(":", $API_KEY)[0]);

// دالة الاتصال بتليجرام
function bot($method, $datas=[]){
    $url = "https://api.telegram.org/bot".API_KEY."/".$method;
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, $datas);
    $res = curl_exec($ch);
    if(curl_error($ch)){
        var_dump(curl_error($ch));
    }else{
        return json_decode($res);
    }
}

// إعدادات المجلدات والملفات
$usrbot = bot("getme")->result->username;
define("USR_BOT", $usrbot);
define("X_", $usrbot);

if(!is_dir('BiFile')) mkdir('BiFile');
if(!is_dir('BiFile/'.USR_BOT)) mkdir('BiFile/'.USR_BOT);
if(!is_dir('onliner')) mkdir('onliner');
if(!is_dir('VI_DZ')) mkdir('VI_DZ');
if(!is_dir('VI_DZ/'.X_)) mkdir('VI_DZ/'.X_);

$config = [
    'admin'=> $sudo,
    'token'=> API_KEY,
    'type_up' => 'php://input',
    'member' => 'BiFile/'.USR_BOT.'/members.bot',
    'start_msg' => "» اهلا بك عزيزي\n» انت الان في بوت الدعمكم\n🔐 ايديك: #id",
];

// استقبال التحديثات
$update = json_decode(file_get_contents($config['type_up']));

if($update){
    $message = $update->message;
    $chat_id = $message->chat->id;
    $text = $message->text;
    $from_id = $message->from->id;
    $name = $message->from->first_name;

    // حفظ المستخدمين الجدد
    if(isset($chat_id)){
        $members = file_get_contents($config['member']);
        if(!strpos($members, (string)$chat_id)){
            file_put_contents($config['member'], $chat_id."\n", FILE_APPEND);
        }
    }

    // أوامر الآدمن
    if($from_id == $sudo){
        if($text == "/start"){
            bot("sendmessage",[
                'chat_id' => $chat_id,
                'text' => "» اهلا بك يا مطور في لوحة التحكم الخاصة بك 🛠",
                'reply_markup'=>json_encode([ 
                    'inline_keyboard'=>[
                        [['text'=>'قسم الإذاعة','callback_data'=>"broadcast"],['text'=>'الإحصائيات','callback_data'=>"statebot"]],
                        [['text'=>'إعدادات الاشتراك','callback_data'=>"shtraks"]]
                    ]
                ])
            ]);
        }
    } else {
        // أوامر المستخدم العادي
        if($text == "/start"){
            $msg = str_replace("#id", $from_id, $config['start_msg']);
            bot("sendmessage",[
                'chat_id' => $chat_id,
                'text' => $msg
            ]);
        }
    }
}

// لإبقاء صفحة Render تعمل بدون خطأ 404
echo "Bot is running...";
