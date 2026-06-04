from flask import Flask, render_template, request, jsonify
import yfinance as yf
import json
import google.generativeai as genai


app = Flask(__name__)
genai.configure(api_key="AQ.Ab8RN6JVpWvwb1kdbQpj6ryZzzMw52CY5qYLRUgytAiHXykkvw")


# In memory portfolio and alerts storage
portfolio = {}
alerts = []

@app.route("/")
def home():
    return render_template("index.html")

# ============ STOCK ANALYSIS ============
@app.route("/analyze", methods=["POST"])
def analyze():
    try:
        symbol = request.json.get("symbol").upper().strip()
        stock = yf.Ticker(symbol)
        data = stock.history(period="1mo")
        info = stock.info

        if data.empty:
            return jsonify({"error": "Stock not found!"})

        current_price = round(data['Close'].iloc[-1], 2)
        prev_price = round(data['Close'].iloc[-2], 2)
        change = round(current_price - prev_price, 2)
        change_pct = round((change / prev_price) * 100, 2)
        avg_price = data['Close'].mean()

        if current_price < avg_price * 0.95:
            signal = "BUY"
            reason = "Price is below average - good entry point!"
            color = "green"
        elif current_price > avg_price * 1.05:
            signal = "SELL"
            reason = "Price is above average - consider exit!"
            color = "red"
        else:
            signal = "HOLD"
            reason = "Price near average - wait and watch!"
            color = "orange"

        dates = data.index.strftime('%d %b').tolist()
        prices = [round(p, 2) for p in data['Close'].tolist()]

        return jsonify({
            "symbol": symbol,
            "company": info.get('longName', symbol),
            "current_price": current_price,
            "change": change,
            "change_pct": change_pct,
            "high": round(data['Close'].max(), 2),
            "low": round(data['Close'].min(), 2),
            "avg": round(avg_price, 2),
            "volume": info.get('volume', 'N/A'),
            "signal": signal,
            "reason": reason,
            "color": color,
            "dates": dates,
            "prices": prices
        })
    except Exception as e:
        return jsonify({"error": str(e)})

# ============ AI CHATBOT ============
@app.route("/chat", methods=["POST"])
def chat():
    try:
        message = request.json.get("message")
        language = request.json.get("language", "english")

        if language == "telugu":
            prompt = f"""మీరు స్టాక్ మార్కెట్ మరియు 
            ఫైనాన్స్ నిపుణుడు. తెలుగులో సమాధానం 
            ఇవ్వండి: {message}"""
        else:
            prompt = f"""You are a stock market and 
            finance expert for Indian markets.
            Answer clearly and simply: {message}"""

        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)

        return jsonify({"response": response.text})
    except Exception as e:
        return jsonify({"error": str(e)})

# ============ PORTFOLIO ============
@app.route("/portfolio/add", methods=["POST"])
def add_to_portfolio():
    try:
        symbol = request.json.get("symbol").upper()
        quantity = float(request.json.get("quantity"))
        buy_price = float(request.json.get("buy_price"))

        stock = yf.Ticker(symbol)
        data = stock.history(period="1d")

        if data.empty:
            return jsonify({"error": "Stock not found!"})

        current_price = round(data['Close'].iloc[-1], 2)
        invested = round(quantity * buy_price, 2)
        current_value = round(quantity * current_price, 2)
        pnl = round(current_value - invested, 2)
        pnl_pct = round((pnl / invested) * 100, 2)

        portfolio[symbol] = {
            "symbol": symbol,
            "quantity": quantity,
            "buy_price": buy_price,
            "current_price": current_price,
            "invested": invested,
            "current_value": current_value,
            "pnl": pnl,
            "pnl_pct": pnl_pct
        }

        return jsonify({"success": True, "portfolio": list(portfolio.values())})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/portfolio/get", methods=["GET"])
def get_portfolio():
    try:
        total_invested = sum(s["invested"] for s in portfolio.values())
        total_value = sum(s["current_value"] for s in portfolio.values())
        total_pnl = round(total_value - total_invested, 2)
        total_pnl_pct = round((total_pnl / total_invested * 100) if total_invested > 0 else 0, 2)

        return jsonify({
            "stocks": list(portfolio.values()),
            "total_invested": round(total_invested, 2),
            "total_value": round(total_value, 2),
            "total_pnl": total_pnl,
            "total_pnl_pct": total_pnl_pct
        })
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/portfolio/remove", methods=["POST"])
def remove_from_portfolio():
    symbol = request.json.get("symbol").upper()
    if symbol in portfolio:
        del portfolio[symbol]
    return jsonify({"success": True, "portfolio": list(portfolio.values())})

# ============ ALERTS ============
@app.route("/alerts/add", methods=["POST"])
def add_alert():
    try:
        symbol = request.json.get("symbol").upper()
        target_price = float(request.json.get("target_price"))
        alert_type = request.json.get("alert_type")

        alert = {
            "id": len(alerts) + 1,
            "symbol": symbol,
            "target_price": target_price,
            "alert_type": alert_type,
            "status": "active"
        }
        alerts.append(alert)
        return jsonify({"success": True, "alerts": alerts})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/alerts/check", methods=["GET"])
def check_alerts():
    try:
        triggered = []
        for alert in alerts:
            if alert["status"] != "active":
                continue
            stock = yf.Ticker(alert["symbol"])
            data = stock.history(period="1d")
            if data.empty:
                continue
            current_price = round(data['Close'].iloc[-1], 2)
            if alert["alert_type"] == "above" and current_price >= alert["target_price"]:
                alert["status"] = "triggered"
                triggered.append({**alert, "current_price": current_price})
            elif alert["alert_type"] == "below" and current_price <= alert["target_price"]:
                alert["status"] = "triggered"
                triggered.append({**alert, "current_price": current_price})
        return jsonify({"triggered": triggered, "all_alerts": alerts})
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == "__main__":
    app.run(debug=True)