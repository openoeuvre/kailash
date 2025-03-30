from http.server import BaseHTTPRequestHandler
import json
import sys
import os

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trading_strategy import TradingStrategy

def analyze_strategy(initial_investment, shares_per_trade, consecutive_days, stock_symbol):
    try:
        # Create strategy instance
        strategy = TradingStrategy(
            initial_investment=float(initial_investment),
            shares_per_trade=int(shares_per_trade),
            consecutive_days=int(consecutive_days),
            stock_symbol=stock_symbol
        )
        
        # Run analysis
        results = strategy.analyze()
        
        # Format results
        return {
            'initial_investment': f"${float(initial_investment):,.2f}",
            'final_value': f"${results['final_value']:,.2f}",
            'total_return': f"{results['total_return']:.2f}%",
            'sp500_return': f"{results['sp500_return']:.2f}%",
            'number_of_trades': results['number_of_trades'],
            'last_trades': results['last_trades'],
            'plot_html': results['plot_html']
        }
    except Exception as e:
        return {'error': str(e)}

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            # Get form data
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            form_data = dict(item.split('=') for item in post_data.decode().split('&'))
            
            # Extract parameters
            initial_investment = form_data.get('initial_investment')
            shares_per_trade = form_data.get('shares_per_trade')
            consecutive_days = form_data.get('consecutive_days')
            stock_symbol = form_data.get('stock_symbol')
            
            # Validate parameters
            if not all([initial_investment, shares_per_trade, consecutive_days, stock_symbol]):
                raise ValueError("Missing required parameters")
            
            # Run analysis
            results = analyze_strategy(
                initial_investment=initial_investment,
                shares_per_trade=shares_per_trade,
                consecutive_days=consecutive_days,
                stock_symbol=stock_symbol
            )
            
            # Send response
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(results).encode())
            
        except Exception as e:
            # Send error response
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode()) 