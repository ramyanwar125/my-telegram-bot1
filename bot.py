import telebot
from telebot import types
import subprocess
import os
import signal
import logging
import json
import time
import re
import sys
import threading

# إعداد التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot_debug.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

STATE_FILE = "bot_state.json"
control_data = {}

# التوكن من متغير بيئي (مهم على Render)
BOT_TOKEN = os.getenv("BOT_TOKEN", "8348936725:AAEr4qGK16Tt51XBovCfPr2keZTDyg2mFwI")
bot = telebot.TeleBot(BOT_TOKEN)

ALLOWED_USERS = [7349033289]  # أضف chat_id الخاص بك هنا

def is_user_allowed(chat_id):
    return chat_id in ALLOWED_USERS

def save_state():
    try:
        state_to_save = {}
        for msg_id, data in control_data.items():
            state_to_save[msg_id] = {
                "chat_id": data["chat_id"],
                "file_path": data["file_path"],
                "state": data["state"],
                "proc_pid": data["proc"].pid if data.get("proc") and data["proc"].poll() is None else None,
                "libs": data.get("libs", [])
            }
        with open(STATE_FILE, "w") as f:
            json.dump(state_to_save, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving state: {e}")

def load_state():
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "r") as f:
                saved_state = json.load(f)
                for msg_id_str, data in saved_state.items():
                    msg_id = int(msg_id_str)
                    proc = None
                    if data.get("proc_pid"):
                        try:
                            proc = subprocess.Popen(["python3", data["file_path"]],
                                                    stdout=subprocess.PIPE,
                                                    stderr=subprocess.PIPE,
                                                    text=True)
                        except Exception as e:
                            logger.error(f"Failed to restart process {data['file_path']}: {e}")
                    control_data[msg_id] = {
                        "chat_id": data["chat_id"],
                        "proc": proc,
                        "file_path": data["file_path"],
                        "state": data["state"],
                        "libs": data.get("libs", [])
                    }
    except Exception as e:
        logger.error(f"Error loading state: {e}")

def extract_libraries(file_path):
    libs = set()
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        patterns = [
            r'^\s*import\s+([a-zA-Z0-9_]+)',
            r'^\s*from\s+([a-zA-Z0-9_]+)\s+import'
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, content, re.MULTILINE):
                lib = match.group(1).split('.')[0]
                if lib:
                    libs.add(lib)
        
        # استبعاد المكتبات القياسية
        std_libs = sys.stdlib_module_names
        libs = {lib for lib in libs if lib not in std_libs}
        
    except Exception as e:
        logger.error(f"Error extracting libs from {file_path}: {e}")
    
    return list(libs)

def build_keyboard(file_specific=True, msg_id=None):
    keyboard = types.InlineKeyboardMarkup()
    
    if file_specific:
        keyboard.row(
            types.InlineKeyboardButton("⏯️ إيقاف/تشغيل", callback_data=f"toggle_{msg_id}"),
            types.InlineKeyboardButton("🔄 إعادة تشغيل", callback_data=f"restart_{msg_id}")
        )
        keyboard.row(
            types.InlineKeyboardButton("📦 تنصيب المكتبات", callback_data=f"install_{msg_id}"),
            types.InlineKeyboardButton("🗑️ حذف", callback_data=f"delete_{msg_id}")
        )
        keyboard.row(
            types.InlineKeyboardButton("🔙 رجوع", callback_data="back_to_list")
        )
    else:
        keyboard.row(
            types.InlineKeyboardButton("📂 عرض الملفات", callback_data="list_files"),
            types.InlineKeyboardButton("❓ المساعدة", callback_data="help")
        )
    return keyboard

def build_files_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    
    if not control_data:
        keyboard.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main"))
        return keyboard
    
    for msg_id, data in control_data.items():
        file_name = os.path.basename(data["file_path"])
        status = "🟢" if data["state"] == "running" else "⏸️"
        btn = types.InlineKeyboardButton(
            f"{status} {file_name}",
            callback_data=f"file_{msg_id}"
        )
        keyboard.add(btn)
    
    keyboard.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main"))
    return keyboard

