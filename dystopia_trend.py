import ccxt
import ta
import secret
import pandas as pd
import time
import warnings 
warnings.filterwarnings('ignore')
import requests
import secret

# Dictionary to store active trades
active_trades = {}
symbol = 'BTC/USDT'

def update_trailing_stop(trade_id, current_price):
    """
    Update trailing stop based on current price movement
    """
    if trade_id not in active_trades:
        return None
    
    trade = active_trades[trade_id]
    entry_price = trade['entry_price']
    current_stop = trade['current_stop']
    highest_price = trade['highest_price']
    lowest_price = trade['lowest_price']
    
    if trade['side'] == 'BUY':
        # Update highest price if current price is higher
        if current_price > highest_price:
            trade['highest_price'] = current_price
            
            # Calculate price movement from entry
            price_movement = current_price - entry_price
            
            # If price has moved up by 25 points and stop is still at initial level
            if price_movement >= 25 and current_stop < entry_price:
                trade['current_stop'] = entry_price
            # After stop is at entry, move stop up every 25 points
            elif current_price >= (highest_price + 25):
                new_stop = current_price - 25
                if new_stop > current_stop:
                    trade['current_stop'] = new_stop
                    
    elif trade['side'] == 'SELL':
        # Update lowest price if current price is lower
        if current_price < lowest_price:
            trade['lowest_price'] = current_price
            
            # Calculate price movement from entry
            price_movement = entry_price - current_price
            
            # If price has moved down by 25 points and stop is still at initial level
            if price_movement >= 25 and current_stop > entry_price:
                trade['current_stop'] = entry_price
            # After stop is at entry, move stop down every 25 points
            elif current_price <= (lowest_price - 25):
                new_stop = current_price + 25
                if new_stop < current_stop:
                    trade['current_stop'] = new_stop
    
    return trade['current_stop']

def check_stop_hit(trade_id, current_price):
    """
    Check if current price has hit the trailing stop
    """
    if trade_id not in active_trades:
        return False
        
    trade = active_trades[trade_id]
    current_stop = trade['current_stop']
    
    if trade['side'] == 'BUY':
        return current_price <= current_stop
    else:
        return current_price >= current_stop

def place_trade(exchange, symbol, side, amount, price, ha_data, multiplier = 2):
    """
    Place trade and set up initial trailing stop
    """
    try:
        # Place the market order
        order = exchange.create_market_order(symbol, side, amount)
        
        # Generate unique trade ID
        trade_id = f"{symbol}-{order['id']}"
        
        # Calculate initial stop (5 points from entry)
        sl_distance = ha_data['ha_atr'] * multiplier
        initial_stop = price - sl_distance if side == 'BUY' else price + sl_distance
        
        # Store trade information
        active_trades[trade_id] = {
            'symbol': symbol,
            'side': side,
            'entry_price': price,
            'amount': amount,
            'current_stop': initial_stop,
            'highest_price': price,
            'lowest_price': price,
            'order_id': order['id']
        }
        
        return trade_id
        
    except Exception as e:
        trade_error = f"Error placing trade: {e}"
        payload = {
                'username': 'alertbot',
                'content': trade_error
            }
        WEBHOOK_URL = secret.DISCORD_WEBHOOK
        requests.post(WEBHOOK_URL, json=payload)

        return None

def close_trade(exchange, trade_id):
    """
    Close trade and clean up
    """
    if trade_id not in active_trades:
        return
        
    trade = active_trades[trade_id]
    try:
        # Place closing market order
        side = 'SELL' if trade['side'] == 'BUY' else 'BUY'
        exchange.create_market_order(trade['symbol'], side, trade['amount'])
        
        # Remove trade from active trades
        del active_trades[trade_id]
        
    except Exception as e:
        trade_error = f"Error placing trade: {e}"
        payload = {
                'username': 'alertbot',
                'content': trade_error
            }
        WEBHOOK_URL = secret.DISCORD_WEBHOOK
        requests.post(WEBHOOK_URL, json=payload)


