import logging
import re
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

# تنظیمات logging برای خطاها و اشکال‌زدایی
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# مسیر ذخیره‌سازی دیتابیس (یا فایل)
DATABASE_FILE = "user_data.json"

# تابع برای بارگذاری داده‌ها از فایل
def load_data():
    try:
        with open(DATABASE_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

# تابع برای ذخیره‌سازی داده‌ها در فایل
def save_data(data):
    with open(DATABASE_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

# پیام خوشامدگویی به کاربران جدید
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()

    # چک کردن اینکه آیا کاربر قبلاً در سیستم ثبت شده یا نه
    if user_id not in data:
        referrer_id = None
        if context.args and context.args[0].isdigit():
            referrer_id = context.args[0]
        data[user_id] = {
            "username": update.effective_user.username,
            "plan": None,
            "total_gb": 0,
            "used_gb": 0,
            "wallet": 0,
            "referrer": referrer_id,
            "invited": []
        }
        if referrer_id and referrer_id in data:
            data[referrer_id].setdefault("invited", []).append(user_id)
        save_data(data)

    keyboard = [
        [InlineKeyboardButton("💳 خرید اشتراک", callback_data="buy_plan")],
        [InlineKeyboardButton("🎁 دریافت موجودی رایگان", callback_data="freecredit")],
        [InlineKeyboardButton("📢 دعوت دوستان + کسب درآمد", callback_data="invite")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("سلام! خوش آمدید به ربات فیلترشکن! از منو زیر استفاده کنید:", reply_markup=reply_markup)

# هندلر خرید اشتراک
async def plan_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = load_data()
    user_id = str(query.from_user.id)
    user = data.get(user_id, None)

    if user is None:
        await query.answer("شما هنوز در سیستم ثبت‌نام نکردید.")
        return

    if query.data == "buy_plan":
        # فهرست قیمت‌ها
        plans = [
            ("20GB", 70000),
            ("30GB", 100000),
            ("40GB", 120000),
            ("50GB", 150000),
            ("100GB", 250000),
            ("200GB", 430000),
        ]
        keyboard = [
            [InlineKeyboardButton(f"{plan[0]} - {plan[1]} تومان", callback_data=f"buy_{plan[0]}")]
            for plan in plans
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("لطفاً یکی از پلن‌ها را انتخاب کنید:", reply_markup=reply_markup)

    elif query.data.startswith("buy_"):
        plan_size = query.data.split("_")[1]
        plan_prices = {
            "20GB": 70000,
            "30GB": 100000,
            "40GB": 120000,
            "50GB": 150000,
            "100GB": 250000,
            "200GB": 430000,
        }
        price = plan_prices.get(plan_size, 0)
        if user["wallet"] >= price:
            user["wallet"] -= price
            user["total_gb"] += int(plan_size.split("GB")[0])
            user["plan"] = f"{user['total_gb']}GB فعال"
            save_data(data)

            # پاداش به معرف اگر اولین خرید است
            if user.get("referrer"):
                ref_id = user["referrer"]
                if ref_id in data:
                    data[ref_id]["wallet"] += 3000
                    save_data(data)

            await query.edit_message_text(f"شما اشتراک {plan_size} خریداری کردید. حجم کل شما: {user['total_gb']}GB")

# هندلر دریافت موجودی رایگان
async def freecredit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    promo_text = (
        "🔰 فروش ویژه فیلترشکن 𝑽2𝑹𝑨𝒀𝑵𝑮\n\n"
        "تخفیف ویژه برای همکاران محترم\n\n"
        "✅ یکی از امن‌ترین و معروف‌ترین سرویس‌های وی‌پی‌ان 🏝\n"
        "✅ دارای آی‌پی ثابت و پینگ عالی 👌\n"
        "✅ مناسب همه برنامه‌ها 📱📱📱\n"
        "✅ سرعت بسیار بالا در دانلود و آپلود 🚀\n"
        "✅ دور زدن نت ملی 🔓\n"
        "✅ اتصال ۲۴ ساعته بدون قطعی 🔩\n"
        "✅ تضمین تا آخرین روز اشتراک 🔥\n"
        "✅ مناسب برای:\nاندروید 📱 | آیفون 📱 | ویندوز 💻\n\n"
        "💟 جهت خرید 👇👇\n"
        "لینک خرید شما: [Support Link]"
    )
    await update.message.reply_text(promo_text)

# هندلر دعوت دوستان
async def invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ref_link = f"https://t.me/GameVPNBot?start={update.message.from_user.id}"
    user_data = load_data().get(str(update.message.from_user.id), {})
    invited_count = len(user_data.get("invited", []))
    
    msg = (
        "با لینک زیر دوستاتو به ربات دعوت کن:\n\n"
        f"{ref_link}\n\n"
        f"تعداد افرادی که دعوت کردی: {invited_count} نفر\n"
        "با هر خرید از طرف اون‌ها، ۳,۰۰۰ تومان به کیف پولت اضافه می‌شه!"
    )
    await update.message.reply_text(msg)

# هندلر مشخصات اشتراک
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()
    message_text = update.message.text.strip()

    if not re.match(r"^(v2ray://|vmess://)", message_text):
        return  # اگر لینک صحیح نیست، پاسخی ندیم

    if user_id not in data:
        await update.message.reply_text("شما هنوز اشتراکی فعال ندارید.")
        return

    user = data[user_id]
    remaining = user["total_gb"] - user["used_gb"]
    status = "فعال" if user["total_gb"] > 0 else "غیرفعال"

    msg = (
        f"🔐 مشخصات اشتراک شما:\n\n"
        f"وضعیت اشتراک: {status}\n"
        f"حجم کل: {user['total_gb']} گیگابایت\n"
        f"مصرف‌شده: {user['used_gb']} گیگابایت\n"
        f"مانده: {remaining} گیگابایت\n"
        f"کیف پول: {user['wallet']} تومان"
    )
    await update.message.reply_text(msg)

    if remaining <= 1:
        warning_msg = "⚠️ هشدار: حجم باقی‌مانده شما ۱ گیگابایت یا کمتر است. لطفاً اشتراک خود را تمدید کنید."
        await update.message.reply_text(warning_msg)

# تابع اصلی که همه هندلرها رو متصل می‌کنه
def main():
    application = Application.builder().token("YOUR_BOT_API_KEY").build()

    # هندلرها
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(plan_selected))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(freecredit, pattern="freecredit"))
    application.add_handler(CallbackQueryHandler(invite, pattern="invite"))

    application.run_polling()

if __name__ == "__main__":
    main()
