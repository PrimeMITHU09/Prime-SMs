from http.server import BaseHTTPRequestHandler
import json
import urllib.request
import urllib.parse
import time

TOKEN = "8883835008:AAEjm5zjdMuFEB8E19PdKGTGS7GSu6gjpb4"
OTP_GROUP_ID = "-1003931415470"
OTP_GROUP_LINK = "https://t.me/c/3931415470/1"
BOT_USERNAME = "PrimeRateSMS_bot" # আপনার বটের ইউজারনেম এখানে দিন

config = {
    "maintenance_mode": False,
    "announcement": "✨ স্বাগতম! আমাদের বটের সার্ভিস এখন সম্পূর্ণ সচল রয়েছে।",
    "websites": {
        "Primary Panel": {
            "url": "http://147.135.212.197/crapi/had/viewstats",
            "token": "QlFQSENBUzRpV1hcYYJXU3xwV2VSf2lVXI-YXmSFjnh0VZVGcoNzVA=="
        }
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

                if config["maintenance_mode"] and user_id != 8883835008:
                    self.send_telegram_message(chat_id, "⚠️ **বট বর্তমানে মেইনটেনেন্স মোডে আছে!**")
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
                        self.send_telegram_message(chat_id, f"🎉 নতুন সার্ভিস **{new_service}** যুক্ত হয়েছে!", self.admin_keyboard())
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

                        self.send_telegram_message(chat_id, f"🎉 {service} ({country}) এ {len(numbers)}টি নম্বর সফলভাবে যোগ করা হয়েছে!", self.admin_keyboard())
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
                    self.send_telegram_message(chat_id, "🔧 **Admin Control Panel**", self.admin_keyboard())

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
                        sms_text = self.fetch_sms_safely(assigned_num)

                        text = (
                            f"✅ আপনার নম্বর সফলভাবে বরাদ্দ করা হয়েছে:\n\n"
                            f"📱 **{assigned_num}**\n"
                            f"সার্ভিস: {service} ({country})\n\n"
                            f"📩 **Latest SMS/OTP:**\n{sms_text}"
                        )
                        
                        # নম্বরের নিচে Fetch SMS বাটন যুক্ত করা হলো
                        reply_markup = {
                            "inline_keyboard": [
                                [{"text": "🔄 Fetch SMS Code", "callback_data": f"fetch_{service}_{country}_{assigned_num}"}],
                                [{"text": "🔙 Main Menu", "callback_data": "back_home"}]
                            ]
                        }
                        self.edit_telegram_message(chat_id, message_id, text, reply_markup)

                        # গ্রুপে মেসেজ পাঠানোর সময় নিচে Get Number প্যানেল বাটন যুক্ত করা হলো
                        group_markup = {
                            "inline_keyboard": [
                                [{"text": "📥 Get Number Panel", "url": f"https://t.me/{BOT_USERNAME}?start=get"}]
                            ]
                        }
                        group_message = (
                            f"🚨 **New OTP Assigned Alert**\n"
                            f"👤 User: {user.get('first_name')} (`{user_id}`)\n"
                            f"📱 Number: `{assigned_num}`\n"
                            f"🌐 Service: {service} ({country})\n"
                            f"💬 Message: {sms_text}"
                        )
                        self.send_telegram_message(OTP_GROUP_ID, group_message, group_markup)

                elif data.startswith("fetch_"):
                    parts = data.split("_", 3)
                    service = parts[1]
                    country = parts[2]
                    assigned_num = parts[3]
                    
                    sms_text = self.fetch_sms_safely(assigned_num)
                    text = (
                        f"✅ নম্বর স্ট্যাটাস আপডেট:\n\n"
                        f"📱 **{assigned_num}**\n"
                        f"সার্ভিস: {service} ({country})\n\n"
                        f"📩 **Latest SMS/OTP:**\n{sms_text}"
                    )
                    reply_markup = {
                        "inline_keyboard": [
                            [{"text": "🔄 Fetch SMS Code", "callback_data": f"fetch_{service}_{country}_{assigned_num}"}],
                            [{"text": "🔙 Main Menu", "callback_data": "back_home"}]
                        ]
                    }
                    try:
                        self.edit_telegram_message(chat_id, message_id, text, reply_markup)
                    except:
                        pass

                elif data == "live_traffic":
                    total_nums = sum(len(nums) for s in database.values() for nums in s.values())
                    text = f"📊 **Live Stock Stats**\n📱 Total Active Numbers in Stock: {total_nums}"
                    self.edit_telegram_message(chat_id, message_id, text, {"inline_keyboard": [[{"text": "🔙 Back", "callback_data": "back_home"}]]})

                elif data == "my_profile":
                    text = f"👤 **User Profile**\n🔹 Name: {user.get('first_name')}\n🔹 User ID: `{user_id}`"
                    self.edit_telegram_message(chat_id, message_id, text, {"inline_keyboard": [[{"text": "🔙 Back", "callback_data": "back_home"}]]})

                elif data == "back_home":
                    self.edit_telegram_message(chat_id, message_id, "প্রধান মেনু:", self.main_menu())

                elif data == "admin_menu":
                    keyboard = {
                        "inline_keyboard": [
                            [{"text": "➕ Add New Service", "callback_data": "admin_add_service"}],
                            [{"text": "➕ Add Country/Number", "callback_data": "admin_edit_services"}],
                            [{"text": "🗑️ Delete / Manage Live Numbers", "callback_data": "admin_manage_stock"}],
                            [{"text": "🔙 Back", "callback_data": "back_home"}]
                        ]
                    }
                    self.edit_telegram_message(chat_id, message_id, "🛠️ **Admin Control Panel**", keyboard)

                elif data == "admin_add_service":
                    admin_sessions[user_id] = {"action": "add_service"}
                    self.edit_telegram_message(chat_id, message_id, "📝 নতুন সার্ভিসের নাম লিখুন:", {"inline_keyboard": [[{"text": "❌ Cancel", "callback_data": "admin_menu"}]]})

                elif data == "admin_edit_services":
                    keyboard = []
                    for s_name in database.keys():
                        keyboard.append([{"text": f"➕ Add to {s_name}", "callback_data": f"add_country_{s_name}"}])
                    keyboard.append([{"text": "🔙 Back", "callback_data": "admin_menu"}])
                    self.edit_telegram_message(chat_id, message_id, "📂 কোন সার্ভিসে নম্বর যোগ করতে চান?", {"inline_keyboard": keyboard})

                elif data.startswith("add_country_"):
                    service = data.split("_", 2)[2]
                    admin_sessions[user_id] = {"service": service, "step": "waiting_country"}
                    self.edit_telegram_message(chat_id, message_id, f"📝 **{service}** এর জন্য দেশের নাম ও ফ্ল্যাগ লিখুন:", {"inline_keyboard": [[{"text": "❌ Cancel", "callback_data": "admin_menu"}]]})

                elif data == "admin_manage_stock":
                    # লাইভ স্টক ডিলিট বা ম্যানেজ করার অপশন
                    keyboard = []
                    for s_name, countries in database.items():
                        for c_name, nums in countries.items():
                            keyboard.append([{"text": f"❌ Clear {s_name} ({c_name}: {len(nums)} left)", "callback_data": f"clear_stock_{s_name}_{c_name}"}])
                    keyboard.append([{"text": "🔙 Back", "callback_data": "admin_menu"}])
                    self.edit_telegram_message(chat_id, message_id, "🗑️ স্টক থেকে নির্দিষ্ট দেশের অবশিষ্টাংশ ডিলিট বা পরিষ্কার করতে নিচে ক্লিক করুন:", {"inline_keyboard": keyboard})

                elif data.startswith("clear_stock_"):
                    parts = data.split("_", 3)
                    s_name = parts[2]
                    c_name = parts[3]
                    if s_name in database and c_name in database[s_name]:
                        database[s_name][c_name] = [] # নম্বরগুলো ক্লিয়ার করে দেওয়া হলো
                    self.edit_telegram_message(chat_id, message_id, f"✅ সফলভাবে **{s_name} ({c_name})** এর বাকি সব লাইভ নম্বর ডিলিট বা রিমুভ করা হয়েছে!", {"inline_keyboard": [[{"text": "🔙 Back", "callback_data": "admin_menu"}]]})

            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        except Exception as e:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")

    def fetch_sms_safely(self, phone_number):
        try:
            active_panel = config["active_website"]
            panel_info = config["websites"].get(active_panel, {})
            api_url = panel_info.get("url")
            api_token = panel_info.get("token")

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
        keyboard.append([{"text": "🔙 Back", "callback_data": "back_home"}]]
        return {"inline_keyboard": keyboard}

    def admin_keyboard(self):
        return {
            "inline_keyboard": [
                [{"text": "⚙️ Admin Panel", "callback_data": "admin_menu"}]
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
        self.wfile.write(b"Bot is running with Fetch Code & Delete Stock System!")
