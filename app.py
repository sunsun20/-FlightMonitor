import requests
import threading
import time
import base64
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from config import AVIATIONSTACK_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, CHECK_INTERVAL_MINUTES, DEEPSEEK_API_KEY

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
        if not matched:
            return {"error": f"未找到 {flight_date} 的航班数据，该日期可能还未进入系统（通常起飞前 1-2 天才会有数据）"}
        flight = matched[0]
        if not flight:
            return None
        dep = flight.get("departure", {})
        arr = flight.get("arrival", {})
        return {
            "flight_iata": flight_iata.upper(),
            "flight_number": flight.get("flight", {}).get("number", ""),
            "date": flight.get("flight_date", flight_date),
            "status": flight.get("flight_status", "unknown"),
            "airline": flight.get("airline", {}).get("name", ""),
            "aircraft": flight.get("aircraft", {}).get("registration", ""),
            # 出发
            "departure_airport": dep.get("airport", ""),
            "departure_iata": dep.get("iata", ""),
            "departure_terminal": dep.get("terminal", ""),
            "departure_gate": dep.get("gate", ""),
            "departure_scheduled": dep.get("scheduled", ""),
            "departure_estimated": dep.get("estimated", ""),
            "departure_actual": dep.get("actual", ""),
            "departure_delay": dep.get("delay"),
            # 到达
            "arrival_airport": arr.get("airport", ""),
            "arrival_iata": arr.get("iata", ""),
            "arrival_terminal": arr.get("terminal", ""),
            "arrival_gate": arr.get("gate", ""),
            "arrival_scheduled": arr.get("scheduled", ""),
            "arrival_estimated": arr.get("estimated", ""),
            "arrival_baggage": arr.get("baggage", ""),
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


def format_flight_msg(result):
    """把航班数据格式化成 Telegram 消息"""
    zh = STATUS_ZH.get(result.get("status", ""), result.get("status", ""))

    dep_terminal = f"T{result['departure_terminal']}" if result.get("departure_terminal") else "-"
    dep_gate     = result.get("departure_gate") or "待定"
    dep_sched    = result.get("departure_scheduled", "")[:16].replace("T", " ")
    dep_est      = result.get("departure_estimated", "")[:16].replace("T", " ")
    dep_actual   = result.get("departure_actual", "")[:16].replace("T", " ")
    dep_delay    = result.get("departure_delay")

    arr_terminal = f"T{result['arrival_terminal']}" if result.get("arrival_terminal") else "-"
    arr_gate     = result.get("arrival_gate") or "待定"
    arr_sched    = result.get("arrival_scheduled", "")[:16].replace("T", " ")
    arr_est      = result.get("arrival_estimated", "")[:16].replace("T", " ")
    arr_baggage  = result.get("arrival_baggage") or "-"

    lines = [
        f"✈️ {result.get('flight_iata')}  {result.get('airline', '')}",
        f"状态：{zh}",
        f"─────────────",
        f"【出发】{result.get('departure_airport')} ({result.get('departure_iata', '')})",
        f"航站楼：{dep_terminal}  登机口：{dep_gate}",
        f"计划起飞：{dep_sched}",
    ]
    if dep_est and dep_est != dep_sched:
        lines.append(f"预计起飞：{dep_est}")
    if dep_actual:
        lines.append(f"实际起飞：{dep_actual}")
    if dep_delay:
        lines.append(f"⏰ 延误：{dep_delay} 分钟")
    lines.append("─────────────")
    lines += [
        f"【到达】{result.get('arrival_airport')} ({result.get('arrival_iata', '')})",
        f"航站楼：{arr_terminal}  登机口：{arr_gate}",
        f"计划到达：{arr_sched}",
    ]
    if arr_est and arr_est != arr_sched:
        lines.append(f"预计到达：{arr_est}")
    lines.append(f"🧳 行李转盘：{arr_baggage}")

    return "\n".join(lines)


def extract_flight_from_image(image_bytes):
    """用 DeepSeek Vision 识别截图中的航班号和日期"""
    b64 = base64.b64encode(image_bytes).decode()
    resp = requests.post(
        "https://api.deepseek.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
        json={
            "model": "deepseek-chat",
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                    {"type": "text", "text": (
                        "这是一张机票订单或航班信息截图。"
                        "请提取航班号和出发日期，只返回 JSON 格式，例如：{\"flight\": \"EK306\", \"date\": \"2026-03-13\"}"
                        "如果有多个航班，返回第一个。如果识别不到，返回 {\"flight\": null, \"date\": null}"
                    )}
                ]
            }],
            "max_tokens": 100
        },
        timeout=30
    )
    import json, re
    content = resp.json()["choices"][0]["message"]["content"]
    match = re.search(r'\{.*?\}', content, re.DOTALL)
    if match:
        return json.loads(match.group())
    return {"flight": None, "date": None}


