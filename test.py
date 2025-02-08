import ccxt
import pandas as pd
import ta
import secret
import time

def calculate_tr_atr(df, window=10):
    """Calculate TR and ATR with detailed logging"""
    print('\nCalculating TR and ATR...')
    try:
        # Calculate True Range
        df['previous_close'] = df['close'].shift(1)
        df['high-low'] = df['high'] - df['low']
        df['high-pc'] = abs(df['high'] - df['previous_close'])
        df['low-pc'] = abs(df['low'] - df['previous_close'])
        
        df['tr'] = df[['high-low', 'high-pc', 'low-pc']].max(axis=1)
        
        # Calculate ATR
        df['atr'] = df['tr'].rolling(window=window).mean()
        
        print('TR and ATR calculated successfully')
        print('\nSample of calculations:')
        print(df[['close', 'tr', 'atr']].head())
        return df
    except Exception as e:
        print(f'Error in TR/ATR calculation: {e}')
        raise

def calculate_supertrend(df, period=10, multiplier=3):
    """Calculate Supertrend with detailed logging"""
    print('\nCalculating Supertrend...')
    try:
        # Calculate basic bands
        df['basic_upperband'] = (df['high'] + df['low'])/2 + (multiplier * df['atr'])
        df['basic_lowerband'] = (df['high'] + df['low'])/2 - (multiplier * df['atr'])
        
        # Initialize trend columns
        df['in_uptrend'] = False
        df['supertrend'] = df['basic_upperband']
        
        # Calculate Supertrend
        for i in range(1, len(df)):
            if df['close'][i] > df['basic_upperband'][i-1]:
                df.loc[i, 'in_uptrend'] = True
            elif df['close'][i] < df['basic_lowerband'][i-1]:
                df.loc[i, 'in_uptrend'] = False
            else:
                df.loc[i, 'in_uptrend'] = df['in_uptrend'][i-1]
                
        print('Supertrend calculated successfully')
        print('\nSample of Supertrend results:')
        print(df[['close', 'in_uptrend']].tail())
        return df
    except Exception as e:
        print(f'Error in Supertrend calculation: {e}')
        raise

while True:
    try:
        print('\n=== Starting New Cycle ===')
        
        # 1. Connect to exchange
        exchange = ccxt.gateio({
            'apiKey': secret.GATEIO_API_KEY,
            'secret': secret.GATEIO_SECRET_KEY
        })
        print('Connected to exchange')
        
        # 2. Fetch data
        bars = exchange.fetch_ohlcv('BTC/USDT', timeframe='1m', limit=35)
        print(f'Fetched {len(bars)} bars')
        
        # 3. Create DataFrame
        df = pd.DataFrame(bars[:-1], columns=['timestamp','open','high','low','close','volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        print('Created DataFrame successfully')
        
        # 4. Calculate indicators
        df = calculate_tr_atr(df)
        df = calculate_supertrend(df)
        
        # 5. Check for signals
        current_price = df['close'].iloc[-1]
        current_trend = df['in_uptrend'].iloc[-1]
        
        print('\nCurrent Status:')
        print(f'Price: {current_price}')
        print(f'In Uptrend: {current_trend}')
        
    except Exception as e:
        print(f'Error occurred: {str(e)}')
    
    print('\nWaiting for next cycle...')
    time.sleep(60)