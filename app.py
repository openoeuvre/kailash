from flask import Flask, render_template, request, jsonify, send_file
from trading_strategy import TradingStrategy
import os
import pandas as pd
from io import BytesIO
from datetime import datetime

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
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        
        # Create strategy instance
        strategy = TradingStrategy(
            initial_investment=initial_investment,
            shares_per_trade=shares_per_trade,
            consecutive_days=consecutive_days,
            stock_symbol=stock_symbol,
            start_date=start_date,
            end_date=end_date
        )
        
        # Run analysis
        results = strategy.analyze()
        
        # Add all trades to the results
        results['all_trades'] = strategy.portfolio['trades']
        
        return jsonify(results)
        
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/download_trades', methods=['POST'])
def download_trades():
    try:
        # Get trades data from request
        trades = request.json.get('trades', [])
        
        # Convert trades to DataFrame
        df = pd.DataFrame(trades)
        
        # Create CSV in memory
        csv_buffer = BytesIO()
        df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        
        # Generate filename
        filename = f'trading_trades_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        
        return send_file(
            csv_buffer,
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port) 