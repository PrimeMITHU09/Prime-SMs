from http.server import BaseHTTPRequestHandler
import json
from main import bot, dp, router
import asyncio

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            update_data = json.loads(post_data.decode('utf-8'))
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.process_update(update_data))
        except Exception as e:
            print(f"Error: {e}")

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    async def process_update(data):
        from aiogram.types import Update
        update = Update.model_validate(data, context={"bot": bot})
        await dp.feed_update(bot, update)

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Telegram Bot is running on Vercel!")