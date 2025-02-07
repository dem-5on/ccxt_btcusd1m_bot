import ccxt
import ta
import secret
import pandas as pd
import schedule
import time
import warnings 
warnings.filterwarnings('ignore')
import requests

while True:
    try:
        
        exchange = ccxt.binance({
            'apiKey':secret.BINANCE_API_KEY,
            'secret':secret.BINANCE_SECRET_KEY
        })
        server_time = exchange.fetch_time()
        symbol = 'BTC/USDT'

        def tr(df):
            #calculating for atr manually(instead of using ta library)
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


        def check_signal(ema_data,ha_data, s_data, multiplier=2, risk_reward_ratio=2):
            SIGNAL_MESSAGE = ('=====================================\n'
            'Checking for buy or sell signal\n\n')
            payload = {
                'username': 'alertbot',
                'content': SIGNAL_MESSAGE
            }
            WEBHOOK_URL = secret.DISCORD_WEBHOOK
            requests.post(WEBHOOK_URL, json=payload)

            try:
                # Fetch current market price
                ticker = exchange.fetch_ticker(symbol)
                current_price = ticker['last']

                # Fetch balance of USDT
                balance = exchange.fetch_balance(params={'type':'spot'})['total']['USDT']
                if balance <=1:
                    balance = 20

                # Calculate order size in USDT and convert it to the base currency
                order_size = balance * 0.5 if balance >= 100 else balance
                base_amount = round(order_size/current_price,6)

                # Improved amount calculation
                market = exchange.market(symbol)
                min_amount = market['limits']['amount']['min']
                precise_amount = exchange.amount_to_precision(symbol, base_amount)

                # Ensure amount meets minimum requirements
                if float(precise_amount) < float(min_amount):
                    precise_amount = min_amount

                # Get current trend state
                current_supertrend = s_data['in_uptrend'].iloc[-1]
                current_ha_trend = ha_data['ha_uptrend'].iloc[-1]
                current_ema_trend = ema_data['ema_uptrend'].iloc[-1]

                # Buy Signal Detection
                orders = exchange.fetch_open_orders(symbol)
                ORDER_MESSAGE = ('=====================================\n\n'
                f"Current Orders are: {orders}\n"
                f"Current market price is : {current_price}\n\n")
                
                payload = {
                    'username': 'alertbot',
                    'content': ORDER_MESSAGE
                }
                WEBHOOK_URL = secret.DISCORD_WEBHOOK
                requests.post(WEBHOOK_URL, json=payload)

                if orders==[]:
                    CHECK_BUY = ('\n\n================================\n'
                                     'Checking for buy signal...\n'
                                     '================================\n')
                    
                    payload = {
                        'username': 'alertbot',
                        'content': CHECK_BUY
                    }
                    WEBHOOK_URL = secret.DISCORD_WEBHOOK
                    requests.post(WEBHOOK_URL, json=payload)

                    #Buy conditions 
                    if current_ha_trend and current_supertrend and current_ema_trend:
                        UPTREND_MESSAGE = ('=====================================\n'
                        'Uptrend detected, Buy\n'
                        '=====================================\n')
                        
                        payload = {
                            'username': 'alertbot',
                            'content': UPTREND_MESSAGE
                        }
                        WEBHOOK_URL = secret.DISCORD_WEBHOOK
                        requests.post(WEBHOOK_URL, json=payload)

                        # Execute buy order
                        sl_distance = ha_data['ha_atr'] * multiplier
                        tp_distalce = sl_distance * risk_reward_ratio
                        long_tp =  current_price + tp_distalce
                        long_sl = current_price - sl_distance
                        params = {
                            'stopLoss': long_sl,  # limit price for a limit stop loss order
                            'takeProfit': long_tp
                        }
                        try:
                            # order = exchange.create_market_buy_order(symbol=symbol, amount=precise_amount, params=params)
                            order = exchange.create_order(
                                symbol=symbol,
                                type='MARKET',
                                side='BUY',
                                amount=precise_amount,
                                params=params
                            )
                            payload = {
                            'username': 'alertbot',
                            'content': order,
                            }
                            WEBHOOK_URL = secret.DISCORD_WEBHOOK
                            requests.post(WEBHOOK_URL, json=payload)
                        except Exception as e:
                            error_message = f"Order error: {e}"
                            # Log detailed error for debugging
                            payload = {
                                'username': 'alertbot',
                                'content': error_message
                            }
                            requests.post(secret.DISCORD_WEBHOOK, json=payload)

                        # Update trend state
                        s_data.loc[s_data.index[-1], 'in_uptrend'] = False
                        ha_data.loc[ha_data.index[-1], 'ha_uptrend']=False
                        ema_data.loc[ema_data.index[-1], 'ema_uptrend']=False

                        return 
                    else:
                        CHECK_SELL = ('\n\nNo buy signal detected\n'
                                      f'The trends are {current_supertrend} : {current_ha_trend} : {current_ema_trend}\n\n'
                                      '======================================\n'
                                      'Checking for SELL signal...\n'
                                      '======================================\n\n')
                        
                        payload = {
                            'username': 'alertbot',
                            'content': CHECK_SELL
                        }
                        WEBHOOK_URL = secret.DISCORD_WEBHOOK
                        requests.post(WEBHOOK_URL, json=payload)

                        # Sell Signal Conditions
                        if not current_ha_trend  and not current_supertrend and not current_ema_trend:
                            DOWN_TREND_MESSAGE = ('=====================================\n'
                                        'Downtrend detected, Sell\n'
                                        '=====================================\n'
                                        )
                            
                            payload = {
                                'username': 'alertbot',
                                'content': DOWN_TREND_MESSAGE
                            }
                            WEBHOOK_URL = secret.DISCORD_WEBHOOK

                            requests.post(WEBHOOK_URL, json=payload)


                            # Execute sell order
                            sl_distance = ha_data['ha_atr'] * multiplier
                            tp_distalce = sl_distance * risk_reward_ratio
                            short_tp =  current_price - tp_distalce
                            short_sl = current_price + sl_distance
                            params = {
                                'stopLoss': short_sl,  # limit price for a limit stop loss order
                                
                                'takeProfit': short_tp 
                            }                
                            try:
                                # order = exchange.create_market_sell_order(symbol=symbol, amount=precise_amount, params=params)
                                order = exchange.create_order(
                                symbol=symbol,
                                type='MARKET',
                                side='SELL',
                                amount=precise_amount,
                                params=params
                            )
                                payload = {
                                'username': 'alertbot',
                                'content': order,
                                }
                                WEBHOOK_URL = secret.DISCORD_WEBHOOK
                                requests.post(WEBHOOK_URL, json=payload)
                            except Exception as e:
                                error_message = f"Order error: {e}"
                                # Log detailed error for debugging
                                payload = {
                                    'username': 'alertbot',
                                    'content': error_message
                                }
                                requests.post(secret.DISCORD_WEBHOOK, json=payload)

                            # Reset trend state for next potential buy
                            s_data.loc[s_data.index[-1], 'in_uptrend'] = True
                            ha_data.loc[ha_data.index[-1], 'ha_uptrend']=True
                            ema_data.loc[ema_data.index[-1], 'ema_uptrrend']=True
                        else:
                            no_sell = ('No sell signal detected :'
                                       f'The trends are {current_supertrend} : {current_ha_trend} : {current_ema_trend}')
                            payload = {
                                'username': 'alertbot',
                                'content': no_sell,
                                }
                            WEBHOOK_URL = secret.DISCORD_WEBHOOK
                            requests.post(WEBHOOK_URL, json=payload)
                else:
                    order_available = f'There are orders : {orders}'
                    payload = {
                            'username': 'alertbot',
                            'content': order_available
                        }
                    WEBHOOK_URL = secret.DISCORD_WEBHOOK

                    requests.post(WEBHOOK_URL, json=payload)

            except Exception as e:
                error = f'An error occurred: {str(e)}'
                payload = {
                            'username': 'alertbot',
                            'content': error,
                        }
                WEBHOOK_URL = secret.DISCORD_WEBHOOK
                requests.post(WEBHOOK_URL, json=payload)
            return s_data


        def run():
            print('fetching market data')
            bars = exchange.fetch_ohlcv('BTC/USDT', timeframe='1m', limit=40)
            df = pd.DataFrame(bars[:-1], columns=['timestamp','open','high','low','close','volume'])
            df['timestamp']=pd.to_datetime(df['timestamp'], unit='ms')

            s_data = supertrend(df)
            ha_data = ha(df)
            ema_data = ema(df)
            check_signal(s_data,ha_data,ema_data)


    except ccxt.NetworkError as e:
        print(f'Network error: {e}')
    except ccxt.ExchangeError as e:
        print(f'Exchange error: {e}')
    except Exception as e:
        print(f'An unexpected error occured: {e}')

    time.sleep(60)

