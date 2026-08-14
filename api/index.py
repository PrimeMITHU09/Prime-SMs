from http.server import BaseHTTPRequestHandler
import json
import urllib.request

TOKEN = "8883835008:AAEjm5zjdMuFEB8E19PdKGTGS7GSu6gjpb4"

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

                if text.startswith("/start"):
                    reply_markup = {
                        "inline_keyboard": [
                            [{"text": "📥 Get Number", "callback_data": "get_number"}],
                            [{"text": "📊 Live Traffic", "callback_data": "live_traffic"}],
                            [{"text": "👤 My Profile", "callback_data": "my_profile"}],
                            [{"text": "🔗 Get OTP Group", "url": "https://t.me/your_otp_group"}]
                        ]
                    }
                    self.send_telegram_message(chat_id, f"স্বাগতম {first_name}! নিচের মেনু থেকে আপনার প্রয়োজনীয় অপশনটি সিলেক্ট করুন:", reply_markup)

                elif text.startswith("/admin") or text.startswith("/admin_pannel"):
                    reply_markup = {
                        "inline_keyboard": [
                            [{"text": "✏️ Edit Services (FB/Insta)", "callback_data": "admin_edit_services"}]
                        ]
                    }
                    self.send_telegram_message(chat_id, "🔧 **Admin Panel**\nসেটিংস পরিবর্তন করতে নিচে ক্লিক করুন:", reply_markup)

            elif "callback_query" in update:
                callback = update["callback_query"]
                chat_id = callback["message"]["chat"]["id"]
                message_id = callback["message"]["message_id"]
                data = callback["data"]
                user = callback.get("from", {})
                
                if data == "get_number":
                    reply_markup = {
                        "inline_keyboard": [
                            [{"text": "📘 Facebook", "callback_data": "service_Facebook"}],
                            [{"text": "📷 Instagram", "callback_data": "service_Instagram"}],
                            [{"text": "🔙 Back", "callback_data": "back_home"}]
                        ]
                    }
                    self.edit_telegram_message(chat_id, message_id, "দয়া করে সার্ভিস সিলেক্ট করুন:", reply_markup)

                elif data.startswith("service_"):
                    service = data.split("_")[1]
                    reply_markup = {
                        "inline_keyboard": [
                            [{"text": "USA 🇺🇸", "callback_data": f"country_{service}_USA"}],
                            [{"text": "🔙 Back", "callback_data": "get_number"}]
                        ]
                    }
                    self.edit_telegram_message(chat_id, message_id, f"🌍 **{service}** এর জন্য দেশ সিলেক্ট করুন:", reply_markup)

                elif data.startswith("country_"):
                    _, service, country = data.split("_", 2)
                    reply_markup = {
                        "inline_keyboard": [
                            [{"text": "🔙 Main Menu", "callback_data": "back_home"}]
                        ]
                    }
                    self.edit_telegram_message(chat_id, message_id, f"✅ আপনার নম্বর সফলভাবে বরাদ্দ করা হয়েছে:\n\n📱 **+1234567890**\nসার্ভিস: {service} ({country})\n\nওটিপি আসার জন্য অপেক্ষা করুন...", reply_markup)

                elif data == "live_traffic":
                    reply_markup = {
                        "inline_keyboard": [
                            [{"text": "🔙 Back", "callback_data": "back_home"}]
                        ]
                    }
                    text = "📊 **Live Traffic Analysis**\n\n📘 Facebook Total Active Numbers: 2\n📷 Instagram Total Active Numbers: 1\n\nঅবস্থা স্বাভাবিক রয়েছে।"
                    self.edit_telegram_message(chat_id, message_id, text, reply_markup)

                elif data == "my_profile":
                    reply_markup = {
                        "inline_keyboard": [
                            [{"text": "🔙 Back", "callback_data": "back_home"}]
                        ]
                    }
                    text = f"👤 **User Profile**\n\n🔹 Name: {user.get('first_name')}\n🔹 Username: @{user.get('username', 'N/A')}\n🔹 User ID: `{user.get('id')}`"
                    self.edit_telegram_message(chat_id, message_id, text, reply_markup)

                elif data == "back_home":
                    reply_markup = {
                        "inline_keyboard": [
                            [{"text": "📥 Get Number", "callback_data": "get_number"}],
                            [{"text": "📊 Live Traffic", "callback_data": "live_traffic"}],
                            [{"text": "👤 My Profile", "callback_data": "my_profile"}],
                            [{"text": "🔗 Get OTP Group", "url": "https://t.me/your_otp_group"}]
                        ]
                    }
                    self.edit_telegram_message(chat_id, message_id, "প্রধান মেনু:", reply_markup)

                elif data == "admin_edit_services":
                    reply_markup = {
                        "inline_keyboard": [
                            [{"text": "🔙 Back", "callback_data": "back_home"}]
                        ]
                    }
                    self.edit_telegram_message(chat_id, message_id, "🛠️ অ্যাডমিন কন্ট্রোল প্যানেল", reply_markup)

            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        except Exception as e:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")

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
