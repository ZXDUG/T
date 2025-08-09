import requests
import time
import asyncio
from threading import Thread
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

# مراحل الحوار
ENTER_NUMBER, ENTER_PASSWORD, ENTER_MEMBER1, ENTER_MEMBER2, CONFIRM = range(5)

user_data_global = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📱 أدخل رقم فودافون:")
    return ENTER_NUMBER

async def enter_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data_global['number'] = update.message.text.strip()
    await update.message.reply_text("🔑 أدخل كلمة مرور الحساب:")
    return ENTER_PASSWORD

async def enter_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data_global['password'] = update.message.text.strip()
    await update.message.reply_text("👤 member1:")
    return ENTER_MEMBER1

async def enter_member1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data_global['member1'] = update.message.text.strip()
    await update.message.reply_text("👤 member2:")
    return ENTER_MEMBER2

async def enter_member2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data_global['member2'] = update.message.text.strip()
    # الثوابت
    user_data_global['count'] = 60
    user_data_global['q1'] = 40
    user_data_global['q2'] = 10
    user_data_global['time'] = 3
    summary = (
        f"📋 ملخص البيانات:\n"
        f"رقم فودافون: {user_data_global['number']}\n"
        f"member1: {user_data_global['member1']}\n"
        f"member2: {user_data_global['member2']}\n"
        f"count: {user_data_global['count']}\n"
        f"q1: {user_data_global['q1']}\n"
        f"q2: {user_data_global['q2']}\n"
        f"time: {user_data_global['time']} ثانية\n\n"
        f"هل تريد بدء التنفيذ؟ (نعم/لا)"
    )
    await update.message.reply_text(summary)
    return CONFIRM

async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = update.message.text.strip().lower()
    if answer not in ['نعم', 'ن']:
        await update.message.reply_text("تم إلغاء العملية.")
        return ConversationHandler.END

    await update.message.reply_text("✅ جاري تنفيذ العملية ...")

    loop = asyncio.get_event_loop()
    Thread(target=run_quota_distribution, args=(update, context, loop)).start()
    return ConversationHandler.END

