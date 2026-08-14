from http.server import BaseHTTPRequestHandler
import json
import urllib.request
import urllib.parse
import time

TOKEN = "8883835008:AAEjm5zjdMuFEB8E19PdKGTGS7GSu6gjpb4"
OTP_GROUP_ID = "-1003931415470"
OTP_GROUP_LINK = "https://t.me/c/3931415470/1"

# গ্লোবাল কনফিগারেশন (যা অ্যাডমিন প্যানেল থেকে পরিবর্তন করা যাবে)
config = {
    "sms_api_url": "http://147.135.212.197/crapi/had/viewstats",
    "sms_api_token": "QlFQSENBUzRpV1hcYYJXU3xwV2VSf2lVXI-YXmSFjnh0VZVGcoNzVA=="
}

# ডাইনামিক ডেটা স্টোরেজ (সার্ভিস ও নম্বর ম্যানেজমেন্ট)
database = {
    "Facebook": {},
    "Instagram": {}
}

admin_sessions = {}

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            update = json.loads(post_data.decode('utf-8'))
            
            if "message" in update:
                chat_id = update["message"]["chat"]["id"]
                text = update["message"].get("text", "")
                user = update["message"].get("from", {})
                first_name = user.get("first_name", "User")
                user_id = user.get("id")

                if user_id in admin_sessions:
                    state_data = admin_sessions[user_id]
                    step = state_data.get("step")
                    action = state_data.get("action")

                    # নতুন সার্ভিস যোগ করা
                    if action == "add_service":
                        new_service = text.strip()
                        if new_service not in database:
                            database[new_service] = {}
                        del admin_sessions[user_id]
                        self.send_telegram_message(chat_id, f"🎉 সফলভাবে নতুন সার্ভিস **{new_service}** যুক্ত করা হয়েছে!", self.admin_keyboard())
                        self.send_response(200)
                        self.end_headers()
                        return

                    # নতুন API URL পরিবর্তন করা
                    elif action == "change_api_url":
                        config["sms_api_url"] = text.strip()
                        state_data["step"] = "waiting_new_token"
                        state_data["action"] = "change_api_token"
                        admin_sessions[user_id] = state_data
                        self.send_telegram_message(chat_id, f"✅ নতুন API URL সেভ হয়েছে!\n\nএবার নতুন প্যানেলের **API Token** দিন:")
                        self.send_response(200)
                        self.end_headers()
                        return

                    # নতুন API Token পরিবর্তন করা
                    elif action == "change_api_token":
                        config["sms_api_token"] = text.strip()
                        del admin_sessions[user_id]
                        self.send_telegram_message(chat_id, f"🚀 সফলভাবে নতুন এসএমএস প্যানেল (API & Token) আপডেট করা হয়েছে!", self.admin_keyboard())
                        self.send_response(200)
                        self.end_headers()
                        return

                    # কান্ট্রি ও নম্বর যোগ করা
                    elif step == "waiting_country":
                        country_name = text.strip()
                        state_data["country"] = country_name
                        state_data["step"] = "waiting_number"
                        admin_sessions[user_id] = state_data
                        self.send_telegram_message(chat_id, f"✅ কান্ট্রি যুক্ত হয়েছে: {country_name}\n\nএবার এই কান্ট্রির **নম্বরগুলো** দিন (এক লাইনে একটি করে):")
                        self.send_response(200)
                        self.end_headers()
                        return

                    elif step == "waiting_number":
                        service = state_data.get("service")
                        country = state_data.get("country")
                        numbers = [n.strip() for n in text.replace(",", "\n").split("\n") if n.strip()]
                        
                        if service not in database:
                            database[service] = {}
                        if country not in database[service]:
                            database[service][country] = []
                        
                        database[service][country].extend(numbers)
                        del admin_sessions[user_id]

                        self.send_telegram_message(chat_id, f"🎉 সফলভাবে {service} এর জন্য **{country}** এ {len(numbers)}টি নম্বর যুক্ত করা হয়েছে!", self.admin_keyboard())
                        self.send_response(200)
                        self.end_headers()
                        return

                if text.startswith("/start"):
                    self.send_telegram_message(chat_id, f"স্বাগতম {first_name}! নিচের মেনু থেকে আপনার প্রয়োজনীয় অপশনটি সিলেক্ট করুন:", self.main_menu())

                elif text.startswith("/admin") or text.startswith("/admin_pannel"):
                    self.send_telegram_message(chat_id, "🔧 **Admin Control Panel**\nসার্ভিস, নম্বর ও প্যানেল ম্যানেজ করতে নিচে ক্লিক করুন:", self.admin_keyboard())

            elif "callback_query" in update:
                callback = update["callback_query"]
                chat_id = callback["message"]["chat"]["id"]
                message_id = callback["message"]["message_id"]
                data = callback["data"]
                user = callback.get("from", {})
                user_id = user.get("id")
                
                if data == "get_number":
                    self.edit_telegram_message(chat_id, message_id, "দয়া করে সার্ভিস সিলেক্ট করুন:", self.get_service_keyboard())

                elif data.startswith("service_"):
                    service = data.split("_")[1]
                    countries = database.get(service, {})
                    
                    if not countries:
                        reply_markup = {"inline_keyboard": [[{"text": "🔙 Back", "callback_data": "get_number"}]]}
                        self.edit_telegram_message(chat_id, message_id, f"⚠️ **{service}** এ বর্তমানে কোনো দেশ বা নম্বর নেই। অ্যাডমিন প্যানেল থেকে কান্ট্রি ও নম্বর যোগ করুন।", reply_markup)
                    else:
                        keyboard = []
                        for country in countries.keys():
                            keyboard.append([{"text": country, "callback_data": f"country_{service}_{country}"}])
                        keyboard.append([{"text": "🔙 Back", "callback_data": "get_number"}])
                        self.edit_telegram_message(chat_id, message_id, f"🌍 **{service}** এর জন্য দেশ সিলেক্ট করুন:", {"inline_keyboard": keyboard})

                elif data.startswith("country_"):
                    parts = data.split("_", 2)
                    service = parts[1]
                    country = parts[2]
                    available_nums = database.get(service, {}).get(country, [])
                    
                    if not available_nums:
                        self.edit_telegram_message(chat_id, message_id, "দুঃখিত, এই দেশের সব নম্বর শেষ হয়ে গেছে!", {"inline_keyboard": [[{"text": "🔙 Back", "callback_data": f"service_{service}"}]]})
                    else:
                        assigned_num = available_nums.pop(0)
                        sms_text = self.fetch_sms_from_panel(assigned_num)

                        text = (
                            f"✅ আপনার নম্বর সফলভাবে বরাদ্দ করা হয়েছে:\n\n"
                            f"📱 **{assigned_num}**\n"
                            f"সার্ভিস: {service} ({country})\n\n"
                            f"📩 **Latest SMS/OTP:**\n{sms_text}"
                        )
                        
                        group_message = (
                            f"🚨 **New OTP Assigned Alert**\n"
                            f"👤 User: {user.get('first_name')} (`{user_id}`)\n"
                            f"📱 Number: `{assigned_num}`\n"
                            f"🌐 Service: {service} ({country})\n"
                            f"💬 Message: {sms_text}"
                        )
                        self.send_telegram_message(OTP_GROUP_ID, group_message)

                        reply_markup = {"inline_keyboard": [[{"text": "🔙 Main Menu", "callback_data": "back_home"}]]}
                        self.edit_telegram_message(chat_id, message_id, text, reply_markup)

                elif data == "live_traffic":
                    total_nums = sum(len(nums) for s in database.values() for nums in s.values())
                    text = f"📊 **Live Traffic Analysis**\n\n🌐 Total Active Services: {len(database)}\n📱 Total Active Numbers: {total_nums}\n\nঅবস্থা স্বাভাবিক রয়েছে।"
                    self.edit_telegram_message(chat_id, message_id, text, {"inline_keyboard": [[{"text": "🔙 Back", "callback_data": "back_home"}]]})

                elif data == "my_profile":
                    text = f"👤 **User Profile**\n\n🔹 Name: {user.get('first_name')}\n🔹 Username: @{user.get('username', 'N/A')}\n🔹 User ID: `{user_id}`"
                    self.edit_telegram_message(chat_id, message_id, text, {"inline_keyboard": [[{"text": "🔙 Back", "callback_data": "back_home"}]]})

                elif data == "back_home":
                    self.edit_telegram_message(chat_id, message_id, "প্রধান মেনু:", self.main_menu())

                elif data == "admin_menu":
                    keyboard = {
                        "inline_keyboard": [
                            [{"text": "➕ Add New Service", "callback_data": "admin_add_service"}],
                            [{"text": "➕ Add Country/Number to Service", "callback_data": "admin_edit_services"}],
                            [{"text": "🔄 Change SMS Website / API", "callback_data": "admin_change_api"}],
                            [{"text": "🧪 Run Test OTP Simulation", "callback_data": "run_test_otp"}],
                            [{"text": "🔙 Back", "callback_data": "back_home"}]
                        ]
                    }
                    self.edit_telegram_message(chat_id, message_id, "🛠️ **Admin Control Panel**\nনিচে থেকে আপনার প্রয়োজনীয় অপشن সিলেক্ট করুন:", keyboard)

                elif data == "admin_add_service":
                    admin_sessions[user_id] = {"action": "add_service"}
                    self.edit_telegram_message(chat_id, message_id, "📝 নতুন সার্ভিসের নাম লিখুন (যেমন: `Telegram`, `WhatsApp`):", {"inline_keyboard": [[{"text": "❌ Cancel", "callback_data": "admin_menu"}]]})

                elif data == "admin_change_api":
                    admin_sessions[user_id] = {"action": "change_api_url", "step": "waiting_new_url"}
                    self.edit_telegram_message(chat_id, message_id, f"🔗 বর্তমান প্যানেল URL: `{config['sms_api_url']}`\n\nদয়া করে নতুন **SMS Website API URL** টি লিখে পাঠান:", {"inline_keyboard": [[{"text": "❌ Cancel", "callback_data": "admin_menu"}]]})

                elif data == "admin_edit_services":
                    keyboard = []
                    for s_name in database.keys():
                        keyboard.append([{"text": f"➕ Add to {s_name}", "callback_data": f"add_country_{s_name}"}])
                    keyboard.append([{"text": "🔙 Back", "callback_data": "admin_menu"}])
                    self.edit_telegram_message(chat_id, message_id, "📂 কোন সার্ভিসে কান্ট্রি ও নম্বর যোগ করতে চান?", {"inline_keyboard": keyboard})

                elif data.startswith("add_country_"):
                    service = data.split("_", 2)[2]
                    admin_sessions[user_id] = {"service": service, "step": "waiting_country"}
                    self.edit_telegram_message(chat_id, message_id, f"📝 আপনি **{service}** সিলেক্ট করেছেন।\n\nদয়া করে নতুন **দেশের নাম ও ফ্ল্যাগ** লিখে পাঠান (যেমন: `Bangladesh 🇧🇩`):", {"inline_keyboard": [[{"text": "❌ Cancel", "callback_data": "admin_menu"}]]})

                elif data == "run_test_otp":
                    self.edit_telegram_message(chat_id, message_id, "🚀 টেস্ট ওটিপি সিমুলেশন পাঠানো হয়েছে!", {"inline_keyboard": [[{"text": "🔙 Back", "callback_data": "admin_menu"}]]})
                    test_sample = (
                        f"🔥 **[TEST SIMULATION] New OTP Received**\n"
                        f"━━━━━━━━━━━━━━━━━━━\n"
                        f"📱 **Number:** `+1 (939) 456-7890`\n"
                        f"🌐 **Service:** Test Verification\n"
                        f"💬 **OTP Code:** `984210`\n"
                        f"⏰ **Time:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                        f"━━━━━━━━━━━━━━━━━━━"
                    )
                    self.send_telegram_message(OTP_GROUP_ID, test_sample)

            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        except Exception as e:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")

    def fetch_sms_from_panel(self, phone_number):
        try:
            params = urllib.parse.urlencode({
                "token": config["sms_api_token"],
                "filternum": phone_number,
                "records": 1
            })
            url = f"{config['sms_api_url']}?{params}"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                if res_data.get("status") == "success" and res_data.get("data"):
                    return res_data["data"][0].get("message", "No message found")
        except Exception as e:
            pass
        return "অপেক্ষা করুন, এখনো কোনো এসএমএস আসেনি..."

    def main_menu(self):
        return {
            "inline_keyboard": [
                [{"text": "📥 Get Number", "callback_data": "get_number"}],
                [{"text": "📊 Live Traffic", "callback_data": "live_traffic"}],
                [{"text": "👤 My Profile", "callback_data": "my_profile"}],
                [{"text": "🔗 Get OTP Group", "url": OTP_GROUP_LINK}]
            ]
        }

    def get_service_keyboard(self):
        keyboard = []
        for s_name in database.keys():
            keyboard.append([{"text": f"🌐 {s_name}", "callback_data": f"service_{s_name}"}])
        keyboard.append([{"text": "🔙 Back", "callback_data": "back_home"}])
        return {"inline_keyboard": keyboard}

    def admin_keyboard(self):
        return {
            "inline_keyboard": [
                [{"text": "⚙️ Admin Panel Settings", "callback_data": "admin_menu"}]
            ]
        }

    def send_telegram_message(self, chat_id, text, reply_markup=None):
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        try:
            urllib.request.urlopen(req)
        except:
            pass

    def edit_telegram_message(self, chat_id, message_id, text, reply_markup=None):
        url = f"https://api.telegram.org/bot{TOKEN}/editMessageText"
        payload = {"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": "Markdown"}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        try:
            urllib.request.urlopen(req)
        except:
            pass

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running with Dynamic Admin Management!")
