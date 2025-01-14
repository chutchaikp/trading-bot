import json
import logging
from flask import Flask, request
import MetaTrader5 as mt5

# Initialize the Flask application
app = Flask(__name__)

# Set up logging
logging.basicConfig(filename="webhook_bot.log", level=logging.INFO)

# Function to initialize MT5 connection
def initialize_mt5():
    if not mt5.initialize():
        logging.error("MetaTrader5 initialization failed.")
        return False

    # Check if MT5 is connected to the broker
    if not mt5.terminal_info().connected:
        logging.error("MetaTrader5 is not connected to the broker.")
        return False

    return True

# Function to close positions for a symbol (supports closing partial positions)
def close_positions(symbol, position_type, volume=None):
    positions = mt5.positions_get(symbol=symbol)
    if not positions:
        logging.info(f"No open positions to close for {symbol}.")
        return {"status": "success", "message": f"No open positions to close for {symbol}."}

    for position in positions:
        if position.type == position_type:  # 0 = BUY, 1 = SELL
            # If volume is provided, close only part of the position
            close_volume = volume if volume and volume <= position.volume else position.volume
            close_price = mt5.symbol_info_tick(symbol).bid if position_type == 0 else mt5.symbol_info_tick(symbol).ask
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": close_volume,
                "type": mt5.ORDER_SELL if position_type == 0 else mt5.ORDER_BUY,
                "price": close_price,
                "deviation": 10,
                "position": position.ticket,
                "magic": 123456,
                "comment": f"Close position via webhook bot (partial volume: {close_volume})",
            }
            result = mt5.order_send(request)
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logging.error(f"Failed to close position {position.ticket}: {result.comment}")
                return {"status": "error", "message": f"Failed to close position {position.ticket}: {result.comment}"}
            logging.info(f"Closed position {position.ticket} successfully (Volume: {close_volume}).")
    return {"status": "success", "message": f"Closed all {'long' if position_type == 0 else 'short'} positions for {symbol}."}

# Function to send trade signals to MT5
def send_order(signal, symbol, lot_size, stop_loss=None, take_profit=None):
    deviation = 10  # Allowed price deviation in points
    price = None  # Default price

    # Get the current price
    symbol_info = mt5.symbol_info_tick(symbol)
    if not symbol_info:
        logging.error(f"Symbol {symbol} not found.")
        return {"status": "error", "message": f"Symbol {symbol} not found."}

    # Determine order type and price
    if signal == "buy":
        order_type = mt5.ORDER_BUY
        price = symbol_info.ask
    elif signal == "sell":
        order_type = mt5.ORDER_SELL
        price = symbol_info.bid
    elif signal == "closelong":
        return close_positions(symbol, position_type=0)  # 0 = BUY positions
    elif signal == "closeshort":
        return close_positions(symbol, position_type=1)  # 1 = SELL positions
    else:
        return {"status": "error", "message": "Unsupported signal type."}

    # Create the order request
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot_size,
        "type": order_type,
        "price": price,
        "deviation": deviation,
        "magic": 123456,  # Custom identifier for the bot
        "comment": f"{signal.capitalize()} order via webhook bot",
    }

    if stop_loss:
        request["sl"] = stop_loss
    if take_profit:
        request["tp"] = take_profit

    # Send the order
    result = mt5.order_send(request)

    # Log and return the result
    if result.retcode == mt5.TRADE_RETCODE_DONE:
        logging.info(f"{signal.capitalize()} order executed successfully. Order ID: {result.order}")
        return {"status": "success", "message": f"{signal.capitalize()} order executed.", "order_id": result.order}
    else:
        logging.error(f"Order failed: {result.comment}")
        return {"status": "error", "message": f"Order failed: {result.comment}"}

# Webhook endpoint to receive signals from TradingView
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    logging.info(f"Received data: {data}")

    # Parse parameters from the incoming request
    signal = data.get("signal", "").lower()
    symbol = data.get("symbol", "XAUUSDm").upper()  # Default to XAUUSDm if not provided
    lot_size = data.get("lot_size", 0.03)  # Default to 0.03 lot if not provided
    stop_loss = data.get("stop_loss")
    take_profit = data.get("take_profit")
    volume = data.get("volume")

    # Validate the signal
    if signal in ["buy", "sell", "closelong", "closeshort"]:
        if initialize_mt5():
            result = send_order(signal, symbol, lot_size, stop_loss, take_profit)
            if signal in ["closelong", "closeshort"] and volume:
                # If closing positions, pass the volume for partial closure
                result = close_positions(symbol, position_type=0 if signal == "closelong" else 1, volume=volume)
            return json.dumps(result)
        else:
            return json.dumps({"status": "error", "message": "MT5 connection failed."})
    else:
        return json.dumps({"status": "error", "message": "Invalid signal."})

# Run the application
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)