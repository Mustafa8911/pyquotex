import asyncio
from flask import Flask, request, jsonify
from pyquotex.stable_api import Quotex
import threading

# === بيانات الدخول مباشرة ===
EMAIL = "mustafa74833929@gmail.com"
PASSWORD = "Mustafa8911220"
TRADE_DURATION = 60  # مدة الصفقة بالثواني
TRADE_AMOUNT = 3     # المبلغ لكل صفقة

# === إدارة حالة كل أصل ===
pairs_state = {}  # مثال: {"EURUSD": {"trade_no": 0}}

# === إعداد Flask ===
app = Flask(__name__)

# === تهيئة Quotex ===
client = Quotex(email=EMAIL, password=PASSWORD)

# === تسجيل الدخول ===
async def connect():
    print("🔌 تسجيل الدخول إلى Quotex...")
    try:
        success = await client.connect()
        if not success:
            print("❌ فشل تسجيل الدخول. تحقق من البيانات أو الشبكة.")
            return False
    except Exception as e:
        print(f"⚠️ خطأ أثناء تسجيل الدخول: {e}")
        return False

    client.is_demo = True  # اختر DEMO أو REAL حسب الحساب
    print("✅ تم تسجيل الدخول بنجاح!")
    return True

# === تنفيذ الصفقة ===
async def execute_trade(asset, signal):
    if asset not in pairs_state:
        pairs_state[asset] = {"trade_no": 0}

    pair = pairs_state[asset]
    pair["trade_no"] += 1

    # تحويل إشارة TradingView إلى call/put
    direction_map = {"buy": "call", "sell": "put"}
    direction = direction_map.get(signal.lower())
    if not direction:
        print(f"⚠️ إشارة غير صحيحة: {signal}")
        return

    print(f"📊 [{asset}] تنفيذ صفقة رقم {pair['trade_no']} بمبلغ {TRADE_AMOUNT}$ - الاتجاه: {direction}")

    try:
        status, order = await client.buy(
            amount=TRADE_AMOUNT,
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
        return jsonify({"error": "No data received"}), 400

    asset = data.get("asset")
    signal = data.get("signal")
    print(f"📥 [{asset}] إشارة مستلمة: {data}")

    threading.Thread(target=lambda: asyncio.run(execute_trade(asset, signal))).start()
    return jsonify({"status": f"Signal for {asset} received"}), 200

# === تشغيل السيرفر ===
if __name__ == "__main__":
    if not asyncio.run(connect()):
        print("❌ توقف السيرفر بسبب فشل تسجيل الدخول.")
    else:
        print("🚀 السيرفر يعمل على المنفذ 5050 ...")
        app.run(host="0.0.0.0", port=5050)
