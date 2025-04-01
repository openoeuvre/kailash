from flask import Flask, render_template, request, jsonify, send_file
from trading_strategy import TradingStrategy
import os
import pandas as pd
from io import BytesIO
from datetime import datetime, timedelta
import logging

app = Flask(__name__)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        # Get form data
        initial_investment = float(request.form['initial_investment'])
        shares_small_move = int(request.form['shares_small_move'])
        shares_large_move = int(request.form['shares_large_move'])
        consecutive_days = int(request.form['consecutive_days'])
        stock_symbol = request.form['stock_symbol'].upper()
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        
        logger.info(f"Starting analysis for {stock_symbol}")
        
        # Create strategy instance
        strategy = TradingStrategy(
            initial_investment=initial_investment,
            shares_small_move=shares_small_move,
            shares_large_move=shares_large_move,
            consecutive_days=consecutive_days,
            stock_symbol=stock_symbol,
            start_date=start_date,
            end_date=end_date
        )
        
        # Run analysis with timeout
        try:
            results = strategy.analyze()
        except Exception as e:
            logger.error(f"Error during strategy analysis: {str(e)}")
            return render_template('index.html', error=f"Error during analysis: {str(e)}")
        
        if 'error' in results:
            logger.error(f"Strategy returned error: {results['error']}")
            return render_template('index.html', error=results['error'])
            
        logger.info("Analysis completed successfully")
        return render_template('index.html', results=results)
        
    except Exception as e:
        logger.error(f"Error in analyze route: {str(e)}")
        return render_template('index.html', error=f"An error occurred: {str(e)}")

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