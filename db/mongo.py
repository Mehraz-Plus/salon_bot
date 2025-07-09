from pymongo import MongoClient, ReturnDocument
import sys
import os

# اضافه کردن مسیر فولدر config به sys.path
config_path = os.path.join(os.path.dirname(__file__), '..', 'config')
sys.path.append(config_path)
from bson import ObjectId
from datetime import datetime, timezone
import settings

class MongoManager:
    def __init__(self):
        self.client = MongoClient(settings.MONGO_URI)
        self.db = self.client[settings.DB_NAME]
        

        self.users = self.db.users
        self.products = self.db.products
        self.invoices = self.db.invoices
        self.withdrawals = self.db.withdrawals


    #  کاربران
    def add_user(self,id ,name, mobile, role="stylist"):
        user = {
            "id" : id,
            "name": name,
            "mobile": mobile,
            "role": role,
            "balance": 0,
            "telegram_id": None,
        }
        return self.users.insert_one(user).inserted_id

    def update_user_telegram_id(self, user_id, telegram_id):
        return self.users.find_one_and_update(
            {"id": user_id},
            {"$set": {"telegram_id": telegram_id}},
            return_document=ReturnDocument.AFTER,
        )

    def get_user_by_telegram(self, telegram_id):
        return self.users.find_one({"telegram_id": telegram_id})
    def get_user_by_telegram2(self, telegram_id):
        return self.users.find_one({"id": telegram_id})

    def get_user_by_mobile(self, mobile):
        return self.users.find_one({"mobile": mobile})

    #  محصولات
    def add_product(self, name, unit, total_weight, price_per_gram):
        product = {
            "name": name,
            "unit": unit,
            "total_weight": total_weight,
            "price_per_gram": price_per_gram,
            "created_at": datetime.now(timezone.utc),
        }
        return self.products.insert_one(product).inserted_id

    def update_product_stock(self, product_id, amount_used):
        return self.products.find_one_and_update(
            {"id": product_id},
            {"$inc": {"total_weight": -amount_used}},
            return_document=ReturnDocument.AFTER,
        )

    def get_product(self, product_id):
        return self.products.find_one({"name": product_id})

    def list_products(self):
        return list(self.products.find())

    # 📋 فاکتور
    def create_invoice(self, stylist_id, customer_name, items):
        """
        items: list of dicts
        [
            {"product_id": <ObjectId>, "amount": 20, "unit_price": 2.5, "total_price": 50},
            ...
        ]
        """
        total = sum(item["total_price"] for item in items)
        stylist_profit = round(total * 0.4, 2)
        owner_profit = round(total * 0.6, 2)

        invoice = {
            "id": stylist_id,
            "customer_name": customer_name,
            "date": datetime.now(timezone.utc),
            "items": items,
            "total": total,
            "profit_split": {
                "stylist": stylist_profit,
                "owner": owner_profit,
            },
        }

        self.invoices.insert_one(invoice)

        # آپدیت موجودی هر محصول
        for item in items:
            self.update_product_stock(item["product_id"], item["amount"])

        # افزایش موجودی آرایشگر
        self.users.update_one(
            {"_id": ObjectId(stylist_id)},
            {"$inc": {"balance": stylist_profit}}
        )

        return invoice

    # 📋 تسویه
    def withdraw(self, stylist_id, note=""):
        user = self.users.find_one({"_id": ObjectId(stylist_id)})
        if not user:
            return None
        amount = user.get("balance", 0)
        if amount <= 0:
            return None

        withdrawal = {
            "stylist_id": ObjectId(stylist_id),
            "amount": amount,
            "date": datetime.now(timezone.utc),
            "note": note,
        }

        self.withdrawals.insert_one(withdrawal)

        # صفر کردن موجودی
        self.users.update_one(
            {"_id": ObjectId(stylist_id)},
            {"$set": {"balance": 0}}
        )

        return withdrawal
# ##
    def get_profit_report(self, from_date, to_date):
        """
        گزارش سود کلی سالن بین دو تاریخ
        """
        pipeline = [
            {
                "$match": {
                    "date": {
                        "$gte": from_date,
                        "$lte": to_date
                    }
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total": {"$sum": "$total"},
                    "total_owner": {"$sum": "$profit_split.owner"},
                    "total_stylist": {"$sum": "$profit_split.stylist"}
                }
            }
        ]

        result = list(self.invoices.aggregate(pipeline))
        if result:
            return result[0]
        return {
            "total": 0,
            "total_owner": 0,
            "total_stylist": 0
        }
    

    def get_stylist_report(self, stylist_id, from_date, to_date):
        """
        گزارش درآمد آرایشگر بین دو تاریخ
        """
        pipeline = [
            {
                "$match": {
                    "stylist_id": ObjectId(stylist_id),
                    "date": {
                        "$gte": from_date,
                        "$lte": to_date
                    }
                }
            },
            {
                "$group": {
                    "_id": "$stylist_id",
                    "total": {"$sum": "$total"},
                    "stylist_profit": {"$sum": "$profit_split.stylist"}
                }
            }
        ]

        result = list(self.invoices.aggregate(pipeline))
        if result:
            return result[0]
        return {
            "total": 0,
            "stylist_profit": 0
        }

    def delete_stylist(self, name):
        """
        حذف یک آرایشگر بر اساس نام
        """
        result = self.users.delete_many({
            "name": name,
            "role": "stylist"
        })
        if result.deleted_count > 0:
            print(f"{result.deleted_count} آرایشگر با نام {name} حذف شد.")
        
        


mongo_manager = MongoManager()