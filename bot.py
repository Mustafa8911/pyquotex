import asyncio
import json
from aiohttp import web
from pyquotex import Quotex

EMAIL = "mustafa74833929@gmail.com"
PASSWORD = "Mustafa8911220"

client = Quotex(email=EMAIL, password=PASSWORD)

current_signal = None
martingale_level = 0
max_martingale = 5
base_amount = 1


async def login():
    print("Connecting User Account ...")
    try:
        await client.connect()
        print("✅ تم تسجيل الدخول بنجاح")
    except Exception as e:
        print("❌ فشل تسجيل الدخول/الاتصال:", e)


async def execute_trade(signal, amount):
    try:
        result = await client.buy(asset=current_signal["asset"], amount=amount, action=signal)

        if result is None:
            print("❌ لم يتم فتح الصفقة")
            return None

        print("📌 صفقة مفتوحة، رقمها:", result)
        return result

    except Exception as e:
        print("❌ خطأ أثناء فتح الصفقة:", e)


async def check_result(position_id):
    """
    التحقق من نتيجة الصفقة بالقوة
    لأن Render لا يدعم WebSocket events
    """
    for _ in range(40):  # 40 × 1 ثانية = 40 ثانية انتظار
        try:
            status = await client.get_position(position_id)
            if status and status["status"] in ["win", "loss"]:
                return status
        except:
            pass

        await asyncio.sleep(1)

    return None


async def process_signal():
    global martingale_level

    print(f"🚀 بدء صفقة جديدة: {current_signal}")

    amount = base_amount * (2 ** martingale_level)
    print("💰 قيمة دخول الصفقة:", amount)

    trade = await execute_trade(current_signal["signal"], amount)
    if not trade:
        print("❌ لا يوجد صفقة مفتوحة، إلغاء")
        martingale_level = 0
        return

    print("⏳ بانتظار نتيجة الصفقة ...")

    result = await check_result(trade)

    if not result:
        print("⚠️ فشل معرفة نتيجة الصفقة")
        martingale_level = 0
        return

    status = result["status"]
    print("📊 نتيجة الصفقة:", status)

    if status == "win":
        print("🏆 ربح — إعادة المارتنجال للصفر")
        martingale_level = 0

    else:
        print("❌ خسارة")
        if martingale_level < max_martingale:
            martingale_level += 1
            print("🔁 تشغيل مارتنجال رقم:", martingale_level)
            await process_signal()
        else:
            print("⛔ وصلت للحد الأقصى للمضاعفات")
            martingale_level = 0


async def webhook_handler(request):
    global current_signal

    data = await request.json()
    print("📩 Webhook:", data)

    current_signal = {
        "asset": data["asset"],
        "signal": data["signal"]
    }

    asyncio.create_task(process_signal())
    return web.Response(text="OK")


async def start_server():
    await login()

    app = web.Application()
    app.router.add_post("/hook", webhook_handler)

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, "0.0.0.0", 10000)
    print("🚀 Webhook Server Running on port 10000")
    await site.start()

    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(start_server())
