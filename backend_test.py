import requests
import sys
import time
from datetime import datetime
import json

class FCNAPITester:
    def __init__(self, base_url="https://0bf3f961-4ee9-49fc-8ed6-5c5ee1eccf8e.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.analysis_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return success, response.json()
                except:
                    return success, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_detail = response.json().get('detail', 'No detail provided')
                    print(f"Error detail: {error_detail}")
                except:
                    print(f"Response: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_health_check(self):
        """Test API health check endpoint"""
        return self.run_test(
            "API Health Check",
            "GET",
            "",
            200
        )

    def test_get_stock(self, symbol):
        """Test getting stock information"""
        return self.run_test(
            f"Get Stock Info for {symbol}",
            "GET",
            f"stock/{symbol}",
            200
        )

    def test_analyze_fcn(self, symbols, fcn_params):
        """Test FCN analysis"""
        data = {
            "symbols": symbols,
            "fcn_params": fcn_params,
            "analysis_period": 252,
            "scenarios": {
                "base_case": 0.0,
                "bull_case": 0.15,
                "bear_case": -0.20
            }
        }
        
        success, response = self.run_test(
            "FCN Analysis",
            "POST",
            "analyze",
            200,
            data=data
        )
        
        if success and response and 'id' in response:
            self.analysis_id = response['id']
            self.print_fcn_analysis_results(response)
            
        return success, response
    
    def print_fcn_analysis_results(self, analysis):
        """Print key FCN analysis results for verification"""
        print("\n📊 FCN Analysis Results:")
        
        # Print FCN parameters
        fcn_params = analysis.get('request_params', {}).get('fcn_params', {})
        print(f"FCN Parameters:")
        print(f"  Coupon Rate: {fcn_params.get('coupon_rate')}%")
        print(f"  Face Value: ${fcn_params.get('face_value'):,.2f}")
        print(f"  Maturity: {fcn_params.get('maturity_months')} months")
        print(f"  Strike Price: ${fcn_params.get('strike_price'):,.2f}")
        print(f"  Knock-Out Barrier: ${fcn_params.get('knock_out_barrier'):,.2f}")
        print(f"  Knock-In Barrier: ${fcn_params.get('knock_in_barrier'):,.2f}")
        print(f"  Barrier Style: {fcn_params.get('barrier_style')}")
        print(f"  Autocallable: {fcn_params.get('autocallable')}")
        
        # Print stock info
        stocks_info = analysis.get('stocks_info', [])
        print("\nStock Information:")
        for stock in stocks_info:
            symbol = stock.get('symbol')
            exchange = stock.get('exchange')
            current_price = stock.get('current_price')
            
            # Determine currency symbol based on exchange
            currency_symbol = 'HK$' if exchange == 'HKG' else '$'
            
            print(f"  {symbol} ({exchange}): {currency_symbol}{current_price:,.2f}")
        
        # Print FCN metrics
        fcn_metrics = analysis.get('fcn_metrics', {})
        print("\nFCN Metrics:")
        for symbol, metrics in fcn_metrics.items():
            # Find the stock info for this symbol to get the exchange
            stock = next((s for s in stocks_info if s.get('symbol') == symbol), None)
            currency_symbol = 'HK$' if stock and stock.get('exchange') == 'HKG' else '$'
            
            print(f"  {symbol}:")
            print(f"    Distance to Knock-Out: {metrics.get('distance_to_knockout'):,.2f}%")
            print(f"    Distance to Knock-In: {metrics.get('distance_to_knockin'):,.2f}%")
            print(f"    Monthly Coupon: {currency_symbol}{metrics.get('monthly_coupon'):,.2f}")
        
        # Print risk metrics
        risk_metrics = analysis.get('risk_metrics', {})
        print("\nRisk Metrics:")
        for symbol, metrics in risk_metrics.items():
            # Find the stock info for this symbol to get the exchange
            stock = next((s for s in stocks_info if s.get('symbol') == symbol), None)
            currency_symbol = 'HK$' if stock and stock.get('exchange') == 'HKG' else '$'
            
            print(f"  {symbol}:")
            print(f"    Knock-Out Probability: {metrics.get('knock_out_probability'):,.2f}%")
            print(f"    Knock-In Probability: {metrics.get('knock_in_probability'):,.2f}%")
            print(f"    Expected Payoff: {currency_symbol}{metrics.get('expected_payoff'):,.2f}")
            print(f"    Avg Redemption Month: {metrics.get('avg_redemption_month'):,.2f}")
        
        # Print scenario analysis
        scenario_analysis = analysis.get('scenario_analysis', {})
        print("\nScenario Analysis:")
        for scenario, data in scenario_analysis.items():
            print(f"  {scenario}:")
            for symbol, results in data.items():
                # Find the stock info for this symbol to get the exchange
                stock = next((s for s in stocks_info if s.get('symbol') == symbol), None)
                currency_symbol = 'HK$' if stock and stock.get('exchange') == 'HKG' else '$'
                
                print(f"    {symbol}: {currency_symbol}{results.get('payoff'):,.2f} ({results.get('total_return'):+.2f}%)")
                print(f"      Redemption Type: {results.get('redemption_type')}")
                print(f"      Future Price: {currency_symbol}{results.get('future_price'):,.2f}")

    def test_get_analysis(self, analysis_id):
        """Test retrieving a saved analysis"""
        return self.run_test(
            "Get Saved Analysis",
            "GET",
            f"analysis/{analysis_id}",
            200
        )

    def test_list_analyses(self):
        """Test listing recent analyses"""
        return self.run_test(
            "List Recent Analyses",
            "GET",
            "analyses",
            200
        )

    def test_generate_report(self, analysis_id, report_type):
        """Test report generation"""
        data = {
            "analysis_id": analysis_id,
            "report_type": report_type,
            "include_charts": True
        }
        
        success, response = self.run_test(
            f"Generate {report_type.capitalize()} Report",
            "POST",
            "generate-report",
            200,
            data=data
        )
        
        if success and response and 'filename' in response:
            return self.test_download_report(response['filename'])
        
        return False, {}

    def test_download_report(self, filename):
        """Test downloading a report"""
        return self.run_test(
            f"Download Report {filename}",
            "GET",
            f"download/{filename}",
            200
        )

def main():
    # Setup
    tester = FCNAPITester()
    
    # Test health check
    tester.test_health_check()
    
    # Test US stock info retrieval
    print("\n🔍 Testing US Stock Info Retrieval")
    us_test_symbols = ["AAPL", "MSFT", "GOOGL"]
    us_stock_info_results = {}
    
    for symbol in us_test_symbols:
        success, response = tester.test_get_stock(symbol)
        if success:
            us_stock_info_results[symbol] = response
            print(f"  Symbol: {symbol}")
            print(f"  Current Price: ${response.get('current_price'):,.2f}")
            print(f"  Exchange: {response.get('exchange')}")
            print(f"  Name: {response.get('name')}")
            print("")
    
    # Test HK stock info retrieval
    print("\n🔍 Testing HK Stock Info Retrieval")
    hk_test_symbols = ["0700.HK", "9988.HK", "0005.HK"]
    hk_stock_info_results = {}
    
    for symbol in hk_test_symbols:
        success, response = tester.test_get_stock(symbol)
        if success:
            hk_stock_info_results[symbol] = response
            print(f"  Symbol: {symbol}")
            print(f"  Current Price: ${response.get('current_price'):,.2f}")
            print(f"  Exchange: {response.get('exchange')}")
            print(f"  Name: {response.get('name')}")
            print("")
    
    # Test Case 1: US Market FCN Structure
    print("\n🔍 Test Case 1: US Market FCN Structure")
    fcn_params_us = {
        "coupon_rate": 5.5,
        "face_value": 100000,
        "maturity_months": 12,
        "strike_price": 200.0,
        "knock_out_barrier": 220.0,  # 110% of strike
        "knock_in_barrier": 140.0,   # 70% of strike
        "barrier_style": "american",
        "observation_frequency": "monthly",
        "autocallable": True
    }
    
    success_us, analysis_us = tester.test_analyze_fcn(["AAPL"], fcn_params_us)
    
    # Test Case 2: HK Market FCN Structure
    print("\n🔍 Test Case 2: HK Market FCN Structure")
    fcn_params_hk = {
        "coupon_rate": 6.0,
        "face_value": 1000000,
        "maturity_months": 12,
        "strike_price": 400.0,
        "knock_out_barrier": 440.0,
        "knock_in_barrier": 280.0,
        "barrier_style": "american",
        "observation_frequency": "monthly",
        "autocallable": True
    }
    
    success_hk, analysis_hk = tester.test_analyze_fcn(["0700.HK", "9988.HK"], fcn_params_hk)
    
    # Test Case 3: Mixed US/HK Portfolio
    print("\n🔍 Test Case 3: Mixed US/HK Portfolio")
    fcn_params_mixed = {
        "coupon_rate": 5.8,
        "face_value": 500000,
        "maturity_months": 6,
        "strike_price": 150.0,  # This will be relative to the first stock
        "knock_out_barrier": 165.0,
        "knock_in_barrier": 105.0,
        "barrier_style": "european",
        "observation_frequency": "monthly",
        "autocallable": True
    }
    
    success_mixed, analysis_mixed = tester.test_analyze_fcn(["AAPL", "0700.HK"], fcn_params_mixed)
    
    # Test Case 4: Edge Case - Dynamic Barriers Based on Current Prices
    print("\n🔍 Test Case 4: Dynamic Barriers Based on Current Prices")
    
    # Get Tencent current price
    _, tencent_info = tester.test_get_stock("0700.HK")
    if tencent_info and 'current_price' in tencent_info:
        current_price = tencent_info['current_price']
        fcn_params_dynamic = {
            "coupon_rate": 8.0,
            "face_value": 750000,
            "maturity_months": 3,
            "strike_price": current_price,
            "knock_out_barrier": current_price * 1.05,  # 105% of current price
            "knock_in_barrier": current_price * 0.95,   # 95% of current price (close to current)
            "barrier_style": "american",
            "observation_frequency": "daily",
            "autocallable": True
        }
        
        success_dynamic, analysis_dynamic = tester.test_analyze_fcn(["0700.HK"], fcn_params_dynamic)
    
    # Test retrieving and listing analyses if any test succeeded
    if tester.analysis_id:
        # Test retrieving the analysis
        tester.test_get_analysis(tester.analysis_id)
        
        # Test listing analyses
        tester.test_list_analyses()
        
        # Test report generation
        tester.test_generate_report(tester.analysis_id, "excel")
        tester.test_generate_report(tester.analysis_id, "powerpoint")
    
    # Test error handling
    print("\n🔍 Testing Error Handling...")
    
    # Test with invalid stock symbol
    tester.test_get_stock("INVALID_SYMBOL")
    
    # Test with invalid HK stock symbol format
    tester.test_get_stock("700.HK")  # Missing leading zero
    
    # Test analysis with empty symbols
    tester.test_analyze_fcn([], fcn_params_us)
    
    # Test with invalid barrier structure (knock_in_barrier > knock_out_barrier)
    invalid_barriers_params = {
        "coupon_rate": 5.5,
        "face_value": 100000,
        "maturity_months": 12,
        "strike_price": 200.0,
        "knock_out_barrier": 150.0,  # Lower than knock_in_barrier (invalid)
        "knock_in_barrier": 180.0,   # Higher than knock_out_barrier (invalid)
        "barrier_style": "american",
        "observation_frequency": "monthly",
        "autocallable": True
    }
    
    tester.test_analyze_fcn(["0700.HK"], invalid_barriers_params)
    
    # Print results
    print(f"\n📊 Tests passed: {tester.tests_passed}/{tester.tests_run}")
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())
