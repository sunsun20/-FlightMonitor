# 航班状态监控工具

查询航班实时状态，航班取消/延误时自动发送 Telegram 通知。

---

## 项目结构

```
FlightMonitor/
├── app.py              # 后端主程序
├── config.py           # 配置文件（API Key、Telegram 等，不上传 GitHub）
├── config.example.py   # 配置模板（上传 GitHub 用）
├── requirements.txt    # Python 依赖
├── templates/
│   └── index.html      # 前端页面（NES.css 像素风格）
└── venv/               # Python 虚拟环境（不需要动）
```

---

## 部署方式（Azure VM + Tailscale，推荐）

### 已部署位置

- **VM**：`vm-talos-cicd-01`（Southeast Asia）
- **访问地址**：`http://100.69.178.121:5002`（Tailscale 内网）
- **服务管理**：systemd，VM 重启后自动启动

### 手机访问

1. iPhone 安装 Tailscale App，登录同一账号
2. 保持 Tailscale 开启
3. Safari 打开 `http://100.69.178.121:5002`

### VM 上管理服务

```bash
# 查看状态
sudo systemctl status flightmonitor

# 停止服务
sudo systemctl stop flightmonitor

# 启动服务
sudo systemctl start flightmonitor

# 永久禁用（重启后不自动启动）
sudo systemctl disable flightmonitor
```

---

## 本地开发启动

```bash
cd ~/Downloads/自创app/FlightMonitor
venv/bin/python app.py
```

访问：**http://localhost:5002**

---

## 使用方法

### 查询航班状态

1. 填入航班号，例如 `EK306`
2. 选择出发日期
3. 点击「**▶ 查询**」

显示信息包括：
- 航班状态（计划中 / 飞行中 / 已降落 / 已取消 / 延误）
- 出发机场、**航站楼**、登机口、计划/实际起飞时间
- 到达机场、航站楼、登机口、计划/预计到达时间
- 延误分钟数（红色显示）
- 行李转盘（落地后）

### 开始自动监控

1. 填好航班号和日期，点击「**◉ 开始监控**」
2. 每 **10 分钟**自动检查一次
3. 状态变化时（取消/延误）**Telegram 立即通知**

> 航班数据通常在起飞前 1-2 天进入系统，太早查询会显示"未找到数据"，属正常现象。

### Telegram Bot 使用

直接在 Telegram 给 Bot 发消息：

| 发送内容 | 效果 |
|----------|------|
| `EK306` | 查询今天的 EK306 |
| `EK306 2026-03-13` | 查询指定日期 |
| 发截图（机票/订单） | 自动 OCR 识别航班号和日期，确认后查询 |

截图识别流程：
1. 发送机票截图给 Bot
2. Bot 识别后回复：「识别到：✈️ EK306 📅 2026-03-13，发送「确认」查询，或「取消」」
3. 发「确认」即可查询

---

## 配置说明

配置文件 `config.py`（不提交到 GitHub，复制 `config.example.py` 修改）：

| 参数 | 说明 |
|------|------|
| `AVIATIONSTACK_API_KEY` | 航班数据 API Key（aviationstack.com 免费注册） |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token（从 @BotFather 获取） |
| `TELEGRAM_CHAT_ID` | 你的 Telegram 用户 ID |
| `CHECK_INTERVAL_MINUTES` | 监控检查间隔，默认 10 分钟 |
| `DEEPSEEK_API_KEY` | DeepSeek API Key（截图识别用，deepseek.com 注册） |

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
A：航班数据通常起飞前 1-2 天才入库，提前太多查不到是正常的。

**Q：Telegram 没有收到通知？**
A：确认已经给 Bot 发过消息（必须先主动发消息，Bot 才能给你推送）。

**Q：手机访问不了？**
A：确认 iPhone 上 Tailscale 已开启并登录同一账号。

---

## 后续计划

- [x] 部署到 Azure VM，实现 7×24 小时监控
- [x] Tailscale 内网访问，无需公网 IP
- [x] Telegram Bot 文字查询（EK306 或 EK306 2026-03-13）
- [x] 截图识别（OCR + DeepSeek AI 解析航班信息）
- [ ] 支持同时监控多个航班
- [ ] 增加历史记录功能
