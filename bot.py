import asyncio
from aiohttp import web
from pyquotex.stable_api import Quotex

# ===== إعدادات الدخول =====
EMAIL = "mustafa74833929@gmail.com"
PASSWORD = "Mustafa8911220"
ACCOUNT_MODE = "DEMO"   # REAL أو DEMO

# ===== إعدادات التداول =====
BASE_AMOUNT = 1.0      # مبلغ ثابت
TRADE_DURATION = 60    # مدة الصفقة بالثواني

client = Quotex(email=EMAIL, password=PASSWORD)

# الصفقة المفتوحة لكل زوج
active_order = {}


# ========== تسجيل الدخول ==========
async def initialize_client():
    await client.connect()

    if ACCOUNT_MODE.upper() == "REAL":
        await client.change_account("REAL")
    else:
        await client.change_account("PRACTICE")

    print("✅ تم تسجيل الدخول بنجاح\n")


# ========= جلب نتيجة الصفقة ==========
async def fast_check(order_id):
    for _ in range(200):
        try:
            res = await client.check_win(order_id)
            if res is not None:
                return res
        except:
            pass
        await asyncio.sleep(0.5)
    return None


# ========== تنفيذ الصفقة ==========
async def execute_trade(asset, direction):

    print(f"\n📩 إشارة: {asset} — {direction}")
    print(f"📌 فتح صفقة بمبلغ ثابت: {BASE_AMOUNT}")

    try:
        status, order = await client.buy(
            BASE_AMOUNT,
            asset,
            direction,
            TRADE_DURATION
        )
    except Exception as e:
        print(f"⚠ خطأ في إرسال الصفقة: {e}")
        return

    if not status or not order:
        print("❌ فشل إرسال الصفقة")
        return

    order_id = order.get("id")
    if not order_id:
        print("⚠ لا يوجد order_id")
        return

    active_order[asset] = order_id
    print(f"[{asset}] ⏳ الصفقة بدأت...")

    await asyncio.sleep(TRADE_DURATION)

    result = await fast_check(order_id)
    active_order[asset] = None

    if result is None:
        print(f"[{asset}] ⚠ لم يتم جلب النتيجة")
    elif result > 0:
        print(f"[{asset}] 🏆 ربح: +{result}")
    else:
        print(f"[{asset}] ❌ خسارة")


# ========== معالجة الإشارة ==========
async def process_signal(asset, direction):

    if active_order.get(asset):
        print(f"🚫 تم تجاهل الإشارة — صفقة {asset} ما زالت مفتوحة")
        return

    asyncio.create_task(execute_trade(asset, direction))


# ========== webhook ==========
async def handle_webhook(request):
    try:
        data = await request.json()
    except:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    asset = data.get("asset")
    signal = data.get("signal")

    if not asset or not signal:
        return web.json_response({"error": "Invalid signal"}, status=400)

    direction = "call" if signal.lower() == "buy" else "put"

    await process_signal(asset, direction)

    return web.json_response({"status": "received"})


# ========== تشغيل السيرفر ==========
async def start_server():
    await initialize_client()

    app = web.Application()
    app.router.add_post("/hook", handle_webhook)

    print("🚀 Webhook جاهز:")
    print("http://0.0.0.0:5050/hook")
    print("https://webhook.vmfjfnfkfldlfld.org/hook")

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 5050)
    await site.start()

    while True:
        await asyncio.sleep(3600)


asyncio.run(start_server())
