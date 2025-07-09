import sys
import os

path = os.path.join(os.path.dirname(__file__), '..', 'db')
sys.path.append(path)

import mongo
from telethon import events, Button
from datetime import datetime, timezone


async def handle_callback(event, data, bot):
    if data == "add_stylist":
        await add_stylist(event, bot)
    elif data == "add_product":
        await add_product(event, bot)
    elif data == "report_profit":
        await report_profit(event)
    elif data == "list_products":
        await list_products(event)
    elif data == "list_stylists":
        await list_stylists(event)
    
    elif data == "delete_stylists":
        await delete_stylists(event, bot)
    
    await event.answer()


async def add_stylist(event, bot):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message(" آیدی تلگرام آرایشگر را بدون @ وارد کنید: ")
        telegram_id = (await conv.get_response()).text.strip()

        await conv.send_message(" نام آرایشگر را وارد کنید:")
        name = (await conv.get_response()).text.strip()

        await conv.send_message(" شماره موبایل آرایشگر را وارد کنید:")
        mobile = (await conv.get_response()).text.strip()

        mongo.mongo_manager.add_user(telegram_id, name, mobile)
        await conv.send_message(f"✅ آرایشگر {name} با شماره {mobile} اضافه شد.")

 
async def add_product(event, bot):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message(" نام محصول را وارد کنید:")
        name = (await conv.get_response()).text.strip()

        await conv.send_message(" واحد محصول (مثل گرم) را وارد کنید:")
        unit = (await conv.get_response()).text.strip()

        await conv.send_message(" مقدار اولیه محصول را وارد کنید:")
        weight = float((await conv.get_response()).text.strip())

        await conv.send_message(" قیمت هر واحد را وارد کنید:")
        price = float((await conv.get_response()).text.strip())

        mongo.mongo_manager.add_product(name, unit, weight, price)
        await conv.send_message(f"✅ محصول {name} ثبت شد.")

###
async def report_profit(event):
    from_date = datetime(1970, 1, 1)
    to_date = datetime.now(timezone.utc)

    report = mongo.mongo_manager.get_profit_report(from_date, to_date)
    if not report:
        await event.respond(" هیچ درآمدی ثبت نشده.")
        return

    await event.respond(
        f" گزارش سود:\n"
        f"کل: {report['total']}\n"
        f"سهم سالن: {report['total_owner']}\n"
        f"سهم آرایشگرها: {report['total_stylist']}"
    )

# 
async def list_products(event):
    products = mongo.mongo_manager.list_products()
    if not products:
        await event.respond(" محصولی ثبت نشده.")
        return

    text = " محصولات:\n"
    for p in products:
        text += f"- {p['name']} | موجودی: {p['total_weight']} {p['unit']} | قیمت: {p['price_per_gram']} / واحد\n"
    await event.respond(text)

# 
async def list_stylists(event):
    users = mongo.mongo_manager.users.find({"role": "stylist"})
    text = " آرایشگرها:\n"
    for u in users:
        balance = u.get("balance", 0)
        text += f"- {u['name']} |  {u['mobile']} |  موجودی: {balance}\n"
    await event.respond(text)


async def delete_stylists(event, bot):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message(" نام آرایشگر را وارد کنید:")
        name = (await conv.get_response()).text.strip()
        mongo.mongo_manager.delete_stylist(name)
        await event.reply(f"آرایشگر {name} حذف شد")