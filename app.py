from flask import Flask, render_template, request, jsonify
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from trading_strategy import TradingStrategy
import os

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        # Get form data
        initial_investment = float(request.form['initial_investment'])
        shares_per_trade = int(request.form['shares_per_trade'])
        consecutive_days = int(request.form['consecutive_days'])
        stock_symbol = request.form['stock_symbol'].upper()
        
        # Create strategy instance
        strategy = TradingStrategy(
            initial_investment=initial_investment,
            shares_per_trade=shares_per_trade,
            consecutive_days=consecutive_days,
            stock_symbol=stock_symbol
        )
        
        # Run analysis
        results = strategy.analyze()
        
        return jsonify({
            'initial_investment': f"${initial_investment:,.2f}",
            'final_value': f"${results['final_value']:,.2f}",
            'total_return': f"{results['total_return']:.2f}%",
            'sp500_return': f"{results['sp500_return']:.2f}%",
            'number_of_trades': results['number_of_trades'],
            'last_trades': results['last_trades'],
            'plot_html': results['plot_html']
        })
        
    except Exception as e:
        return jsonify({
            'error': f'An error occurred: {str(e)}'
        })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port) 