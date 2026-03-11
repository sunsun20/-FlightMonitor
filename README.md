# 航班状态监控工具

查询航班实时状态，航班取消/延误时自动发送 Telegram 通知。

---

## 项目结构

```
FlightMonitor/
├── app.py              # 后端主程序
├── config.py           # 配置文件（API Key、Telegram 等）
├── requirements.txt    # Python 依赖
├── templates/
│   └── index.html      # 前端页面
└── venv/               # Python 虚拟环境（不需要动）
```

---

## 启动方法

### 第一次使用

打开终端，进入项目目录：

```bash
cd ~/Downloads/自创app/FlightMonitor
```

安装依赖（只需要做一次）：

```bash
venv/bin/pip install -r requirements.txt
```

### 每次启动

```bash
cd ~/Downloads/自创app/FlightMonitor
venv/bin/python app.py
```

看到以下输出说明启动成功：

```
 * Running on http://127.0.0.1:5002
```

然后打开浏览器访问：**http://localhost:5002**

---

## 使用方法

### 查询航班状态

1. 在「航班号」输入框填入航班号，例如 `EK306`
2. 在「日期」选择你的出发日期
3. 点击「**查询状态**」按钮

页面会显示：
- 航班状态（正常 / 飞行中 / 已降落 / 已取消 / 延误）
- 出发机场和计划起飞时间
- 到达机场和计划到达时间
- 延误分钟数（有延误时显示红色）

### 开始自动监控（推荐）

1. 填好航班号和日期后，点击「**开始监控**」
2. 程序每 **10 分钟**自动检查一次航班状态
3. 状态发生变化时（比如从"正常"变成"取消"），**Telegram 会立即发消息通知你**

> 注意：监控依赖程序持续运行，关闭终端后监控会停止。

---

## 关闭程序

### 方法一：在终端直接按

```
Ctrl + C
```

### 方法二：如果终端已经关了，找到进程手动杀掉

查找程序进程：

```bash
ps aux | grep app.py
```

会看到类似这样的输出：

```
hugo  12345  ...  venv/bin/python app.py
```

记下前面的数字（进程 ID），然后：

```bash
kill 12345
```

### 方法三：一键关闭

```bash
pkill -f "venv/bin/python app.py"
```

---

## 配置说明

配置文件在 `config.py`，如需修改：

| 参数 | 说明 |
|------|------|
| `AVIATIONSTACK_API_KEY` | 航班数据 API Key（来自 aviationstack.com） |
| `TELEGRAM_BOT_TOKEN` | Telegram 机器人 Token |
| `TELEGRAM_CHAT_ID` | 你的 Telegram 用户 ID |
| `CHECK_INTERVAL_MINUTES` | 监控检查间隔，默认 10 分钟 |

---

## 航班状态说明

| 状态 | 含义 |
|------|------|
| scheduled | 正常，计划中 |
| active | 飞行中 |
| landed | 已降落 |
| cancelled | 已取消 ❌ |
| diverted | 改飞其他机场 |
| incident | 出现事故 |

---

## 常见问题

**Q：查询显示"未找到该航班"？**
A：航班数据通常在起飞前 1-2 天才会出现在系统里，太早查可能没有数据。

**Q：Telegram 没有收到通知？**
A：确认已经给 `@hugo_flight_bot` 发过消息（必须先发消息，Bot 才能给你发通知）。

**Q：关掉终端后监控停了怎么办？**
A：重新启动程序，再点一次「开始监控」即可。后续可以部署到 Azure VM 上实现 24 小时运行。

---

## 后续计划

- [ ] 部署到 Azure VM，实现 7×24 小时监控
- [ ] 支持同时监控多个航班
- [ ] 增加历史记录功能
