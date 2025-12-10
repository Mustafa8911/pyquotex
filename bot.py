import asyncio
from aiohttp import web
from pyquotex.stable_api import Quotex

# ===== إعدادات الدخول =====
EMAIL = "mustafa74833929@gmail.com"
PASSWORD = "Mustafa8911220"
ACCOUNT_MODE = "DEMO"

# ===== إعدادات التداول =====
BASE_AMOUNT = 1.0
MARTINGALE_MULTIPLIER = 2
TRADE_DURATION = 60
MAX_MARTINGALE = 5

client = Quotex(email=EMAIL, password=PASSWORD)

# لكل زوج مستوى خاص
martingale_level = {}

# لمعرفة هل هناك صفقة مفتوحة على الزوج
active_order = {}


# ========== تسجيل الدخول ==========
async def initialize_client():
    await client.connect()

    if ACCOUNT_MODE.upper() == "REAL":
        await client.change_account("REAL")
    else:
        await client.change_account("PRACTICE")

    print("✅ تم تسجيل الدخول بنجاح\n")


# ========= أسرع طريقة للحصول على النتيجة ==========
async def fast_check(order_id):
    """
    يتحقق من نتيجة الصفقة كل 0.5 ثانية
    بدون انتظار 60s كاملة
    أسرع طريقة متوافقة مع pyquotex
    """
    for _ in range(180):  # 90 ثانية / 0.5 ثانية
        try:
            res = await client.check_win(order_id)
            if res is not None:
                return res
        except:
            pass

        await asyncio.sleep(0.5)

    return None


# ========== تنفيذ الصفقة ==========
async def open_trade(asset, direction):

    # منع فتح صفقة جديدة قبل انتهاء السابقة
    if active_order.get(asset):
        print(f"⛔ لا يمكن فتح صفقة جديدة — هناك صفقة مفتوحة على {asset}")
        return

    level = martingale_level.get(asset, 0)
    amount = BASE_AMOUNT * (MARTINGALE_MULTIPLIER ** level)

    print(f"\n📩 إشارة: {asset} — {direction}")
    print(f"📌 مستوى {level} — فتح صفقة بمبلغ {amount}")

    try:
        status, order = await client.buy(amount, asset, direction, TRADE_DURATION)
    except Exception as e:
        print(f"⚠ خطأ عند إرسال الصفقة: {e}")
        return

    if not status or order is None:
        print("❌ فشل إرسال الصفقة")
        return

    order_id = order.get("id")
    if not order_id:
        print("⚠ لا يوجد order_id — لا يمكن متابعة الصفقة")
        return

    # نُسجّل الصفقة كصفقة مفتوحة
    active_order[asset] = order_id

    print("⏳ التحقق السريع من نتيجة الصفقة...")

    result = await fast_check(order_id)

    # عند الحصول على النتيجة — نحذف حالة الصفقة المفتوحة
    active_order[asset] = None

    if result is None:
        print("⚠ لم يتم الحصول على النتيجة")
        return

    # ======== تحليل النتيجة ============
    if result > 0:
        print(f"🏆 ربح: +{result} — reset")
        martingale_level[asset] = 0
    else:
        martingale_level[asset] = min(martingale_level.get(asset, 0) + 1, MAX_MARTINGALE)
        print(f"❌ خسارة — المستوى الجديد {martingale_level[asset]}")


# ========== webhook ==========
async def handle_webhook(request):
    data = await request.json()

    asset = data.get("asset")
    signal = data.get("signal")

    if not asset or not signal:
        return web.json_response({"error": "Invalid signal"})

    direction = "call" if signal.lower() == "buy" else "put"

    # إطلاق الصفقة
    asyncio.create_task(open_trade(asset, direction))

    return web.json_response({"status": "received"})


# ========== تشغيل السيرفر ==========
async def start_server():
    await initialize_client()

    app = web.Application()
    app.router.add_post("/hook", handle_webhook)

    print("🚀 Webhook جاهز:")
    print("http://0.0.0.0:5050/hook")
    print("https://vmfjfnfkfldlfld.org/hook")

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 5050)
    await site.start()

    while True:
        await asyncio.sleep(3600)


asyncio.run(start_server())
