# 🧠 Dystopia Trend Bot

A cryptocurrency trading bot for Binance that utilizes a combination of technical indicators—including **Supertrend**, **Heikin Ashi**, and **Exponential Moving Averages (EMAs)**—to detect trends and automatically place trades. The bot features **dynamic trailing stops**, **risk-managed entries**, and **Discord alerts** for transparency.

---

## 📌 Features

* 📈 **Multi-indicator strategy** (Supertrend, Heikin Ashi, EMA)
* 🧠 **Automated trading on Binance** using [CCXT](https://github.com/ccxt/ccxt)
* 🔁 **Dynamic trailing stop-loss** system for better risk management
* 📊 **Real-time 15-minute OHLCV data** used for analysis
* 💬 **Discord Webhook integration** for instant trade alerts
* ⚙️ Fully modular and extensible Python structure

---

## 🛠️ Installation

```bash
git clone https://github.com/yourusername/dystopia-trend-bot.git
cd dystopia-trend-bot
pip install -r requirements.txt
```

### Dependencies

* `ccxt`
* `ta`
* `pandas`
* `requests`

---

## 🔐 Setup

Create a file named `secret.py` in the root of your project directory:

```python
BINANCE_API_KEY = "your_binance_api_key"
BINANCE_SECRET_KEY = "your_binance_secret_key"
DISCORD_WEBHOOK = "your_discord_webhook_url"
```

---

## 🚀 How It Works

1. **Fetches market data** (15m timeframe) from Binance using `ccxt`.
2. **Calculates indicators**:

   * 📉 **Supertrend**
   * 🔴 **Heikin Ashi trend strength**
   * 🔵 **EMA crossovers**
3. If all three indicators align in trend direction:

   * Places a **market trade**
   * Sets up an **initial stop-loss**
   * Dynamically adjusts the **trailing stop**
4. Sends **alerts** to your Discord server on trade signals and events.
5. **Continuously runs** in 15-minute intervals.

---

## 🧪 Example Alert Messages (Discord)

```
📢 Uptrend detected, Buy
The current trends are: True : True : True

📈 Opened long position: BTC/USDT-123456

🔁 Updating Trailing stop...
```

---

## 📂 File Structure

```
.
├── dystopia_trend.py    # Main bot logic
├── secret.py            # API keys and Discord webhook
├── README.md            # This file
```

---

## 📅 Future Improvements

* Add backtesting module
* Implement sell-side logic (currently commented out)
* Improve exception handling and logging
* Add GUI dashboard

---

## ⚠️ Disclaimer

> This bot is for **educational and experimental purposes** only. Cryptocurrency trading involves significant risk. Use at your own discretion and responsibility.

---

## 🧑‍💻 Author

**dem-5on**
For support or feature requests, open an issue or contact via GitHub.
