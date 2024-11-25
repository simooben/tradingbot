import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import asyncio
import pandas as pd
import pandas_ta as ta

# معلومات API
COINMARKETCAP_API_KEY = "6350493d-9c72-4855-b36e-77ea8435fd68"
COINMARKETCAP_API_URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
TELEGRAM_BOT_TOKEN = "7942288166:AAHwmF51b3srRJo3KD8m3fV0C7pvHaJODUA"

# قائمة لتتبع العملات التي تم إرسالها بالفعل
sent_coins = set()

# قائمة لتتبع العملات التي وصلت إلى الهدف الأخير
target_reached_coins = set()

# قائمة لتخزين معرفات المستخدمين
user_chat_ids = set()

# دالة للحصول على بيانات العملات المشفرة
def get_coin_data():
    headers = {
        'X-CMC_PRO_API_KEY': COINMARKETCAP_API_KEY,
        'Accept': 'application/json'
    }

    params = {
        'start': '1',
        'limit': '100',  # الحصول على أول 100 عملة مشفرة
        'convert': 'USD'
    }

    response = requests.get(COINMARKETCAP_API_URL, headers=headers, params=params)
    
    if response.status_code == 200:
        data = response.json()
        return data['data']
    else:
        return None

# دالة لتحليل البيانات وإرسال الإشعارات
async def analyze_and_notify(context: ContextTypes.DEFAULT_TYPE):
    coins = get_coin_data()
    
    if coins:
        for coin in coins:
            name = coin['name']
            symbol = coin['symbol']
            price = coin['quote']['USD']['price']
            percent_change_24h = coin['quote']['USD']['percent_change_24h']
            
            # حساب المؤشرات الفنية
            df = pd.DataFrame(coins)
            df['price'] = df['quote'].apply(lambda x: x['USD']['price'])
            df['rsi'] = ta.rsi(df['price'], length=14)
            df['macd'] = ta.macd(df['price'])['MACD_12_26_9']
            
            # تعيين سعر الدخول والهدف الأخير خارج الشروط
            entry_price = price
            target_price = entry_price * 1.05  # الهدف الأخير
            
            # منطق لتحديد العملات التي قد ترتفع في الـ 24 ساعة القادمة بنسبة 10% على الأقل
            if symbol not in sent_coins and percent_change_24h > 10:
                message = (
                    f"🪩BUY {name} / USDT\n"
                    f"سبوت متوسطة 🪩\n\n"
                    f"🔑 ENTRY {entry_price:.6f}\n"
                    f"النسبة المئوية للزيادة المتوقعة: {percent_change_24h:.2f}%\n"
                    f"TARGETS:\n"
                    f"➡️{entry_price * 1.01:.6f}✔️\n"
                    f"➡️{entry_price * 1.02:.6f}✔️✔️\n"
                    f"➡️{entry_price * 1.03:.6f}✔️✔️✔️\n"
                    f"➡️{entry_price * 1.04:.6f}✔️✔️✔️✔️\n"
                    f"➡️{target_price:.6f}✔️✔️✔️✔️✔️\n"
                    f"Stop ❌ {entry_price * 0.95:.6f} اغلاق شمعة 4 ساعات\n"
                )
                if percent_change_24h >= 20:
                    message += "💥 عملة انفجارية 💥\n"
                
                # إرسال الرسالة إلى جميع المستخدمين
                for chat_id in user_chat_ids:
                    await context.bot.send_message(chat_id=chat_id, text=message)
                
                sent_coins.add(symbol)
                await asyncio.sleep(10)  # الانتظار 10 ثوانٍ بين الرسائل

            # تحقق مما إذا كانت العملة قد وصلت إلى الهدف الأخير
            if symbol in sent_coins and symbol not in target_reached_coins and price >= target_price:
                percent_gain = ((price - entry_price) / entry_price) * 100
                confirmation_message = (
                    f"✅ {name} / USDT وصلت إلى الهدف الأخير!\n"
                    f"سعر الدخول: {entry_price:.6f}\n"
                    f"السعر الحالي: {price:.6f}\n"
                    f"النسبة المئوية للزيادة: {percent_gain:.2f}%\n"
                )
                for chat_id in user_chat_ids:
                    await context.bot.send_message(chat_id=chat_id, text=confirmation_message)
                
                target_reached_coins.add(symbol)

# دالة لبدء البوت وتسجيل معرف الدردشة
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_chat_ids.add(chat_id)  # إضافة معرف المستخدم إلى القائمة
    await update.message.reply_text("🎯 مرحبًا! البوت الآن يعمل وستتلقى إشعارات.")

# إعداد التطبيق وربط الوظائف
def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # إضافة معالج الأمر /start
    application.add_handler(CommandHandler("start", start))

    # إعداد وظيفة متكررة لإرسال الإشعارات
    job_queue = application.job_queue
    job_queue.run_repeating(analyze_and_notify, interval=60, first=0)

    # بدء البوت
    application.run_polling()

if __name__ == "__main__":
    main()