def send_msg(chat_id, text):
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        json={"chat_id": chat_id, "text": text},
        timeout=10
    )


def telegram_bot_loop():
    """Telegram Bot 轮询，接收用户消息并回复航班查询"""
    offset = 0
    today = datetime.now().strftime("%Y-%m-%d")
    # 等待确认的状态：chat_id -> {"flight": "EK306", "date": "2026-03-13"}
    pending = {}

    while True:
        try:
            resp = requests.get(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates",
                params={"offset": offset, "timeout": 30},
                timeout=35
            )
            updates = resp.json().get("result", [])
            for update in updates:
                offset = update["update_id"] + 1
                msg = update.get("message", {})
                chat_id = msg.get("chat", {}).get("id")
                if not chat_id:
                    continue

                # 处理图片
                if msg.get("photo"):
                    send_msg(chat_id, "🔍 识别中，请稍等...")
                    try:
                        # 取最高清的图片
                        file_id = msg["photo"][-1]["file_id"]
                        file_info = requests.get(
                            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile",
                            params={"file_id": file_id}, timeout=10
                        ).json()
                        file_path = file_info["result"]["file_path"]
                        image_bytes = requests.get(
                            f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}",
                            timeout=15
                        ).content
                        parsed = extract_flight_from_image(image_bytes)
                        flight = parsed.get("flight")
                        date = parsed.get("date") or today
                        if flight:
                            pending[chat_id] = {"flight": flight, "date": date}
                            send_msg(chat_id, f"识别到：✈️ {flight}  📅 {date}\n\n发送「确认」查询，或发送「取消」")
                        else:
                            send_msg(chat_id, "❌ 未能识别到航班信息，请直接发送航班号，例如：EK306")
                    except Exception as e:
                        send_msg(chat_id, f"❌ 识别失败：{e}")
                    continue

                text = msg.get("text", "").strip()
                if not text:
                    continue

                # 处理确认/取消
                if chat_id in pending:
                    if text in ("确认", "是", "yes", "ok", "OK", "Yes"):
                        p = pending.pop(chat_id)
                        result = query_flight(p["flight"], p["date"])
                        if not result:
                            reply = f"❌ 未找到数据"
                        elif "error" in result:
                            reply = f"❌ {result['error']}"
                        else:
                            reply = format_flight_msg(result)
                        send_msg(chat_id, reply)
                        continue
                    elif text in ("取消", "no", "No"):
                        pending.pop(chat_id)
                        send_msg(chat_id, "已取消")
                        continue

                # 文字查询：EK306 或 EK306 2026-03-13
                parts = text.upper().split()
                flight_iata = parts[0] if parts else ""
                flight_date = parts[1] if len(parts) > 1 else today

                if len(flight_iata) < 3 or not any(c.isdigit() for c in flight_iata):
                    send_msg(chat_id, "发送格式：\nEK306\n或\nEK306 2026-03-13\n\n也可以直接发截图 📸")
                    continue

                result = query_flight(flight_iata, flight_date)
                if not result:
                    reply = f"❌ 未找到 {flight_iata} {flight_date} 的数据"
                elif "error" in result:
                    reply = f"❌ {result['error']}"
                else:
                    reply = format_flight_msg(result)
                send_msg(chat_id, reply)

        except Exception as e:
            print(f"Bot 轮询错误: {e}")
            time.sleep(5)


# 启动后台监控线程
threading.Thread(target=monitor_loop, daemon=True).start()
# 启动 Telegram Bot 轮询线程
threading.Thread(target=telegram_bot_loop, daemon=True).start()


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
