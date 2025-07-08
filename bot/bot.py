import sys
import os

# اضافه کردن مسیر فولدر config به sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'config'))

# حالا می‌توانید ماژول settings را ایمپورت کنید
from config import settings
from telethon import TelegramClient, events
from db import mongo
from bot.handlers import owner, stylist

api_id = settings.API_ID
api_hash = settings.API_HASH
bot_token = settings.BOT_TOKEN

bot = TelegramClient('kandipoor', api_id, api_hash).start(bot_token=bot_token)


def is_owner(user_id):
    return user_id == settings.ADMIN_ID


@bot.on(events.NewMessage(pattern='/start', incoming=True))
async def main_handler(event):
    sender = await event.get_sender()
    sender_id = sender.id
    print(sender_id)
    

    if is_owner(sender_id):
        await event.reply("سلام مدیر ! آماده‌ی مدیریت سالن هستید.")
        
    else:
        user = mongo.get_user_by_telegram(sender_id)
        if user:
            await event.reply(f"سلام {user['name']}! خوش اومدی. آماده‌ای برای ثبت کارهات؟")
        else:
            await event.reply("شما در سیستم ثبت نشده‌اید. لطفاً با مدیر تماس بگیرید.")
    return



if __name__ == "__main__":
    
    bot.run_until_disconnected()
