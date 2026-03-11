import requests
import threading
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from config import AVIATIONSTACK_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, CHECK_INTERVAL_MINUTES

app = Flask(__name__)

# 存储正在监控的航班和上次状态
monitored_flights = {}  # key: "EK306_2026-03-13", value: last_status


def query_flight(flight_iata, flight_date):
    """查询航班状态（免费版不支持按日期过滤，客户端过滤）"""
    url = "http://api.aviationstack.com/v1/flights"
    params = {
        "access_key": AVIATIONSTACK_API_KEY,
        "flight_iata": flight_iata.upper(),
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        if data.get("error"):
            return {"error": data["error"].get("message", "API 错误")}
        flights = data.get("data", [])
        # 按日期过滤
        matched = [f for f in flights if f.get("flight_date", "") == flight_date]
        flight = matched[0] if matched else (flights[0] if flights else None)
        if not flight:
            return None
        return {
            "flight_iata": flight_iata.upper(),
            "date": flight.get("flight_date", flight_date),
            "status": flight.get("flight_status", "unknown"),
            "departure_airport": flight.get("departure", {}).get("airport", ""),
            "departure_scheduled": flight.get("departure", {}).get("scheduled", ""),
            "departure_delay": flight.get("departure", {}).get("delay"),
            "arrival_airport": flight.get("arrival", {}).get("airport", ""),
            "arrival_scheduled": flight.get("arrival", {}).get("scheduled", ""),
            "airline": flight.get("airline", {}).get("name", ""),
        }
    except Exception as e:
        return {"error": str(e)}


def send_telegram(message):
    """发送 Telegram 通知"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=10)
    except Exception as e:
        print(f"Telegram 发送失败: {e}")


STATUS_ZH = {
    "scheduled": "正常（计划中）",
    "active": "飞行中",
    "landed": "已降落",
    "cancelled": "已取消 ✈️❌",
    "incident": "出现事故",
    "diverted": "改飞其他机场",
    "unknown": "未知",
}


def monitor_loop():
    """后台监控线程"""
    while True:
        for key, last_status in list(monitored_flights.items()):
            flight_iata, flight_date = key.split("_", 1)
            result = query_flight(flight_iata, flight_date)
            if result and "status" in result:
                current_status = result["status"]
                if current_status != last_status:
                    monitored_flights[key] = current_status
                    zh = STATUS_ZH.get(current_status, current_status)
                    msg = (
                        f"⚠️ 航班状态变化！\n"
                        f"航班：{flight_iata}  日期：{flight_date}\n"
                        f"新状态：{zh}\n"
                        f"出发：{result.get('departure_airport')} {result.get('departure_scheduled', '')}\n"
                        f"到达：{result.get('arrival_airport')} {result.get('arrival_scheduled', '')}"
                    )
                    send_telegram(msg)
                    print(f"[{datetime.now()}] 状态变化: {key} -> {current_status}")
        time.sleep(CHECK_INTERVAL_MINUTES * 60)


# 启动后台监控线程
threading.Thread(target=monitor_loop, daemon=True).start()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/query", methods=["POST"])
def api_query():
    data = request.json
    flight_iata = data.get("flight_iata", "").strip()
    flight_date = data.get("flight_date", "").strip()
    if not flight_iata or not flight_date:
        return jsonify({"error": "请填写航班号和日期"}), 400
    result = query_flight(flight_iata, flight_date)
    if not result:
        return jsonify({"error": "未找到该航班，请检查航班号和日期"}), 404
    return jsonify(result)


@app.route("/api/monitor", methods=["POST"])
def api_monitor():
    data = request.json
    flight_iata = data.get("flight_iata", "").strip().upper()
    flight_date = data.get("flight_date", "").strip()
    key = f"{flight_iata}_{flight_date}"
    result = query_flight(flight_iata, flight_date)
    if not result or "error" in result:
        return jsonify({"error": "无法查到该航班，无法开始监控"}), 404
    monitored_flights[key] = result.get("status", "unknown")
    send_telegram(
        f"✅ 开始监控航班 {flight_iata}（{flight_date}）\n"
        f"当前状态：{STATUS_ZH.get(result['status'], result['status'])}\n"
        f"每 {CHECK_INTERVAL_MINUTES} 分钟检查一次，状态变化时通知你。"
    )
    return jsonify({"message": f"已开始监控 {flight_iata}，状态变化时 Telegram 会通知你", "current_status": result["status"]})


@app.route("/api/monitored", methods=["GET"])
def api_monitored():
    return jsonify(monitored_flights)


if __name__ == "__main__":
    app.run(debug=True, port=5002)
