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
            print(f"  {stock.get('symbol')}: ${stock.get('current_price'):,.2f}")
        
        # Print FCN metrics
        fcn_metrics = analysis.get('fcn_metrics', {})
        print("\nFCN Metrics:")
        for symbol, metrics in fcn_metrics.items():
            print(f"  {symbol}:")
            print(f"    Distance to Knock-Out: {metrics.get('distance_to_knockout'):,.2f}%")
            print(f"    Distance to Knock-In: {metrics.get('distance_to_knockin'):,.2f}%")
            print(f"    Monthly Coupon: ${metrics.get('monthly_coupon'):,.2f}")
        
        # Print risk metrics
        risk_metrics = analysis.get('risk_metrics', {})
        print("\nRisk Metrics:")
        for symbol, metrics in risk_metrics.items():
            print(f"  {symbol}:")
            print(f"    Knock-Out Probability: {metrics.get('knock_out_probability'):,.2f}%")
            print(f"    Knock-In Probability: {metrics.get('knock_in_probability'):,.2f}%")
            print(f"    Expected Payoff: ${metrics.get('expected_payoff'):,.2f}")
            print(f"    Avg Redemption Month: {metrics.get('avg_redemption_month'):,.2f}")
        
        # Print scenario analysis
        scenario_analysis = analysis.get('scenario_analysis', {})
        print("\nScenario Analysis:")
        for scenario, data in scenario_analysis.items():
            print(f"  {scenario}:")
            for symbol, results in data.items():
                print(f"    {symbol}: ${results.get('payoff'):,.2f} ({results.get('total_return'):+.2f}%)")
                print(f"      Redemption Type: {results.get('redemption_type')}")

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
    
    # Test stock info retrieval
    test_symbols = ["AAPL", "MSFT", "GOOGL"]
    stock_info_results = {}
    
    for symbol in test_symbols:
        success, response = tester.test_get_stock(symbol)
        if success:
            stock_info_results[symbol] = response
            print(f"  Current Price: ${response.get('current_price'):,.2f}")
    
    # Test Case 1: Normal FCN Structure (American Style)
    print("\n🔍 Test Case 1: Normal FCN Structure (American Style)")
    fcn_params_1 = {
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
    
    success_1, analysis_1 = tester.test_analyze_fcn(["AAPL"], fcn_params_1)
    
    # Test Case 2: European Style FCN with Multiple Stocks
    print("\n🔍 Test Case 2: European Style FCN with Multiple Stocks")
    fcn_params_2 = {
        "coupon_rate": 6.0,
        "face_value": 50000,
        "maturity_months": 6,
        "strike_price": 300.0,
        "knock_out_barrier": 330.0,  # 110% of strike
        "knock_in_barrier": 210.0,   # 70% of strike
        "barrier_style": "european",
        "observation_frequency": "monthly",
        "autocallable": False
    }
    
    success_2, analysis_2 = tester.test_analyze_fcn(["MSFT", "GOOGL"], fcn_params_2)
    
    # Test Case 3: Edge Case - Knock-in Barrier Close to Current Price
    print("\n🔍 Test Case 3: Edge Case - Knock-in Barrier Close to Current Price")
    
    # Get AAPL current price
    _, aapl_info = tester.test_get_stock("AAPL")
    if aapl_info and 'current_price' in aapl_info:
        current_price = aapl_info['current_price']
        fcn_params_3 = {
            "coupon_rate": 8.0,
            "face_value": 75000,
            "maturity_months": 3,
            "strike_price": current_price,
            "knock_out_barrier": current_price * 1.05,  # 105% of current price
            "knock_in_barrier": current_price * 0.95,   # 95% of current price (close to current)
            "barrier_style": "american",
            "observation_frequency": "daily",
            "autocallable": True
        }
        
        success_3, analysis_3 = tester.test_analyze_fcn(["AAPL"], fcn_params_3)
    
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
    
    # Test analysis with empty symbols
    tester.test_analyze_fcn([], fcn_params_1)
    
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
    
    tester.test_analyze_fcn(["AAPL"], invalid_barriers_params)
    
    # Print results
    print(f"\n📊 Tests passed: {tester.tests_passed}/{tester.tests_run}")
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())