def run_quota_distribution(update, context, loop):
    number = user_data_global['number']
    password_owner = user_data_global['password']
    member1 = user_data_global['member1']
    member2 = user_data_global['member2']
    count = user_data_global['count']
    q1 = user_data_global['q1']
    q2 = user_data_global['q2']
    tt = user_data_global['time']

    session = requests.Session()

    def send_msg(text):
        asyncio.run_coroutine_threadsafe(update.message.reply_text(text), loop)

    # تسجيل الدخول - توكن
    try:
        login_url = "https://mobile.vodafone.com.eg/auth/realms/vf-realm/protocol/openid-connect/token"
        login_payload = {
            'grant_type': "password",
            'username': number,
            'password': password_owner,
            'client_secret': "95fd95fb-7489-4958-8ae6-d31a525cd20a",
            'client_id': "ana-vodafone-app"
        }
        login_headers = {
            'User-Agent': "okhttp/4.11.0",
            'Accept': "application/json, text/plain, */*",
            'Accept-Encoding': "gzip",
            'silentLogin': "false",
            'x-agent-operatingsystem': "13",
            'clientId': "AnaVodafoneAndroid",
            'Accept-Language': "ar",
            'x-agent-device': "Xiaomi 21061119AG",
            'x-agent-version': "2024.12.1",
            'x-agent-build': "946",
            'digitalId': "28RI9U7IINOOB"
        }
        response = session.post(login_url, data=login_payload, headers=login_headers)
        if response.status_code != 200:
            send_msg(f"❌ فشل تسجيل الدخول، الكود: {response.status_code}\nالرد: {response.text}")
            return
        tok = response.json().get('access_token')
        if not tok:
            send_msg(f"❌ لم يتم الحصول على التوكن:\n{response.text}")
            return
        send_msg("✅ تم تسجيل الدخول بنجاح!")
    except Exception as e:
        send_msg(f"❌ خطأ أثناء تسجيل الدخول:\n{e}")
        return

    head = {
        "api-host": "ProductOrderingManagement",
        "useCase": "MIProfile",
        "Authorization": f"Bearer {tok}",
        "api-version": "v2",
        "x-agent-operatingsystem": "9",
        "clientId": "AnaVodafoneAndroid",
        "x-agent-device": "Xiaomi Redmi 6A",
        "x-agent-version": "2024.3.2",
        "x-agent-build": "592",
        "msisdn": number,
        "Accept": "application/json",
        "Accept-Language": "ar",
        "Content-Type": "application/json; charset=UTF-8",
        "Connection": "Keep-Alive",
        "Accept-Encoding": "gzip",
        "User-Agent": "okhttp/4.11.0"
    }

    def thread1(quota):
        url = "https://web.vodafone.com.eg/services/dxl/cg/customerGroupAPI/customerGroup"
        data = {
            "category": [{"listHierarchyId": "TemplateID", "value": "47"}],
            "createdBy": {"value": "MobileApp"},
            "parts": {
                "characteristicsValue": {
                    "characteristicsValue": [{"characteristicName": "quotaDist1", "type": "percentage", "value": quota}]
                },
                "member": [
                    {"id": [{"schemeName": "MSISDN", "value": number}], "type": "Owner"},
                    {"id": [{"schemeName": "MSISDN", "value": member1}], "type": "Member"}
                ]
            },
            "type": "QuotaRedistribution"
        }
        try:
            response = session.post(url, headers=head, json=data)
            resp_json = response.json()
            send_msg(f"Thread1 - quota={quota} - Response: {resp_json}")
        except Exception as e:
            send_msg(f"Thread1 Error: {e}")

    def thread2(quota):
        url_wap = "https://web.vodafone.com.eg/services/dxl/cg/customerGroupAPI/customerGroup"
        headers = {
            "Host": "web.vodafone.com.eg",
            "Connection": "keep-alive",
            "Content-Length": "449",
            "sec-ch-ua": '"Not)A;Brand";v="99", "Google Chrome";v="127", "Chromium";v="127"',
            "msisdn": number,
            "Accept-Language": "AR",
            "sec-ch-ua-mobile": "?1",
            "Authorization": f"Bearer {tok}",
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36",
            "Content-Type": "application/json",
            "x-dtpc": "5$338036891_621h9vEAOVPAOTUAJDPRUQFKUMHFVECNFHNCFC-0e0",
            "Accept": "application/json",
            "clientId": "WebsiteConsumer",
            "sec-ch-ua-platform": '"Android"',
            "Origin": "https://web.vodafone.com.eg",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "Referer": "https://web.vodafone.com.eg/spa/familySharing/manageFamily",
            "Accept-Encoding": "gzip, deflate, br, zstd"
        }
        payload = {
            "category": [{"listHierarchyId": "TemplateID", "value": "47"}],
            "createdBy": {"value": "MobileApp"},
            "parts": {
                "characteristicsValue": {
                    "characteristicsValue": [{"characteristicName": "quotaDist1", "type": "percentage", "value": quota}]
                },
                "member": [
                    {"id": [{"schemeName": "MSISDN", "value": number}], "type": "Owner"},
                    {"id": [{"schemeName": "MSISDN", "value": member2}], "type": "Member"}
                ]
            },
            "type": "QuotaRedistribution"
        }
        try:
            response = session.post(url_wap, headers=headers, json=payload)
            resp_json = response.json()
            send_msg(f"Thread2 - quota={quota} - Response: {resp_json}")
        except Exception as e:
            send_msg(f"Thread2 Error: {e}")

    try:
        for cycle in range(count):
            send_msg(f"بدء الدورة {cycle+1} من {count} ...")
            for i in range(30):
                time.sleep(tt)
                thread1(q1)
                time.sleep(tt)
                thread2(q1)
                time.sleep(tt)

                t1 = Thread(target=thread1, args=(q2,))
                t2 = Thread(target=thread2, args=(q2,))
                t1.start()
                t2.start()
                t1.join()
                t2.join()

                time.sleep(3)
            send_msg(f"انتهت الدورة {cycle+1} من {count}")
    except Exception as e:
        send_msg(f"حدث خطأ في الاتصال بالإنترنت: {e}")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("تم إلغاء العملية.")
    return ConversationHandler.END

def main():
    TOKEN = "7253422977:AAGwMuEafu8YRGhe5FKKQccmMEdcQQqSEyw"

    application = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            ENTER_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_number)],
            ENTER_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_password)],
            ENTER_MEMBER1: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_member1)],
            ENTER_MEMBER2: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_member2)],
            CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    application.add_handler(conv_handler)
    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