def check_signal(exchange, symbol, ema_data, ha_data, s_data):
    """
    Modified check_signal function to use trailing stops
    """
    try:
        # Fetch current market price
        ticker = exchange.fetch_ticker(symbol)
        current_price = ticker['last']
        
        # Check existing trades first
        for trade_id in list(active_trades.keys()):
            # Update trailing stop
            update_trailing = 'Updating Trailing stop...'
            payload = {
                'username': 'alertbot',
                'content': update_trailing
            }
            WEBHOOK_URL = secret.DISCORD_WEBHOOK
            requests.post(WEBHOOK_URL, json=payload)
            update_trailing_stop(trade_id, current_price)
            
            # # Check if stop is hit
            # if check_stop_hit(symbol, trade_id, current_price):
            #     close_trade(exchange, trade_id)
            #     continue
        
        # Get current trend state
        current_supertrend = s_data['in_uptrend'].iloc[-1]
        current_ha_trend = ha_data['ha_uptrend'].iloc[-1]
        current_ema_trend = ema_data['ema_uptrend'].iloc[-1]
        
        # Calculate trading amount
        balance = exchange.fetch_balance()['total']['USDT']
        order_size = balance * 0.5 if balance >= 100 else balance
        amount = order_size / current_price
        
        # Check for new trade signals
        if not active_trades:  # Only check for new trades if no active trades
            if current_ha_trend and current_supertrend and current_ema_trend:
                up_trend = ('Uptrend detected, Buy\n'
                            f'The current trends are : {current_supertrend} : {current_ha_trend} : {current_ema_trend}')
                payload = {
                'username': 'alertbot',
                'content': up_trend
                }
                WEBHOOK_URL = secret.DISCORD_WEBHOOK
                requests.post(WEBHOOK_URL, json=payload)

                # Buy signal
                trade_id = place_trade(exchange, symbol, 'BUY', amount, current_price, ha_data)
                if trade_id:
                    open_long = f"Opened long position: {trade_id}"
                    payload = {
                        'username': 'alertbot',
                        'content': open_long
                    }
                    WEBHOOK_URL = secret.DISCORD_WEBHOOK
                    requests.post(WEBHOOK_URL, json=payload)
                    
            # elif not current_ha_trend and not current_supertrend and not current_ema_trend:
            #     Down_trend = ('Down trend detected, Sell\n'
            #                 f'The trend is: {current_supertrend} : {current_ha_trend} : {current_ema_trend}')
            #     payload = {
            #     'username': 'alertbot',
            #     'content': Down_trend
            #     }
            #     WEBHOOK_URL = secret.DISCORD_WEBHOOK
            #     requests.post(WEBHOOK_URL, json=payload)

            #     # Sell signal
            #     trade_id = place_trade(exchange, symbol, 'SELL', amount, current_price, ha_data)
            #     if trade_id:
            #         open_short = f"Opened short position: {trade_id}"
            #         payload = {
            #         'username': 'alertbot',
            #         'content': open_short
            #         }
            #         WEBHOOK_URL = secret.DISCORD_WEBHOOK
            #         requests.post(WEBHOOK_URL, json=payload)
            else:
                no_signal =('No signal was detected\n'
                            f'Current trends are: {current_supertrend} : {current_ha_trend} : {current_ema_trend}') 
                payload = {
                'username': 'alertbot',
                'content': no_signal
                }
                WEBHOOK_URL = secret.DISCORD_WEBHOOK
                requests.post(WEBHOOK_URL, json=payload)

    except Exception as e:
        error = f"Error in check_signal: {e}"
        payload = {
                'username': 'alertbot',
                'content': error
            }
        WEBHOOK_URL = secret.DISCORD_WEBHOOK
        requests.post(WEBHOOK_URL, json=payload)

def tr(df):
    print('calculating tr')
    df['previous_close'] = df['close'].shift(1)
    df['high-low'] =  df['high'] - df['low']
    df['high-pc'] = df['high'] - df['previous_close']
    df['low-pc'] = df['low'] - df['previous_close']

    tr = df[['high-low','high-pc', 'low-pc']].max(axis=1)
    return tr

def atr(df,window=10):
    df['tr'] = tr(df)
    print(f'Calculate the value for atr')
    atr = df['tr'].rolling(window=window).mean()
    df['atr'] = atr

    return atr

def supertrend(df, window=10, multiplier=3):
    print('Calculating super trend...')
    df['atr'] = atr(df,window=window)

    #calculating the basic_upperband
    df['upperband'] = (df['high']  + df['low'])/2 + (multiplier * df['atr'])
    #calculating the basic lowerband
    df['lowerband'] = (df['high']  + df['low'])/2 - (multiplier * df['atr'])

    df['in_uptrend'] = False
    for current in range(1, len(df.index)):
        previous = current - 1 

        if df['close'][current] > df['upperband'][previous]:
            df['in_uptrend'][current]=True

        elif df['close'][previous] < df['lowerband'][previous]:
            df['in_uptrend'][current]=False

        else:
            df['in_uptrend'][current] = df['in_uptrend'][previous]
            if df['in_uptrend'][current] and df['lowerband'][current] < df['lowerband'][previous]:
                df['lowerband'][current] = df['lowerband'][previous]
            if not df['in_uptrend'][current] and df['upperband'][current] > df['upperband'][previous]:
                df['upperband'][current] = df['upperband'][previous]
    return df

