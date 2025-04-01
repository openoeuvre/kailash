import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import mpld3
import time
import requests
from requests.exceptions import RequestException

__all__ = ['TradingStrategy']

class TradingStrategy:
    def __init__(self, initial_investment, shares_small_move, shares_large_move, consecutive_days, stock_symbol, start_date=None, end_date=None):
        self.initial_investment = initial_investment
        self.shares_small_move = shares_small_move
        self.shares_large_move = shares_large_move
        self.consecutive_days = consecutive_days
        self.stock_symbol = stock_symbol
        self.start_date = start_date
        self.end_date = end_date
        self.portfolio = {
            'cash': initial_investment,
            'shares': 0,
            'trades': []
        }
        
    def fetch_with_retry(self, ticker, start_date, end_date, max_retries=3):
        """Fetch data with retry logic"""
        for attempt in range(max_retries):
            try:
                print(f"Attempt {attempt + 1} to fetch data for {ticker}")
                # Create a new Ticker instance for each attempt
                stock = yf.Ticker(ticker)
                
                # Try to get info first to validate the ticker
                info = stock.info
                if not info:
                    print(f"No info available for {ticker}")
                    time.sleep(2)
                    continue
                
                # Fetch the data with a longer timeout
                df = stock.history(start=start_date, end=end_date, timeout=60)
                
                if not df.empty:
                    print(f"Successfully fetched {len(df)} rows for {ticker}")
                    return df
                else:
                    print(f"Empty dataframe returned for {ticker}")
                    time.sleep(2)
            except Exception as e:
                print(f"Error on attempt {attempt + 1} for {ticker}: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                continue
        return None
        
    def calculate_price_movement(self, stock_data, start_idx):
        """Calculate the percentage movement over consecutive days"""
        start_price = stock_data['Close'].iloc[start_idx]
        end_price = stock_data['Close'].iloc[start_idx + self.consecutive_days]
        return ((end_price - start_price) / start_price) * 100
        
    def get_shares_to_trade(self, price_movement):
        """Determine number of shares to trade based on price movement"""
        if abs(price_movement) >= 5:
            return self.shares_large_move
        return self.shares_small_move
        
    def get_historical_data(self):
        """Fetch historical data for the stock and S&P 500"""
        try:
            if self.start_date is None or self.end_date is None:
                # Default to 5 years if no dates provided
                end_date = datetime.now()
                start_date = end_date - timedelta(days=5*365)
            else:
                start_date = datetime.strptime(self.start_date, '%Y-%m-%d')
                end_date = datetime.strptime(self.end_date, '%Y-%m-%d')
            
            print(f"Fetching data for {self.stock_symbol} from {start_date} to {end_date}")
            
            # Get stock data with retry
            stock_df = self.fetch_with_retry(self.stock_symbol, start_date, end_date)
            if stock_df is None or stock_df.empty:
                print(f"No data returned for {self.stock_symbol}")
                return None, None, f'No data available for {self.stock_symbol}'
            
            print(f"Successfully fetched {len(stock_df)} days of stock data")
            
            # Get S&P 500 data with retry
            sp500_df = self.fetch_with_retry('^GSPC', start_date, end_date)
            if sp500_df is None or sp500_df.empty:
                print("No S&P 500 data returned")
                return None, None, 'Unable to fetch S&P 500 data'
            
            print(f"Successfully fetched {len(sp500_df)} days of S&P 500 data")
            return stock_df, sp500_df, None
            
        except Exception as e:
            print(f"Error in get_historical_data: {str(e)}")
            return None, None, f'Error fetching data: {str(e)}'
    
    def analyze(self):
        """Run the trading strategy analysis"""
        # Get historical data
        stock_data, sp500_data, error = self.get_historical_data()
        
        if stock_data is None or len(stock_data) == 0:
            return {'error': f'No data available for {self.stock_symbol}'}
            
        if sp500_data is None or len(sp500_data) == 0:
            return {'error': 'Unable to fetch S&P 500 data'}
        
        # Initialize variables
        consecutive_up_days = 0
        consecutive_down_days = 0
        last_price = None
        
        # Iterate through each day
        for i in range(len(stock_data) - self.consecutive_days):
            current_date = stock_data.index[i]
            current_price = stock_data['Close'].iloc[i]
            
            if last_price is not None:
                # Check if price increased or decreased
                if current_price > last_price:
                    consecutive_up_days += 1
                    consecutive_down_days = 0
                else:
                    consecutive_down_days += 1
                    consecutive_up_days = 0
                
                # Trading logic
                if consecutive_up_days >= self.consecutive_days:
                    # Calculate price movement
                    price_movement = self.calculate_price_movement(stock_data, i - self.consecutive_days + 1)
                    shares_to_trade = self.get_shares_to_trade(price_movement)
                    
                    # Sell if we have shares
                    if self.portfolio['shares'] > 0:
                        shares_to_sell = min(self.portfolio['shares'], shares_to_trade)
                        self.portfolio['cash'] += shares_to_sell * current_price
                        self.portfolio['shares'] -= shares_to_sell
                        self.portfolio['trades'].append({
                            'date': current_date.strftime('%Y-%m-%d'),
                            'action': 'SELL',
                            'shares': shares_to_sell,
                            'price': f'${current_price:.2f}',
                            'price_movement': f'{price_movement:.2f}%'
                        })
                
                elif consecutive_down_days >= self.consecutive_days:
                    # Calculate price movement
                    price_movement = self.calculate_price_movement(stock_data, i - self.consecutive_days + 1)
                    shares_to_trade = self.get_shares_to_trade(price_movement)
                    
                    # Buy if we have enough cash
                    shares_to_buy = min(
                        shares_to_trade,
                        int(self.portfolio['cash'] / current_price)
                    )
                    if shares_to_buy > 0:
                        cost = shares_to_buy * current_price
                        self.portfolio['cash'] -= cost
                        self.portfolio['shares'] += shares_to_buy
                        self.portfolio['trades'].append({
                            'date': current_date.strftime('%Y-%m-%d'),
                            'action': 'BUY',
                            'shares': shares_to_buy,
                            'price': f'${current_price:.2f}',
                            'price_movement': f'{price_movement:.2f}%'
                        })
            
            last_price = current_price
        
        # Calculate final portfolio value
        final_value = self.portfolio['cash'] + (self.portfolio['shares'] * last_price)
        
        # Calculate returns
        total_return = ((final_value - self.initial_investment) / self.initial_investment) * 100
        sp500_return = ((sp500_data['Close'].iloc[-1] - sp500_data['Close'].iloc[0]) / sp500_data['Close'].iloc[0]) * 100
        
        # Create performance plot
        portfolio_values = self.calculate_portfolio_value_over_time(stock_data)
        plot_html = self.create_performance_plot(stock_data, portfolio_values, sp500_data)
        
        return {
            'initial_investment': f'${self.initial_investment:,.2f}',
            'final_value': f'${final_value:,.2f}',
            'total_return': f'{total_return:.2f}%',
            'sp500_return': f'{sp500_return:.2f}%',
            'number_of_trades': len(self.portfolio['trades']),
            'last_trades': self.portfolio['trades'][-5:],
            'plot_html': plot_html,
            'all_trades': self.portfolio['trades']
        }
    
    def calculate_portfolio_value_over_time(self, stock_data):
        """Calculate portfolio value for each day"""
        portfolio_values = pd.DataFrame(index=stock_data.index)
        portfolio_values['value'] = self.initial_investment
        
        current_shares = 0
        current_cash = self.initial_investment
        consecutive_up_days = 0
        consecutive_down_days = 0
        last_price = None
        
        for i in range(len(stock_data)):
            current_date = stock_data.index[i]
            current_price = stock_data['Close'].iloc[i]
            
            if last_price is not None:
                # Check if price increased or decreased
                if current_price > last_price:
                    consecutive_up_days += 1
                    consecutive_down_days = 0
                else:
                    consecutive_down_days += 1
                    consecutive_up_days = 0
                
                # Trading logic
                if consecutive_up_days >= self.consecutive_days:
                    # Calculate price movement
                    price_movement = self.calculate_price_movement(stock_data, i - self.consecutive_days + 1)
                    shares_to_trade = self.get_shares_to_trade(price_movement)
                    
                    # Sell if we have shares
                    if current_shares > 0:
                        shares_to_sell = min(current_shares, shares_to_trade)
                        current_cash += shares_to_sell * current_price
                        current_shares -= shares_to_sell
                
                elif consecutive_down_days >= self.consecutive_days:
                    # Calculate price movement
                    price_movement = self.calculate_price_movement(stock_data, i - self.consecutive_days + 1)
                    shares_to_trade = self.get_shares_to_trade(price_movement)
                    
                    # Buy if we have enough cash
                    shares_to_buy = min(
                        shares_to_trade,
                        int(current_cash / current_price)
                    )
                    if shares_to_buy > 0:
                        cost = shares_to_buy * current_price
                        current_cash -= cost
                        current_shares += shares_to_buy
            
            # Update portfolio value for this day
            portfolio_values.loc[current_date, 'value'] = current_cash + (current_shares * current_price)
            last_price = current_price
        
        # Calculate percentage change from initial investment
        portfolio_values['pct_change'] = ((portfolio_values['value'] - self.initial_investment) / self.initial_investment) * 100
        return portfolio_values
    
    def create_performance_plot(self, stock_data, portfolio_values, sp500_data):
        """Create an interactive plot comparing strategy, S&P 500, and stock returns"""
        try:
            # Calculate S&P 500 performance
            sp500_performance = ((sp500_data['Close'] - sp500_data['Close'].iloc[0]) / sp500_data['Close'].iloc[0]) * 100
            
            # Calculate stock performance
            stock_performance = ((stock_data['Close'] - stock_data['Close'].iloc[0]) / stock_data['Close'].iloc[0]) * 100
            
            # Ensure dates are aligned
            common_dates = stock_data.index.intersection(sp500_data.index)
            portfolio_values = portfolio_values.loc[common_dates]
            sp500_performance = sp500_performance.loc[common_dates]
            stock_performance = stock_performance.loc[common_dates]
            
            fig = go.Figure()
            
            # Add portfolio return line
            fig.add_trace(go.Scatter(
                x=portfolio_values.index,
                y=portfolio_values['pct_change'],
                name='Strategy Return',
                line=dict(color='green')
            ))
            
            # Add S&P 500 return line
            fig.add_trace(go.Scatter(
                x=sp500_performance.index,
                y=sp500_performance,
                name='S&P 500 Return',
                line=dict(color='red', dash='dash')
            ))
            
            # Add stock return line
            fig.add_trace(go.Scatter(
                x=stock_performance.index,
                y=stock_performance,
                name=f'{self.stock_symbol} Return',
                line=dict(color='blue', dash='dot')
            ))
            
            fig.update_layout(
                title=f'Strategy vs S&P 500 vs {self.stock_symbol} Performance',
                xaxis_title='Date',
                yaxis_title='Return (%)',
                hovermode='x unified',
                showlegend=True
            )
            
            return fig.to_html(full_html=False)
        except Exception as e:
            print(f"Error creating plot: {str(e)}")
            return "<p>Error creating performance plot</p>" 