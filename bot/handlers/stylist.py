import sys
import os

path = os.path.join(os.path.dirname(__file__), '..', 'db')
sys.path.append(path)
import jdatetime
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
    products = mongo.mongo_manager.list_products2()
    PRODUCTS_PER_PAGE = 5  # تعداد محصولات در هر صفحه
    total_products = len(products)
    total_pages = (total_products + PRODUCTS_PER_PAGE - 1) // PRODUCTS_PER_PAGE
    async with bot.conversation(event.sender_id) as conv:
        page = 1
        while True:
            start_index = (page - 1) * PRODUCTS_PER_PAGE
            end_index = start_index + PRODUCTS_PER_PAGE
            paginated_products = products[start_index:end_index]
            
            buttons = []
            for product in paginated_products:
                none_zero = product["total_weight"]
                none_zero = int(none_zero)
                if none_zero > 0:
                    buttons.append([Button.inline(product["name"], product["name"].encode())])
            
            # افزودن دکمه‌های صفحه‌بندی
            paginator = paginate(
                msg="",
                current_page=page,
                total_pages=total_pages,
                data=f"products{PRODUCTS_PER_PAGE}",
                after=[[Button.inline("اتمام آرایش", b"end")]]
            )
            if paginator:
                buttons.extend(paginator)
            
            await conv.send_message("محصولی که استفاده کردی را انتخاب کن:", buttons=buttons)
            
            response = await conv.get_response()
            if response.data == b"end":
                break


            product_name = response.data.decode()
            product = mongo.mongo_manager.get_product(product_name)
            if not product:
                await conv.send_message(" محصول پیدا نشد.")
                return

            await conv.send_message(" چند گرم استفاده کردی؟")
            amount = float((await conv.get_response()).text.strip())

            

            # update in db
            return_method = mongo.mongo_manager.reduce_product_stock(product_name, amount)
            await event.reply(return_method)
            

        # محاسبه
            unit_price = product["price_per_gram"]
            unit_price_count += unit_price
            total_price += round(unit_price * amount, 2)
            product_lst.append(product["name"])

        await conv.send_message(" نام مشتری:")
        customer_name = (await conv.get_response()).text.strip()

        await conv.send_message("پرداخت نهایی مشتری: ")
        customer_price = float((await conv.get_response()).text.strip())

        total_price = customer_price - total_price
        items = [{
            "product_name": product_lst,
            "unit_price": unit_price,
            "total_price": total_price
        }]
        sender = await event.get_sender()
        sender_id = sender.id
            # ثبت در دیتابیس
        invoice = mongo.mongo_manager.create_invoice(
            stylist_id=mongo.mongo_manager.get_user_by_telegram2(sender_id)["name"],
            customer_name=customer_name,
            customer_price=customer_price,
            items=items
        )

        await conv.send_message(f"✅ ثبت شد. کل مبلغ: {invoice['total']}")

# 
async def stylist_report(event, bot):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message(" تاریخ اولیه را وارد کنید. مثال 1402/01/01 ")
        from_date_str = (await conv.get_response()).text.strip()

        await conv.send_message(" تاریخ ثانویه را وارد کنید. مثال 1402/01/01 ")
        to_date_str = (await conv.get_response()).text.strip()
        from_date_jalali = jdatetime.datetime.strptime(from_date_str, "%Y/%m/%d")
        to_date_jalali = jdatetime.datetime.strptime(to_date_str, "%Y/%m/%d")
        
        from_date = from_date_jalali.togregorian()
        to_date = to_date_jalali.togregorian()
        
        # اطمینان از اینکه تاریخ‌ها در منطقه زمانی UTC هستند
        from_date = from_date.replace(tzinfo=timezone.utc)
        to_date = to_date.replace(tzinfo=timezone.utc)

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



def navigate(msg, current_page=1, total_pages=1, data=None, delimiter='-'):
    current_page = int(current_page)
    total_pages = int(total_pages)
    if data:
        data += delimiter
        keyboard = []
        if total_pages > current_page + 1:
            keyboard.append(Button.inline('last', str.encode(data + str(total_pages))))
        if total_pages > current_page:
            keyboard.append(Button.inline('next', str.encode(data + str(current_page + 1))))
        if total_pages > 1:
            keyboard.append(Button.inline(str(current_page) + ' from ' + str(total_pages)))
        if current_page > 1:
            keyboard.append(Button.inline('previous', str.encode(data + str(current_page - 1))))
        if current_page > 2:
            keyboard.append(Button.inline('first', str.encode(data + '1')))
        return keyboard
    else:
        return None

def paginate(msg, current_page=1, total_pages=1, data=None, delimiter='-',
             before=None, after=None):
    if data:
        paginator = navigate(msg, current_page, total_pages, data, delimiter)
        if before or after:
            paginator = [paginator]
        if before:
            paginator = before + paginator
        if after:
            paginator.append(after)
        return paginator
    else:
        return None