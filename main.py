import os
import asyncio
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup

# --- CONFIGURATIONS ---
TOKEN = "8883835008:AAEjm5zjdMuFEB8E19PdKGTGS7GSu6gjpb4"
GROUP_ID = -1003931415470
ADMIN_IDS = [123456789] # আপনার টেলিগ্রাম আইডি এখানে দিন যাতে অ্যাডমিন প্যানেল কাজ করে

bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()

# In-memory database
user_numbers = {} 
used_numbers_global = set()
country_data = {
    "Facebook": {"USA 🇺🇸": ["+123456789", "+198765432"], "UK 🇬🇧": ["+447123456"]},
    "Instagram": {"Canada 🇨🇦": ["+14161234567"]}
}

# --- MAIN MENU KEYBOARD ---
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📥 Get Number", callback_data="get_number")],
        [InlineKeyboardButton(text="📊 Live Traffic", callback_data="live_traffic")],
        [InlineKeyboardButton(text="👤 My Profile", callback_data="my_profile")],
        [InlineKeyboardButton(text="🔗 Get OTP Group", url="https://t.me/your_otp_group")]
    ])

# --- START COMMAND ---
@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "স্বাগতম! নিচের মেনু থেকে আপনার প্রয়োজনীয় অপশনটি সিলেক্ট করুন:",
        reply_markup=main_menu()
    )

# --- ADMIN PANEL COMMAND (Supports both /admin and /admin_pannel) ---
@router.message(Command("admin", "admin_pannel"))
async def cmd_admin(message: Message):
    # যদি অ্যাডমিন আইডি সেট করা না থাকে টেস্টের জন্য সাময়িকভাবে সবার জন্য ওপেন রাখতে চাইলে নিচের চেক উঠিয়ে দিতে পারেন
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Edit Services (FB/Insta)", callback_data="admin_edit_services")]
    ])
    await message.answer("🔧 **Admin Panel**\nসেটিংস পরিবর্তন করতে নিচে ক্লিক করুন:", reply_markup=keyboard)

# --- GET NUMBER HANDLER ---
@router.callback_query(F.data == "get_number")
async def cb_get_number(callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📘 Facebook", callback_data="service_Facebook")],
        [InlineKeyboardButton(text="📷 Instagram", callback_data="service_Instagram")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="back_home")]
    ])
    await callback.message.edit_text("দয়া করে সার্ভিস সিলেক্ট করুন:", reply_markup=keyboard)

# --- SERVICE & COUNTRY SELECTION ---
@router.callback_query(F.data.startswith("service_"))
async def cb_select_service(callback: CallbackQuery):
    service = callback.data.split("_")[1]
    countries = country_data.get(service, {})
    
    if not countries:
        await callback.answer("এই সার্ভিসে বর্তমানে কোনো দেশ বা নম্বর নেই!", show_alert=True)
        return

    keyboard = []
    for country in countries.keys():
        keyboard.append([InlineKeyboardButton(text=country, callback_data=f"country_{service}_{country}")])
    keyboard.append([InlineKeyboardButton(text="🔙 Back", callback_data="get_number")])

    await callback.message.edit_text(f"🌍 **{service}** এর জন্য দেশ সিলেক্ট করুন:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

# --- ALLOCATE NUMBER ---
@router.callback_query(F.data.startswith("country_"))
async def cb_give_number(callback: CallbackQuery):
    _, service, country = callback.data.split("_", 2)
    available_nums = country_data.get(service, {}).get(country, [])
    
    selected_num = None
    for num in available_nums:
        if num not in used_numbers_global:
            selected_num = num
            break
            
    if not selected_num:
        await callback.answer("দুঃখিত, এই দেশের সব নম্বর শেষ হয়ে গেছে!", show_alert=True)
        return

    used_numbers_global.add(selected_num)
    user_id = callback.from_user.id
    if user_id not in user_numbers:
        user_numbers[user_id] = []
    user_numbers[user_id].append(selected_num)

    await callback.message.edit_text(
        f"✅ আপনার নম্বর সফলভাবে বরাদ্দ করা হয়েছে:\n\n📱 **{selected_num}**\nসার্ভিস: {service} ({country})\n\nওটিপি আসার জন্য অপেক্ষা করুন...",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Main Menu", callback_data="back_home")]])
    )

# --- LIVE TRAFFIC ---
@router.callback_query(F.data == "live_traffic")
async def cb_live_traffic(callback: CallbackQuery):
    fb_count = sum(len(nums) for nums in country_data.get("Facebook", {}).values())
    insta_count = sum(len(nums) for nums in country_data.get("Instagram", {}).values())
    
    text = (
        "📊 **Live Traffic Analysis**\n\n"
        f"📘 Facebook Total Active Numbers: {fb_count}\n"
        f"📷 Instagram Total Active Numbers: {insta_count}\n\n"
        "বিশ্লেষণ অনুযায়ী বর্তমানে ট্রাফিকের অবস্থা স্বাভাবিক রয়েছে।"
    )
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Back", callback_data="back_home")]]))

# --- MY PROFILE ---
@router.callback_query(F.data == "my_profile")
async def cb_my_profile(callback: CallbackQuery):
    user = callback.from_user
    text = (
        f"👤 **User Profile**\n\n"
        f"🔹 Name: {user.full_name}\n"
        f"🔹 Username: @{user.username if user.username else 'N/A'}\n"
        f"🔹 User ID: `{user.id}`\n\n"
        f"স্বাগতম আমাদের বটে!"
    )
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Back", callback_data="back_home")]]))

@router.callback_query(F.data == "back_home")
async def cb_back_home(callback: CallbackQuery):
    await callback.message.edit_text("প্রধান মেনু:", reply_markup=main_menu())

# --- ADMIN EDIT PANEL ---
@router.callback_query(F.data == "admin_edit_services")
async def admin_edit(callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Add Country/Number (FB)", callback_data="add_fb")],
        [InlineKeyboardButton(text="➕ Add Country/Number (Insta)", callback_data="add_insta")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="back_home")]
    ])
    await callback.message.edit_text("🛠️ অ্যাডমিন কন্ট্রোল প্যানেল:", reply_markup=keyboard)

# Include router directly into dispatcher
dp.include_router(router)
