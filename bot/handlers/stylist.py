import sys
import os

path = os.path.join(os.path.dirname(__file__), '..', 'db')
sys.path.append(path)

import mongo
from telethon import events, Button
from datetime import datetime, timezone


async def handle_callback(event, data, bot):
    if data == "use_product":
        await use_product(event, bot)
    elif data == "stylist_report":
        await stylist_report(event, bot)
    elif data == "list_products":
        await list_products(event)
    await event.answer()

# 
async def use_product(event, bot):
    product_lst = []
    total_price = 0
    unit_price_count = 0
    async with bot.conversation(event.sender_id) as conv:
        while True:
            buttons = [
                [Button.inline("اتمام آرایش", b"end")],
                ]
            await conv.send_message(" نام محصولی که استفاده کردی:", buttons=buttons)
            response = await conv.get_response()
            if response.data == b"end":
                break


            product_name = (await conv.get_response()).text.strip()
            product = mongo.mongo_manager.get_product(product_name)
            if not product:
                await conv.send_message(" محصول پیدا نشد.")
                return

            await conv.send_message(" چند گرم استفاده کردی؟")
            amount = float((await conv.get_response()).text.strip())

            await conv.send_message(" نام مشتری:")
            customer_name = (await conv.get_response()).text.strip()
            

            # update in db
            return_method = mongo.mongo_manager.reduce_product_stock(product_name, amount)
            await event.reply(return_method)
            

        # محاسبه
            unit_price = product["price_per_gram"]
            unit_price_count += unit_price
            total_price += round(unit_price * amount, 2)
            product_lst.append(product["name"])



        items = [{
            "product_name": product_lst,
            "amount": amount,
            "unit_price": unit_price,
            "total_price": total_price
        }]
        sender = await event.get_sender()
        sender_id = sender.id
            # ثبت در دیتابیس
        invoice = mongo.mongo_manager.create_invoice(
            stylist_id=mongo.mongo_manager.get_user_by_telegram2(sender_id)["name"],
            customer_name=customer_name,
            items=items
        )

        await conv.send_message(f"✅ ثبت شد. کل مبلغ: {invoice['total']}")

# 
async def stylist_report(event, bot):
    from_date = datetime(1970, 1, 1)
    to_date = datetime.now(timezone.utc)

    stylist = mongo.mongo_manager.get_user_by_telegram(event.sender_id)
    report = mongo.mongo_manager.get_stylist_report(stylist["name"], from_date, to_date)
    if not report:
        await event.respond(" گزارشی برای شما یافت نشد.")
        return

    await event.respond(
        f" گزارش شما:\n"
        f"کل درآمد: {report['total']}\n"
        f"سهم شما: {report['stylist_profit']}"
    )
# 

async def list_products(event):
    products = mongo.mongo_manager.list_products()
    if not products:
        await event.respond(" محصولی ثبت نشده.")
        return

    text = " محصولات:\n"
    for p in products:
        text += f"- {p['name']} | موجودی: {p['total_weight']} {p['unit']}\n"
    await event.respond(text)