import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import mpld3

__all__ = ['TradingStrategy']

class TradingStrategy:
    def __init__(self, initial_investment, shares_per_trade, consecutive_days, stock_symbol, start_date=None, end_date=None):
        self.initial_investment = initial_investment
        self.shares_per_trade = shares_per_trade
        self.consecutive_days = consecutive_days
        self.stock_symbol = stock_symbol
        self.start_date = start_date
        self.end_date = end_date
        self.portfolio = {
            'cash': initial_investment,
            'shares': 0,
            'trades': []
        }
        
    def get_historical_data(self):
        """Fetch historical data for the stock and S&P 500"""
        if self.start_date is None or self.end_date is None:
            # Default to 5 years if no dates provided
            end_date = datetime.now()
            start_date = end_date - timedelta(days=5*365)
        else:
            start_date = datetime.strptime(self.start_date, '%Y-%m-%d')
            end_date = datetime.strptime(self.end_date, '%Y-%m-%d')
        
        # Get stock data
        stock = yf.Ticker(self.stock_symbol)
        stock_df = stock.history(start=start_date, end=end_date)
        
        # Get S&P 500 data
        sp500 = yf.Ticker('^GSPC')
        sp500_df = sp500.history(start=start_date, end=end_date)
        
        return stock_df, sp500_df
    
    def analyze(self):
        """Run the trading strategy analysis"""
        # Get historical data
        stock_data, sp500_data = self.get_historical_data()
        
        if stock_data.empty or len(stock_data) == 0:
            return {'error': f'No data available for {self.stock_symbol}'}
            
        if sp500_data.empty or len(sp500_data) == 0:
            return {'error': 'Unable to fetch S&P 500 data'}
        
        # Initialize variables
        consecutive_up_days = 0
        consecutive_down_days = 0
        last_price = None
        
        # Iterate through each day
        for date, row in stock_data.iterrows():
            current_price = row['Close']
            
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
                    # Sell if we have shares
                    if self.portfolio['shares'] > 0:
                        shares_to_sell = min(self.portfolio['shares'], self.shares_per_trade)
                        self.portfolio['cash'] += shares_to_sell * current_price
                        self.portfolio['shares'] -= shares_to_sell
                        self.portfolio['trades'].append({
                            'date': date.strftime('%Y-%m-%d'),
                            'action': 'SELL',
                            'shares': shares_to_sell,
                            'price': f'${current_price:.2f}'
                        })
                
                elif consecutive_down_days >= self.consecutive_days:
                    # Buy if we have enough cash
                    shares_to_buy = min(
                        self.shares_per_trade,
                        int(self.portfolio['cash'] / current_price)
                    )
                    if shares_to_buy > 0:
                        cost = shares_to_buy * current_price
                        self.portfolio['cash'] -= cost
                        self.portfolio['shares'] += shares_to_buy
                        self.portfolio['trades'].append({
                            'date': date.strftime('%Y-%m-%d'),
                            'action': 'BUY',
                            'shares': shares_to_buy,
                            'price': f'${current_price:.2f}'
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
            'plot_html': plot_html
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
        
        for date, row in stock_data.iterrows():
            current_price = row['Close']
            
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
                    # Sell if we have shares
                    if current_shares > 0:
                        shares_to_sell = min(current_shares, self.shares_per_trade)
                        current_cash += shares_to_sell * current_price
                        current_shares -= shares_to_sell
                
                elif consecutive_down_days >= self.consecutive_days:
                    # Buy if we have enough cash
                    shares_to_buy = min(
                        self.shares_per_trade,
                        int(current_cash / current_price)
                    )
                    if shares_to_buy > 0:
                        cost = shares_to_buy * current_price
                        current_cash -= cost
                        current_shares += shares_to_buy
            
            # Update portfolio value for this day
            portfolio_values.loc[date, 'value'] = current_cash + (current_shares * current_price)
            last_price = current_price
        
        portfolio_values['pct_change'] = ((portfolio_values['value'] - self.initial_investment) / self.initial_investment) * 100
        return portfolio_values
    
    def create_performance_plot(self, stock_data, portfolio_values, sp500_data):
        """Create an interactive plot comparing strategy and S&P 500 returns"""
        try:
            # Calculate S&P 500 performance
            sp500_performance = ((sp500_data['Close'] - sp500_data['Close'].iloc[0]) / sp500_data['Close'].iloc[0]) * 100
            
            # Ensure dates are aligned
            common_dates = stock_data.index.intersection(sp500_data.index)
            portfolio_values = portfolio_values.loc[common_dates]
            sp500_performance = sp500_performance.loc[common_dates]
            
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
            
            fig.update_layout(
                title=f'Strategy vs S&P 500 Performance',
                xaxis_title='Date',
                yaxis_title='Return (%)',
                hovermode='x unified',
                showlegend=True
            )
            
            return fig.to_html(full_html=False)
        except Exception as e:
            print(f"Error creating plot: {str(e)}")
            return "<p>Error creating performance plot</p>" 