def ha(df, period=14, threshold=0.0001):
    print('Calculating heikin ashi(ha)')
    # Calculate Heikin-Ashi components
    df['ha_close'] = (df['open'] + df['high'] + df['low'] + df['close'])/4
    
    # Initialize ha_open with the first value
    df['ha_open'] = 0.0
    df.loc[0, 'ha_open'] = (df['open'].iloc[0] + df['close'].iloc[0])/2
    
    # Calculate ha_open recursively
    for i in range(1, len(df)):
        df.loc[i, 'ha_open'] = (df['ha_open'].iloc[i-1] + df['ha_close'].iloc[i-1])/2
    
    # Calculate high and low and previous close
    df['ha_previous_close'] = df['close'].shift(1)
    df['ha_high'] = df[['high', 'ha_open', 'ha_close']].max(axis=1)
    df['ha_low'] = df[['low', 'ha_open', 'ha_close']].min(axis=1)
    
    # Calculate true range
    df['previous_close'] = df['ha_close'].shift(1)
    df['high-low'] = df['ha_high'] - df['ha_low']
    df['high-pc'] = df['ha_high'] - df['ha_previous_close']
    df['low-pc'] = df['ha_low'] - df['ha_previous_close']
    
    df['ha_tr'] = df[['high-low', 'high-pc', 'low-pc']].max(axis=1)
    
    # Calculate ATR
    df['ha_atr'] = df['ha_tr'].rolling(window=period).mean()
    
    # Initialize ha_uptrend column
    df['ha_uptrend'] = False
    
    # Calculate trend for each row
    for i in range(len(df)):
        if (df['ha_close'].iloc[i] > df['ha_open'].iloc[i] and 
            abs(df['ha_open'].iloc[i] - df['ha_low'].iloc[i]) <= threshold):
            df.loc[i, 'ha_uptrend'] = True
        elif (df['ha_close'].iloc[i] < df['ha_open'].iloc[i] and 
            abs(df['ha_open'].iloc[i] - df['ha_high'].iloc[i]) <= threshold):
            df.loc[i, 'ha_uptrend'] = False
    
    return df


def ema(df):            
    df['ema_5'] = ta.trend.EMAIndicator(df['close'], window=5).ema_indicator()
    df['ema_10'] = ta.trend.EMAIndicator(df['close'], window=10).ema_indicator()
    df['ema_30'] = ta.trend.EMAIndicator(df['close'], window=30).ema_indicator()
    
    df['ema_uptrend'] = (df['ema_5'] > df['ema_10']) & (df['ema_10'] > df['ema_30'])
    return df

def run():
    """
    Modified run function
    """
    print('fetching market data')
    bars = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=35)
    df = pd.DataFrame(bars[:-1], columns=['timestamp','open','high','low','close','volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

    s_data = supertrend(df)
    ha_data = ha(df)
    ema_data = ema(df)
    check_signal(exchange, symbol, ema_data, ha_data, s_data)

# Main loop
while True:
    try:
        exchange = ccxt.binance({
            'apiKey': secret.BINANCE_API_KEY,
            'secret': secret.BINANCE_SECRET_KEY
        })
        run()
    except ccxt.NetworkError as e:
        network = f'Network error: {e}'
        payload = {
                'username': 'alertbot',
                'content': network
            }
        WEBHOOK_URL = secret.DISCORD_WEBHOOK
        requests.post(WEBHOOK_URL, json=payload)

    except ccxt.ExchangeError as e:
        exchangeerror = (f'Exchange error: {e}')
        payload = {
                'username': 'alertbot',
                'content': exchangeerror
            }
        WEBHOOK_URL = secret.DISCORD_WEBHOOK
        requests.post(WEBHOOK_URL, json=payload)

    except Exception as e:
        excep_tion = f'An unexpected error occurred: {e}'
        payload = {
                'username': 'alertbot',
                'content': excep_tion
            }
        WEBHOOK_URL = secret.DISCORD_WEBHOOK
        requests.post(WEBHOOK_URL, json=payload)

    
    time.sleep(900)