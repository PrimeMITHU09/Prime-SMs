from http.server import BaseHTTPRequestHandler
import json
import urllib.request

TOKEN = "8883835008:AAEjm5zjdMuFEB8E19PdKGTGS7GSu6gjpb4"
OTP_GROUP_ID = "-1003931415470"
OTP_GROUP_LINK = "https://t.me/c/3931415470/1"

# ডাইনামিক ডেটা স্টোরেজ (সার্ভিস অনুযায়ী কান্ট্রি এবং নম্বর জমা থাকবে)
# স্ট্রাকচার: { "Facebook": { "Bangladesh 🇧🇩": ["017...", "018..."] }, "Instagram": {} }
database = {
    "Facebook": {},
    "Instagram": {}
}

# অ্যাডমিন অ্যাড করার স্টেট ট্র্যাক করার জন্য
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

                # অ্যাডমিন ইনপুট হ্যান্ডলিং (যদি অ্যাডমিন কান্ট্রি বা নম্বর লিখে পাঠায়)
                if user_id in admin_sessions:
                    state_data = admin_sessions[user_id]
                    step = state_data.get("step")
                    service = state_data.get("service")

                    if step == "waiting_country":
                        country_name = text.strip()
                        state_data["country"] = country_name
                        state_data["step"] = "waiting_number"
                        admin_sessions[user_id] = state_data
                        self.send_telegram_message(chat_id, f"✅ কান্ট্রি যুক্ত হয়েছে: {country_name}\n\nএবার এই কান্ট্রির **নম্বরগুলো** দিন (একাধিক নম্বর হলে কমা দিয়ে অথবা এক লাইনে একটি করে দিতে পারেন):")
                        self.send_response(200)
                        self.end_headers()
                        return

                    elif step == "waiting_number":
                        country = state_data.get("country")
                        # নম্বরগুলো স্প্লিট করে লিস্ট বানানো
                        numbers = [n.strip() for n in text.replace(",", "\n").split("\n") if n.strip()]
                        
                        if service not in database:
                            database[service] = {}
                        if country not in database[service]:
                            database[service][country] = []
                        
                        database[service][country].extend(numbers)
                        del admin_sessions[user_id] # সেশন ক্লিয়ার

                        self.send_telegram_message(chat_id, f"🎉 সফলভাবে {service} এর জন্য **{country}** এ {len(numbers)}টি নম্বর যুক্ত করা হয়েছে!\n\nএখন ইউজাররা 'Get Number' থেকে এটি দেখতে পাবে।", self.admin_keyboard())
                        self.send_response(200)
                        self.end_headers()
                        return

                if text.startswith("/start"):
                    self.send_telegram_message(chat_id, f"স্বাগতম {first_name}! নিচের মেনু থেকে আপনার প্রয়োজনীয় অপশনটি সিলেক্ট করুন:", self.main_menu())

                elif text.startswith("/admin") or text.startswith("/admin_pannel"):
                    self.send_telegram_message(chat_id, "🔧 **Admin Panel**\nনতুন সার্ভিস, কান্ট্রি বা নম্বর যোগ করতে নিচে ক্লিক করুন:", self.admin_keyboard())

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
                        self.edit_telegram_message(chat_id, message_id, f"⚠️ **{service}** এ বর্তমানে কোনো দেশ বা নম্বর নেই। অ্যাডমিন প্যানেل থেকে কান্ট্রি ও নম্বর যোগ করুন।", reply_markup)
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
                        # প্রথম নম্বরটি ইউজারকে দিয়ে লিস্ট থেকে রিমুভ করে দেওয়া (যাতে রিপিট না হয়)
                        assigned_num = available_nums.pop(0)
                        
                        text = f"✅ আপনার নম্বর সফলভাবে বরাদ্দ করা হয়েছে:\n\n📱 **{assigned_num}**\nসার্ভিস: {service} ({country})\n\nওটিপি আসার জন্য অপেক্ষা করুন..."
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
                            [{"text": "🔙 Back", "callback_data": "back_home"}]
                        ]
                    }
                    self.edit_telegram_message(chat_id, message_id, "🛠️ অ্যাডমিন কন্ট্রোল প্যানেল: কোন সার্ভিসে কান্ট্রি ও নম্বর যোগ করতে চান?", keyboard)

                elif data.startswith("add_country_"):
                    service = data.split("_")[2]
                    admin_sessions[user_id] = {"service": service, "step": "waiting_country"}
                    self.edit_telegram_message(chat_id, message_id, f"📝 আপনি **{service}** সিলেক্ট করেছেন।\n\nদয়া করে এখন নতুন **দেশের নাম ও ফ্ল্যাগ** (যেমন: `Bangladesh 🇧🇩`) লিখে চ্যাটে পাঠান:", {"inline_keyboard": [[{"text": "❌ Cancel", "callback_data": "admin_edit_services"}]]})

            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        except Exception as e:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")

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
        self.wfile.write(b"Bot is running!")
