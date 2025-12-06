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

# === EVENT LOOP واحد فقط ===
event_loop = asyncio.new_event_loop()
asyncio.set_event_loop(event_loop)


# === تسجيل الدخول ===
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

    pair = pairs_state[asset]
    pair["trade_no"] += 1
    amount = 3

    direction_map = {"buy": "call", "sell": "put"}
    direction = direction_map.get(signal.lower())

    if not direction:
        print(f"⚠️ إشارة غير صحيحة: {signal}")
        return

    print(f"📊 [{asset}] تنفيذ صفقة رقم {pair['trade_no']} بمبلغ {amount}$ - الاتجاه: {direction}")

    try:
        status, order = await client.buy(
            amount=amount,
            asset=asset,
            direction=direction,
            duration=TRADE_DURATION
        )

        if not status:
            print(f"⚠️ فشل فتح الصفقة على {asset}")
            return

        trade_id = order.get("id") if isinstance(order, dict) else getattr(order, "id", None)
        print(f"✅ تم فتح الصفقة على {asset} ({direction}) لمدة {TRADE_DURATION} ثانية ⏱️ trade_id={trade_id}")

    except Exception as e:
        print(f"⚠️ خطأ أثناء فتح الصفقة على {asset}: {e}")


# === استقبال إشارة من TradingView ===
@app.route("/hook", methods=["POST"])
def webhook():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data"}), 400

    asset = data.get("asset")
    signal = data.get("signal")

    print(f"📥 [{asset}] إشارة مستلمة: {data}")

    # إرسال المهمة إلى EVENT LOOP الوحيد
    event_loop.call_soon_threadsafe(
        lambda: asyncio.create_task(execute_trade(asset, signal))
    )

    return jsonify({"status": "Signal received"}), 200


# === تشغيل السيرفر + event loop ===
def start_loop():
    event_loop.run_until_complete(connect())
    print("🔄 Event Loop Started")


threading.Thread(target=start_loop, daemon=True).start()

import os
port = int(os.environ.get("PORT", 10000))
print(f"🚀 السيرفر يعمل على المنفذ {port} ...")
app.run(host="0.0.0.0", port=port)
