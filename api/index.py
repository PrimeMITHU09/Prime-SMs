from http.server import BaseHTTPRequestHandler
import json
import urllib.request
import urllib.parse
import time

TOKEN = "8883835008:AAEjm5zjdMuFEB8E19PdKGTGS7GSu6gjpb4"
OTP_GROUP_ID = "-1003931415470"
OTP_GROUP_LINK = "https://t.me/c/3931415470/1"

SMS_API_URL = "http://147.135.212.197/crapi/had/viewstats"
SMS_API_TOKEN = "QlFQSENBUzRpV1hcYYJXU3xwV2VSf2lVXI-YXmSFjnh0VZVGcoNzVA=="

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
                    service = state_data.get("service")

                    if step == "waiting_country":
                        country_name = text.strip()
                        state_data["country"] = country_name
                        state_data["step"] = "waiting_number"
                        admin_sessions[user_id] = state_data
                        self.send_telegram_message(chat_id, f"✅ কান্ট্রি যুক্ত হয়েছে: {country_name}\n\nএবার এই কান্ট্রির **নম্বরগুলো** দিন (এক লাইনে একটি করে):")
                        self.send_response(200)
                        self.end_headers()
                        return

                    elif step == "waiting_number":
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
                    self.send_telegram_message(chat_id, "🔧 **Admin Panel**\nসেটিংস এবং টেস্ট অপশন নিচে দেওয়া হলো:", self.admin_keyboard())

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
                        keyboard.append([{"text": "🔙 Back", "callback_data": "get_number"}],)
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
                    fb_count = sum(len(nums) for nums in database.get("Facebook", {}).values())
                    insta_count = sum(len(nums) for nums in database.get("Instagram", {}).values())
                    text = f"📊 **Live Traffic Analysis**\n\n📘 Facebook Total Active Numbers: {fb_count}\n📷 Instagram Total Active Numbers: {insta_count}\n\nঅবস্থা স্বাভাবিক রয়েছে।"
                    self.edit_telegram_message(chat_id, message_id, text, {"inline_keyboard": [[{"text": "🔙 Back", "callback_data": "back_home"}]]})

                elif data == "my_profile":
                    text = f"👤 **User Profile**\n\n🔹 Name: {user.get('first_name')}\n🔹 Username: @{user.get('username', 'N/A')}\n🔹 User ID: `{user_id}`"
                    self.edit_telegram_message(chat_id, message_id, text, {"inline_keyboard": [[{"text": "🔙 Back", "callback_data": "back_home"}]]})

                elif data == "back_home":
                    self.edit_telegram_message(chat_id, message_id, "প্রধান মেনু:", self.main_menu())

                elif data == "admin_edit_services":
                    keyboard = {
                        "inline_keyboard": [
                            [{"text": "➕ Add Country/Number (Facebook)", "callback_data": "add_country_Facebook"}],
                            [{"text": "➕ Add Country/Number (Instagram)", "callback_data": "add_country_Instagram"}],
                            [{"text": "🧪 Run Test OTP Simulation (Group Test)", "callback_data": "run_test_otp"}],
                            [{"text": "🔙 Back", "callback_data": "back_home"}]
                        ]
                    }
                    self.edit_telegram_message(chat_id, message_id, "🛠️ অ্যাডমিন কন্ট্রোল প্যানেল:", keyboard)

                elif data.startswith("add_country_"):
                    service = data.split("_")[2]
                    admin_sessions[user_id] = {"service": service, "step": "waiting_country"}
                    self.edit_telegram_message(chat_id, message_id, f"📝 আপনি **{service}** সিলেক্ট করেছেন।\n\nদয়া করে এখন নতুন **দেশের নাম ও ফ্ল্যাগ** লিখে পাঠান:", {"inline_keyboard": [[{"text": "❌ Cancel", "callback_data": "admin_edit_services"}]]})

                elif data == "run_test_otp":
                    # টেস্ট ওটিপি সিমুলেশন ট্রিগার (গ্রুপে প্রিমিয়াম ফরম্যাটে স্যাম্পল ওটিপি পাঠাবে)
                    self.edit_telegram_message(chat_id, message_id, "🚀 টেস্ট ওটিপি সিমুলেশন শুরু হয়েছে... গ্রুপটি চেক করুন!", {"inline_keyboard": [[{"text": "🔙 Back", "callback_data": "admin_edit_services"}]]})
                    
                    # প্রিমিয়াম স্টাইলে টেস্ট মেসেজ পাঠানো
                    test_sample = (
                        f"🔥 **[TEST SIMULATION] New OTP Received**\n"
                        f"━━━━━━━━━━━━━━━━━━━\n"
                        f"📱 **Number:** `+1 (939) 456-7890`\n"
                        f"🌐 **Service:** Facebook Verification\n"
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
                "token": SMS_API_TOKEN,
                "filternum": phone_number,
                "records": 1
            })
            url = f"{SMS_API_URL}?{params}"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                if res_data.get("status") == "success" and res_data.get("data"):
                    latest_msg = res_data["data"][0].get("message", "No message found")
                    return latest_msg
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
        return {
            "inline_keyboard": [
                [{"text": "📘 Facebook", "callback_data": "service_Facebook"}],
                [{"text": "📷 Instagram", "callback_data": "service_Instagram"}],
                [{"text": "🔙 Back", "callback_data": "back_home"}]
            ]
        }

    def admin_keyboard(self):
        return {
            "inline_keyboard": [
                [{"text": "✏️ Edit Services (FB/Insta)", "callback_data": "admin_edit_services"}]
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
        self.wfile.write(b"Bot is running with Test Simulation!")
