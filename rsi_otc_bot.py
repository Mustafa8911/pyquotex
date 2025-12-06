import asyncio
from flask import Flask, request, jsonify
from pyquotex.stable_api import Quotex
import threading

# === إعداد بيانات الدخول ===
EMAIL = "mustafa74833929@gmail.com"
PASSWORD = "Mustafa8911220"
TRADE_DURATION = 60  # مدة الصفقة بالثواني

# === إدارة حالة كل أصل ===
pairs_state = {}

# === إعداد Flask ===
app = Flask(__name__)

# === تهيئة Quotex ===
client = Quotex(email=EMAIL, password=PASSWORD)

# === الاتصال مرة واحدة فقط ===
async def connect():
    print("🔌 تسجيل الدخول إلى Quotex...")
    if not await client.connect():
        print("❌ فشل تسجيل الدخول.")
        return False
    client.is_demo = True
    print("✅ تم تسجيل الدخول بنجاح!")
    return True

# === تنفيذ الصفقة ===
async def execute_trade(asset, signal):
    if asset not in pairs_state:
        pairs_state[asset] = {"trade_no": 0}

    pairs_state[asset]["trade_no"] += 1
    trade_no = pairs_state[asset]["trade_no"]
    amount = 3

    direction_map = {"buy": "call", "sell": "put"}
    direction = direction_map.get(signal.lower())

    if not direction:
        print(f"⚠️ إشارة غير صحيحة: {signal}")
        return

    print(f"📊 [{asset}] تنفيذ صفقة رقم {trade_no} بمبلغ {amount}$ - الاتجاه: {direction}")

    try:
        status, order = await client.buy(
            amount=amount,
            asset=asset,
            direction=direction,
            duration=TRADE_DURATION,
        )

        if not status:
            print(f"⚠️ فشل فتح الصفقة على {asset}")
            return

        trade_id = order.get("id") if isinstance(order, dict) else getattr(order, "id", None)
        print(f"✅ تم فتح الصفقة على {asset} ({direction}) trade_id={trade_id}")

    except Exception as e:
        print(f"⚠️ خطأ أثناء فتح الصفقة على {asset}: {e}")

# === استقبال الإشارة ===
@app.route("/hook", methods=["POST"])
def webhook():
    data = request.get_json()

    if not data:
        return jsonify({"error": "no data"}), 400

    asset = data.get("asset")
    signal = data.get("signal")

    print(f"📥 [{asset}] إشارة مستلمة: {data}")

    # إرسال المهمة إلى event loop الأساسي بدلاً من asyncio.run()
    loop = asyncio.get_event_loop()
    loop.create_task(execute_trade(asset, signal))

    return jsonify({"status": "ok"}), 200

# === تشغيل السيرفر ===
def start_flask():
    app.run(host="0.0.0.0", port=5050)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(connect())

    print("🚀 السيرفر يعمل على المنفذ 5050 ...")

    # Flask يعمل في Thread منفصل
    threading.Thread(target=start_flask).start()

    # استمرار الـ event loop
    loop.run_forever()