def check_running_files():
    for msg_id, data in list(control_data.items()):
        proc = data.get("proc")
        if proc and proc.poll() is not None and data["state"] == "running":
            try:
                new_proc = subprocess.Popen(
                    ["python3", data["file_path"]],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                control_data[msg_id]["proc"] = new_proc
                control_data[msg_id]["state"] = "running"
                logger.info(f"Restarted: {data['file_path']}")
                bot.send_message(
                    data["chat_id"],
                    f"♻️ تم إعادة تشغيل تلقائي: {os.path.basename(data['file_path'])}"
                )
            except Exception as e:
                logger.error(f"Restart failed: {e}")
                bot.send_message(data["chat_id"], f"❌ فشل إعادة التشغيل: {str(e)}")

@bot.message_handler(commands=["start"])
def start_handler(message):
    if not is_user_allowed(message.chat.id):
        bot.reply_to(message, "⛔ غير مسموح لك")
        return
    bot.reply_to(message, "أرسل ملف .py لتشغيله", reply_markup=build_keyboard(False))

@bot.message_handler(commands=["list"])
def list_handler(message):
    if not is_user_allowed(message.chat.id): return
    text = "الملفات الجارية:" if control_data else "لا توجد ملفات جارية"
    bot.reply_to(message, text, reply_markup=build_files_keyboard())

@bot.message_handler(content_types=["document"])
def document_handler(message):
    if not is_user_allowed(message.chat.id):
        bot.reply_to(message, "⛔ غير مسموح")
        return
    
    doc = message.document
    if not doc.file_name.lower().endswith(".py"):
        bot.reply_to(message, "يجب أن يكون الملف .py")
        return

    try:
        file_info = bot.get_file(doc.file_id)
        downloaded = bot.download_file(file_info.file_path)
        
        os.makedirs("downloads", exist_ok=True)
        path = os.path.join("downloads", doc.file_name)
        
        with open(path, "wb") as f:
            f.write(downloaded)
        
        libs = extract_libraries(path)
        libs_text = "\n".join(f"- {l}" for l in libs) if libs else "لا مكتبات خارجية"
        
        bot.reply_to(message, f"تم رفع الملف\n{doc.file_name}\n\nالمكتبات:\n{libs_text}\n\nجاري التشغيل...")
        
        proc = subprocess.Popen(
            ["python3", path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        msg = bot.send_message(
            message.chat.id,
            f"🛠 التحكم في: {doc.file_name}",
            reply_markup=build_keyboard(True, msg_id=None)  # سيتم تحديث msg_id لاحقاً
        )
        
        control_data[msg.message_id] = {
            "chat_id": message.chat.id,
            "proc": proc,
            "file_path": path,
            "state": "running",
            "libs": libs
        }
        save_state()
        
    except Exception as e:
        bot.reply_to(message, f"خطأ: {str(e)}")
        logger.error(e)

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if not is_user_allowed(call.message.chat.id):
        bot.answer_callback_query(call.id, "غير مسموح")
        return

    data = call.data

    # أزرار عامة
    if data == "list_files":
        bot.edit_message_text(
            "الملفات الجارية:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=build_files_keyboard()
        )
        return

    if data == "back_to_main" or data == "back_to_list":
        bot.edit_message_text(
            "أرسل ملف .py لبدء التشغيل",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=build_keyboard(False)
        )
        return

    # التعامل مع ملف معين
    if data.startswith("file_"):
        msg_id = int(data.split("_")[1])
        d = control_data.get(msg_id)
        if not d:
            bot.answer_callback_query(call.id, "الملف غير موجود")
            return
        name = os.path.basename(d["file_path"])
        status = "🟢 جاري" if d["state"] == "running" else "⏸️ متوقف"
        text = f"الملف: {name}\nالحالة: {status}"
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=build_keyboard(True, msg_id)
        )
        return

    # استخراج msg_id
    try:
        msg_id = int(data.split("_")[1])
    except:
        msg_id = call.message.message_id

    d = control_data.get(msg_id)
    if not d:
        bot.answer_callback_query(call.id, "غير موجود")
        return

    proc = d.get("proc")
    path = d["file_path"]
    name = os.path.basename(path)
    chat_id = d["chat_id"]

    if data.startswith("toggle_"):
        if d["state"] == "running":
            if proc and proc.poll() is None:
                proc.terminate()
                d["state"] = "paused"
                text = f"⏸ تم إيقاف: {name}"
        else:
            new_proc = subprocess.Popen(
                ["python3", path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            d["proc"] = new_proc
            d["state"] = "running"
            text = f"▶️ تم التشغيل: {name}"
        
        bot.edit_message_text(
            text,
            chat_id,
            call.message.message_id,
            reply_markup=build_keyboard(True, msg_id)
        )
        save_state()

    elif data.startswith("restart_"):
        if proc and proc.poll() is None:
            proc.terminate()
        try:
            new_proc = subprocess.Popen(
                ["python3", path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            d["proc"] = new_proc
            d["state"] = "running"
            text = f"♻️ تم إعادة التشغيل: {name}"
            bot.edit_message_text(
                text,
                chat_id,
                call.message.message_id,
                reply_markup=build_keyboard(True, msg_id)
            )
            save_state()
        except Exception as e:
            bot.answer_callback_query(call.id, f"فشل الإعادة: {str(e)}")

    elif data.startswith("delete_"):
        if proc and proc.poll() is None:
            proc.terminate()
        try:
            os.remove(path)
            control_data.pop(msg_id, None)
            save_state()
            bot.edit_message_text(
                f"🗑️ تم حذف: {name}",
                chat_id,
                call.message.message_id,
                reply_markup=build_files_keyboard()
            )
        except Exception as e:
            bot.answer_callback_query(call.id, f"فشل الحذف: {str(e)}")

    elif data.startswith("install_"):
        if not d.get("libs"):
            bot.answer_callback_query(call.id, "لا توجد مكتبات")
            return
        bot.edit_message_text(
            f"جاري تثبيت {len(d['libs'])} مكتبة...",
            chat_id,
            call.message.message_id
        )
        results = []
        for lib in d["libs"]:
            try:
                r = subprocess.run(["pip", "install", "--quiet", lib], capture_output=True)
                results.append(f"{'✔' if r.returncode == 0 else '✖'} {lib}")
            except:
                results.append(f"✖ {lib}")
        bot.edit_message_text(
            "نتائج التثبيت:\n" + "\n".join(results),
            chat_id,
            call.message.message_id,
            reply_markup=build_keyboard(True, msg_id)
        )

    bot.answer_callback_query(call.id)

def periodic_check():
    while True:
        check_running_files()
        save_state()
        time.sleep(60)

if __name__ == "__main__":
    load_state()
    threading.Thread(target=periodic_check, daemon=True).start()
    logger.info("Bot starting...")
    bot.infinity_polling()
