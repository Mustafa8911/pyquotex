import os
import asyncio
from aiohttp import web
from pyquotex.stable_api import Quotex

# ======================
# قراءة إعدادات من environment (مناسب لـ Render)
# ======================
EMAIL = os.environ.get("EMAIL", "mustafa74833929@gmail.com")
PASSWORD = os.environ.get("PASSWORD", "Mustafa8911220")
ACCOUNT_MODE = os.environ.get("ACCOUNT_MODE", "DEMO").upper()  # DEMO or REAL

BASE_AMOUNT = float(os.environ.get("BASE_AMOUNT", "1.0"))
MARTINGALE_MULTIPLIER = float(os.environ.get("MARTINGALE_MULTIPLIER", "2"))
TRADE_DURATION = int(os.environ.get("TRADE_DURATION", "60"))  # بالثواني
MAX_MARTINGALE = int(os.environ.get("MAX_MARTINGALE", "5"))

# المنفذ الذي توفره Render في متغير PORT
PORT = int(os.environ.get("PORT", "5050"))
HOST = "0.0.0.0"

# ======================
# تهيئة مكتبة Quotex
# ======================
client = Quotex(email=EMAIL, password=PASSWORD)

# لكل زوج مستوى خاص
martingale_level = {}

# لمعرفة هل هناك صفقة مفتوحة على الزوج (store order_id)
active_order = {}

# ======================
# تسجيل الدخول
# ======================
async def initialize_client():
    try:
        await client.connect()
        if ACCOUNT_MODE == "REAL":
            await client.change_account("REAL")
        else:
            await client.change_account("PRACTICE")
        print("✅ تم تسجيل الدخول بنجاح")
        print(f"Mode={ACCOUNT_MODE}  BASE_AMOUNT={BASE_AMOUNT}  TRADE_DURATION={TRADE_DURATION}s  MAX_MART={MAX_MARTINGALE}")
    except Exception as e:
        print("❌ فشل تسجيل الدخول/الاتصال:", e)
        raise


# ======================
# أسرع طريقة للحصول على نتيجة (poll every 0.5s)
# ======================
async def fast_check(order_id, timeout_seconds=90):
    """
    يتحقق من نتيجة الصفقة كل 0.5 ثانية حتى timeout_seconds ثم يعيد None.
    """
    attempts = int(timeout_seconds / 0.5)
    for _ in range(attempts):
        try:
            res = await client.check_win(order_id)
            if res is not None:
                return res
        except Exception as e:
            # تجاهل أخطاء مؤقتة
            print("warn: check_win exception:", e)
        await asyncio.sleep(0.5)
    return None


# ======================
# تنفيذ الصفقة
# ======================
async def open_trade(asset, direction):
    """
    يفتح صفقة إذا لم تكن هناك صفقة مفتوحة على نفس الزوج.
    يقرأ النتيجة بسرعة (كل 0.5s) ويحدّث مارتنجال.
    """
    # منع فتح صفقة جديدة لزوج مفتوح
    if active_order.get(asset):
        print(f"⛔ تجاهل الإشارة — توجد صفقة مفتوحة حالياً على {asset}")
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
        print("❌ فشل إرسال الصفقة (status false أو order is None)")
        return

    order_id = order.get("id")
    if not order_id:
        print("⚠ لا يوجد order_id — لا يمكن متابعة الصفقة")
        return

    # سجل أن هناك صفقة نشطة لهذا الزوج
    active_order[asset] = order_id
    print(f"⏳ صفقة مفتوحة order_id={order_id} — التحقق السريع من النتيجة...")

    # تحقق سريع للحصول على النتيجة بأقصر وقت ممكن
    result = await fast_check(order_id, timeout_seconds=90)

    # إفراغ حالة الصفقة حتى نسمح بإشارات لاحقة
    active_order[asset] = None

    if result is None:
        print("⚠ لم يتم الحصول على نتيجة الصفقة ضمن المهلة. لم يتغير مستوى المارتنجال.")
        return

    # بعض إصدارات API قد ترجع True/False بدلاً من رقم ربح: نتعامل مع ذلك
    profit = 0
    if isinstance(result, bool):
        profit = 1 if result else 0
    else:
        try:
            profit = float(result)
        except Exception:
            # إذا لم نتمكن من تحويلها نعاملها كـ 0
            profit = 0

    if profit > 0:
        print(f"🏆 ربح: +{profit} — إعادة المارتنجال إلى 0")
        martingale_level[asset] = 0
    else:
        new_level = min(martingale_level.get(asset, 0) + 1, MAX_MARTINGALE)
        martingale_level[asset] = new_level
        print(f"❌ خسارة — المستوى الجديد = {martingale_level[asset]}")


# ======================
# Webhook handler
# ======================
async def handle_webhook(request):
    """
    تتوقع JSON: {"asset": "EURUSD", "signal": "buy"}
    يدعم buy/sell (أو call/put) ويدشّن open_trade في مهمة غير متزامنة.
    """
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "invalid json"}, status=400)

    asset = data.get("asset")
    signal = data.get("signal")

    if not asset or not signal:
        return web.json_response({"error": "Missing asset or signal"}, status=400)

    s = signal.lower()
    if s in ("buy", "long", "call"):
        direction = "call"
    elif s in ("sell", "short", "put"):
        direction = "put"
    else:
        return web.json_response({"error": "Invalid signal value"}, status=400)

    # إطلاق تنفيذ الصفقة في مهمة موازية
    asyncio.create_task(open_trade(asset, direction))

    return web.json_response({"status": "accepted"})


# ======================
# Health check (Render)
# ======================
async def handle_root(request):
    return web.Response(text="OK")


# ======================
# تشغيل الخادم
# ======================
async def start_server():
    await initialize_client()

    app = web.Application()
    app.router.add_get("/", handle_root)        # health check
    app.router.add_post("/hook", handle_webhook)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, HOST, PORT)
    await site.start()

    print(f"🚀 Webhook جاهز على http://{HOST}:{PORT}/hook")
    # Keep running
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    try:
        asyncio.run(start_server())
    except KeyboardInterrupt:
        print("🔵 Shutting down.")
