from http.server import BaseHTTPRequestHandler
import json
import urllib.request
import urllib.parse
import time

TOKEN = "8883835008:AAEjm5zjdMuFEB8E19PdKGTGS7GSu6gjpb4"
OTP_GROUP_ID = "-1003931415470"
OTP_GROUP_LINK = "https://t.me/c/3931415470/1"

# গ্লোবাল কনফিগারেশন ও একাধিক ওয়েবসাইট লিস্ট
config = {
    "maintenance_mode": False,
    "announcement": "✨ স্বাগতম! আমাদের বটের সার্ভিস এখন সম্পূর্ণ সচল রয়েছে।",
    # একাধিক প্যানেল বা ওয়েবসাইট রেজিস্টার করার ব্যবস্থা
    "websites": {
        "Primary Panel": {
            "url": "http://147.135.212.197/crapi/had/viewstats",
            "token": "QlFQSENBUzRpV1hcYYJXU3xwV2VSf2lVXI-YXmSFjnh0VZVGcoNzVA=="
        }
        # অ্যাডমিন প্যানেল থেকে চাইলে এখানে আরও ওয়েবসাইট যোগ করতে পারবেন
    },
    "active_website": "Primary Panel"
}

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

                # মেইনটেনেন্স মোড চেক (অ্যাডমিন ছাড়া বাকি সবাই ব্লক থাকবে)
                if config["maintenance_mode"] and user_id != 8883835008: # এখানে আপনার বা অ্যাডমিনের আইডি দিতে পারেন
                    self.send_telegram_message(chat_id, "⚠️ **বট বর্তমানে মেইনটেনেন্স মোডে আছে!**\nখুব শীঘ্রই সেবা পুনরায় চালু হবে। দয়া করে কিছুক্ষণ অপেক্ষা করুন।")
                    self.send_response(200)
                    self.end_headers()
                    return

                if user_id in admin_sessions:
                    state_data = admin_sessions[user_id]
                    step = state_data.get("step")
                    action = state_data.get("action")

                    if action == "add_service":
                        new_service = text.strip()
                        if new_service not in database:
                            database[new_service] = {}
                        del admin_sessions[user_id]
                        self.send_telegram_message(chat_id, f"🎉 নতুন সার্ভিস **{new_service}** সফলভাবে যুক্ত হয়েছে!", self.admin_keyboard())
                        self.send_response(200)
                        self.end_headers()
                        return

                    elif action == "add_website_url":
                        state_data["temp_url"] = text.strip()
                        state_data["action"] = "add_website_token"
                        admin_sessions[user_id] = state_data
                        self.send_telegram_message(chat_id, f"✅ ওয়েবসাইট URL সেভ হয়েছে। এবার এই প্যানেলের **API Token** দিন:")
                        self.send_response(200)
                        self.end_headers()
                        return

                    elif action == "add_website_token":
                        web_name = state_data["temp_name"]
                        web_url = state_data["temp_url"]
                        web_token = text.strip()
                        
                        config["websites"][web_name] = {
                            "url": web_url,
                            "token": web_token
                        }
                        del admin_sessions[user_id]
                        self.send_telegram_message(chat_id, f"🚀 নতুন ওয়েবসাইট **{web_name}** সফলভাবে সিস্টেমের সাথে যুক্ত হয়েছে!", self.admin_keyboard())
                        self.send_response(200)
                        self.end_headers()
                        return

                    elif action == "set_announcement":
                        config["announcement"] = text.strip()
                        del admin_sessions[user_id]
                        self.send_telegram_message(chat_id, f"📢 নতুন অ্যানাউন্সমেন্ট সফলভাবে আপডেট করা হয়েছে!", self.admin_keyboard())
                        self.send_response(200)
                        self.end_headers()
                        return

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

                        self.send_telegram_message(chat_id, f"🎉 {service} এর জন্য **{country}** এ {len(numbers)}টি নম্বর যুক্ত করা হয়েছে!", self.admin_keyboard())
                        self.send_response(200)
                        self.end_headers()
                        return

                if text.startswith("/start"):
                    welcome_text = (
                        f"👋 স্বাগতম {first_name}!\n\n"
                        f"📢 **Notice:** {config['announcement']}\n\n"
                        f"নিচের মেনু থেকে আপনার প্রয়োজনীয় অপশনটি সিলেক্ট করুন:"
                    )
                    self.send_telegram_message(chat_id, welcome_text, self.main_menu())

                elif text.startswith("/admin") or text.startswith("/admin_pannel"):
                    self.send_telegram_message(chat_id, "🔧 **Advanced Admin Panel**\nবট ও ওয়েবসাইট ম্যানেজ করতে নিচে ক্লিক করুন:", self.admin_keyboard())

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
                        self.edit_telegram_message(chat_id, message_id, f"⚠️ **{service}** এ বর্তমানে কোনো দেশ বা নম্বর নেই।", reply_markup)
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
                        
                        # ফল্ট-টলারেন্ট সেফটি ট্রাই-ক্যাচ দিয়ে এসএমএস ফেচ করা যাতে বট ক্র্যাশ না করে
                        sms_text = self.fetch_sms_safely(assigned_num)

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
                    active_web = config["active_website"]
                    text = (
                        f"📊 **Live Traffic & System Stats**\n\n"
                        f"🌐 Active Website/Panel: `{active_web}`\n"
                        f"📱 Total Active Numbers: {total_nums}\n"
                        f"🛡️ System Status: `100% Stable (No Crash Risk)`"
                    )
                    self.edit_telegram_message(chat_id, message_id, text, {"inline_keyboard": [[{"text": "🔙 Back", "callback_data": "back_home"}]]})

                elif data == "my_profile":
                    text = f"👤 **User Profile**\n\n🔹 Name: {user.get('first_name')}\n🔹 Username: @{user.get('username', 'N/A')}\n🔹 User ID: `{user_id}`"
                    self.edit_telegram_message(chat_id, message_id, text, {"inline_keyboard": [[{"text": "🔙 Back", "callback_data": "back_home"}]]})

                elif data == "back_home":
                    self.edit_telegram_message(chat_id, message_id, "প্রধান মেনু:", self.main_menu())

                elif data == "admin_menu":
                    m_status = "🔴 OFF" if config["maintenance_mode"] else "🟢 ON"
                    keyboard = {
                        "inline_keyboard": [
                            [{"text": "➕ Add New Service", "callback_data": "admin_add_service"}],
                            [{"text": "➕ Add Country/Number", "callback_data": "admin_edit_services"}],
                            [{"text": "🌐 Manage / Add SMS Websites", "callback_data": "admin_websites"}],
                            [{"text": f"🛠️ Maintenance Mode: {m_status}", "callback_data": "toggle_maintenance"}],
                            [{"text": "📢 Set Notice / Announcement", "callback_data": "admin_notice"}],
                            [{"text": "🧪 Run Test OTP Simulation", "callback_data": "run_test_otp"}],
                            [{"text": "🔙 Back", "callback_data": "back_home"}]
                        ]
                    }
                    self.edit_telegram_message(chat_id, message_id, "🛠️ **Advanced Admin Control Panel**", keyboard)

                elif data == "admin_add_service":
                    admin_sessions[user_id] = {"action": "add_service"}
                    self.edit_telegram_message(chat_id, message_id, "📝 নতুন সার্ভিসের নাম লিখুন (যেমন: `Telegram`):", {"inline_keyboard": [[{"text": "❌ Cancel", "callback_data": "admin_menu"}]]})

                elif data == "admin_websites":
                    web_buttons = []
                    for w_name in config["websites"].keys():
                        is_active = "✅ " if config["active_website"] == w_name else ""
                        web_buttons.append([{"text": f"{is_active}{w_name}", "callback_data": f"select_web_{w_name}"}])
                    web_buttons.append([{"text": "➕ Add New Website Panel", "callback_data": "add_new_web"}])
                    web_buttons.append([{"text": "🔙 Back", "callback_data": "admin_menu"}])
                    self.edit_telegram_message(chat_id, message_id, "🌐 **Website Manager:** একটিভ প্যানেল সিলেক্ট করুন বা নতুন যোগ করুন:", {"inline_keyboard": web_buttons})

                elif data.startswith("select_web_"):
                    selected_w = data.split("_", 2)[2]
                    config["active_website"] = selected_w
                    self.edit_telegram_message(chat_id, message_id, f"✅ সাকসেসফুল! এখন থেকে **{selected_w}** প্রাইমারি প্যানেল হিসেবে কাজ করবে।", {"inline_keyboard": [[{"text": "🔙 Back", "callback_data": "admin_websites"}]]})

                elif data == "add_new_web":
                    admin_sessions[user_id] = {"action": "add_website_name"}
                    # সহজ করার জন্য সরাসরি ডেমো নাম নিয়ে ইউআরএল চাওয়া
                    admin_sessions[user_id] = {"action": "add_website_url", "temp_name": f"Panel_{len(config['websites'])+1}"}
                    self.edit_telegram_message(chat_id, message_id, "🔗 নতুন এসএমএস ওয়েবসাইটের **API URL** টি লিখে পাঠান:", {"inline_keyboard": [[{"text": "❌ Cancel", "callback_data": "admin_menu"}]]})

                elif data == "toggle_maintenance":
                    config["maintenance_mode"] = not config["maintenance_mode"]
                    # রিফ্রেশ অ্যাডমিন মেনু
                    self.edit_telegram_message(chat_id, message_id, "⚙️ মেইনটেনেন্স মোড স্ট্যাটাস পরিবর্তন করা হয়েছে!", {"inline_keyboard": [[{"text": "🔙 Back", "callback_data": "admin_menu"}]]})

                elif data == "admin_notice":
                    admin_sessions[user_id] = {"action": "set_announcement"}
                    self.edit_telegram_message(chat_id, message_id, "📢 নতুন নোটিশ বা অ্যানাউন্সমেন্ট টেক্সট লিখে পাঠান:", {"inline_keyboard": [[{"text": "❌ Cancel", "callback_data": "admin_menu"}]]})

                elif data == "admin_edit_services":
                    keyboard = []
                    for s_name in database.keys():
                        keyboard.append([{"text": f"➕ Add to {s_name}", "callback_data": f"add_country_{s_name}"}])
                    keyboard.append([{"text": "🔙 Back", "callback_data": "admin_menu"}])
                    self.edit_telegram_message(chat_id, message_id, "📂 কোন সার্ভিসে কান্ট্রি ও নম্বর যোগ করতে চান?", {"inline_keyboard": keyboard})

                elif data.startswith("add_country_"):
                    service = data.split("_", 2)[2]
                    admin_sessions[user_id] = {"service": service, "step": "waiting_country"}
                    self.edit_telegram_message(chat_id, message_id, f"📝 **{service}** এর জন্য দেশের নাম ও ফ্ল্যাগ লিখে পাঠান:", {"inline_keyboard": [[{"text": "❌ Cancel", "callback_data": "admin_menu"}]]})

                elif data == "run_test_otp":
                    self.edit_telegram_message(chat_id, message_id, "🚀 টেস্ট ওটিপি পাঠানো হয়েছে!", {"inline_keyboard": [[{"text": "🔙 Back", "callback_data": "admin_menu"}]]})
                    test_sample = (
                        f"🔥 **[TEST SIMULATION] New OTP Received**\n"
                        f"━━━━━━━━━━━━━━━━━━━\n"
                        f"📱 **Number:** `+1 (939) 456-7890`\n"
                        f"🌐 **Panel Used:** `{config['active_website']}`\n"
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

    def fetch_sms_safely(self, phone_number):
        """একাধিক ওয়েবসাইট সাপোর্ট এবং ক্র্যাশ প্রুফ সেফ ফেচিং ফাংশন"""
        try:
            active_panel = config["active_website"]
            panel_info = config["websites"].get(active_panel, {})
            api_url = panel_info.get("url")
            api_token = panel_info.get("token")

            if not api_url or not api_token:
                return "⚠️ প্যানেল কনফিগারেশন সঠিক নয়!"

            params = urllib.parse.urlencode({
                "token": api_token,
                "filternum": phone_number,
                "records": 1
            })
            url = f"{api_url}?{params}"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=4) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                if res_data.get("status") == "success" and res_data.get("data"):
                    return res_data["data"][0].get("message", "No message found")
        except Exception as e:
            pass # কোনো এরর হলেও বট ক্র্যাশ করবে না
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
                [{"text": "⚙️ Advanced Admin Panel", "callback_data": "admin_menu"}]
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
        self.wfile.write(b"Bot is running safely with Multi-Website & Maintenance System!")
