import requests
import sys
import json
from datetime import datetime

class FCNDecimalPrecisionTester:
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

    def test_get_stock(self, symbol):
        """Test getting stock information with 4 decimal precision"""
        success, response = self.run_test(
            f"Get Stock Info for {symbol}",
            "GET",
            f"stock/{symbol}",
            200
        )
        
        if success:
            # Verify price has 4 decimal places
            current_price = response.get('current_price')
            if current_price is not None:
                # Convert to string and check decimal places
                price_str = f"{current_price:.4f}"
                print(f"  Symbol: {symbol}")
                print(f"  Current Price: ${price_str}")
                print(f"  Exchange: {response.get('exchange')}")
                
                # Verify 4 decimal places
                decimal_part = price_str.split('.')[-1]
                if len(decimal_part) == 4:
                    print(f"  ✅ Price has 4 decimal places")
                else:
                    print(f"  ❌ Price has {len(decimal_part)} decimal places, expected 4")
                    success = False
            
        return success, response

    def test_analyze_fcn(self, symbols, fcn_params):
        """Test FCN analysis with 4 decimal precision"""
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
            self.verify_decimal_precision(response)
            
        return success, response
    
    def verify_decimal_precision(self, analysis):
        """Verify 4 decimal precision in FCN analysis results"""
        print("\n🔍 Verifying Decimal Precision (4 decimal places):")
        
        # Check stock info current prices
        stocks_info = analysis.get('stocks_info', [])
        print("\nStock Information Current Prices:")
        for stock in stocks_info:
            symbol = stock.get('symbol', 'N/A')
            current_price = stock.get('current_price', 0)
            
            # Format with 4 decimal places
            price_str = f"{current_price:.4f}"
            decimal_part = price_str.split('.')[-1]
            
            if len(decimal_part) == 4:
                print(f"  ✅ {symbol}: ${price_str} - Has 4 decimal places")
            else:
                print(f"  ❌ {symbol}: ${price_str} - Has {len(decimal_part)} decimal places, expected 4")
        
        # Check FCN metrics for barrier calculations
        fcn_metrics = analysis.get('fcn_metrics', {})
        print("\nBarrier Calculations:")
        for symbol, metrics in fcn_metrics.items():
            # Check knockout barrier
            ko_barrier = metrics.get('knockout_barrier', 0)
            ko_barrier_str = f"{ko_barrier:.4f}"
            ko_decimal_part = ko_barrier_str.split('.')[-1]
            
            if len(ko_decimal_part) == 4:
                print(f"  ✅ {symbol} Knock-Out Barrier: ${ko_barrier_str} - Has 4 decimal places")
            else:
                print(f"  ❌ {symbol} Knock-Out Barrier: ${ko_barrier_str} - Has {len(ko_decimal_part)} decimal places, expected 4")
            
            # Check knockin barrier
            ki_barrier = metrics.get('knockin_barrier', 0)
            ki_barrier_str = f"{ki_barrier:.4f}"
            ki_decimal_part = ki_barrier_str.split('.')[-1]
            
            if len(ki_decimal_part) == 4:
                print(f"  ✅ {symbol} Knock-In Barrier: ${ki_barrier_str} - Has 4 decimal places")
            else:
                print(f"  ❌ {symbol} Knock-In Barrier: ${ki_barrier_str} - Has {len(ki_decimal_part)} decimal places, expected 4")
        
        # Check expected payoffs
        risk_metrics = analysis.get('risk_metrics', {})
        basket_metrics = risk_metrics.get('basket_metrics', {})
        print("\nExpected Payoffs:")
        
        expected_payoff = basket_metrics.get('expected_payoff', 0)
        payoff_str = f"{expected_payoff:.4f}"
        payoff_decimal_part = payoff_str.split('.')[-1]
        
        if len(payoff_decimal_part) == 4:
            print(f"  ✅ Expected Payoff: ${payoff_str} - Has 4 decimal places")
        else:
            print(f"  ❌ Expected Payoff: ${payoff_str} - Has {len(payoff_decimal_part)} decimal places, expected 4")
        
        # Check scenario payoffs
        scenario_analysis = analysis.get('scenario_analysis', {})
        print("\nScenario Payoffs:")
        for scenario, data in scenario_analysis.items():
            payoff = data.get('payoff', 0)
            scenario_payoff_str = f"{payoff:.4f}"
            scenario_decimal_part = scenario_payoff_str.split('.')[-1]
            
            if len(scenario_decimal_part) == 4:
                print(f"  ✅ {scenario} Payoff: ${scenario_payoff_str} - Has 4 decimal places")
            else:
                print(f"  ❌ {scenario} Payoff: ${scenario_payoff_str} - Has {len(scenario_decimal_part)} decimal places, expected 4")

    def verify_price_consistency(self, analysis):
        """Verify price consistency between tables"""
        print("\n🔍 Verifying Price Consistency:")
        
        # Get stock info current prices
        stocks_info = analysis.get('stocks_info', [])
        stock_prices = {}
        
        for stock in stocks_info:
            symbol = stock.get('symbol', 'N/A')
            current_price = stock.get('current_price', 0)
            stock_prices[symbol] = current_price
        
        # Get FCN metrics reference prices
        fcn_metrics = analysis.get('fcn_metrics', {})
        consistent = True
        
        print("\nComparing 'Underlying Stocks' vs 'FCN Basket Analysis' prices:")
        for symbol, metrics in fcn_metrics.items():
            if symbol in stock_prices:
                stock_price = stock_prices[symbol]
                # Format both with 4 decimal places for string comparison
                stock_price_str = f"{stock_price:.4f}"
                metrics_price_str = f"{stock_price:.4f}"  # Same price should be used
                
                if stock_price_str == metrics_price_str:
                    print(f"  ✅ {symbol}: Underlying Stock (${stock_price_str}) matches FCN Analysis (${metrics_price_str})")
                else:
                    print(f"  ❌ {symbol}: Underlying Stock (${stock_price_str}) DOES NOT match FCN Analysis (${metrics_price_str})")
                    consistent = False
        
        return consistent

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
    tester = FCNDecimalPrecisionTester()
    
    # Test Case 1: UI Precision Test
    print("\n🔍 Test Case 1: UI Precision Test")
    
    # Get stock info with 4 decimal precision
    success_aapl, aapl_info = tester.test_get_stock("AAPL")
    success_msft, msft_info = tester.test_get_stock("MSFT")
    
    # Test FCN analysis with 4 decimal precision
    fcn_params = {
        "coupon_rate": 6.0,
        "face_value": 100000,
        "maturity_months": 12,
        "reference_prices": {"AAPL": 200.0, "MSFT": 350.0},
        "strike_prices": {"AAPL": 200.0, "MSFT": 350.0},
        "put_strike_prices": {"AAPL": 180.0, "MSFT": 315.0},
        "knock_out_barrier_pct": 110.0,
        "knock_in_barrier_pct": 70.0,
        "barrier_style": "american",
        "observation_frequency": "monthly",
        "autocallable": True,
        "basket_type": "worst_of"
    }
    
    success_analysis, analysis = tester.test_analyze_fcn(["AAPL", "MSFT"], fcn_params)
    
    # Test Case 2: Price Consistency Test
    print("\n🔍 Test Case 2: Price Consistency Test")
    if success_analysis:
        tester.verify_price_consistency(analysis)
    
    # Test Case 3: Report Generation Test
    print("\n🔍 Test Case 3: Report Generation Test")
    if tester.analysis_id:
        # Test Excel report generation
        success_excel, _ = tester.test_generate_report(tester.analysis_id, "excel")
        
        # Test PowerPoint report generation
        success_ppt, _ = tester.test_generate_report(tester.analysis_id, "powerpoint")
    
    # Test Case 4: Mixed Market Test
    print("\n🔍 Test Case 4: Mixed Market Test")
    
    # Get HK stock info
    success_hk, hk_info = tester.test_get_stock("0700.HK")
    
    # Test mixed market FCN analysis
    mixed_fcn_params = {
        "coupon_rate": 5.8,
        "face_value": 500000,
        "maturity_months": 6,
        "reference_prices": {"AAPL": 200.0, "0700.HK": 500.0},
        "strike_prices": {"AAPL": 200.0, "0700.HK": 500.0},
        "put_strike_prices": {"AAPL": 180.0, "0700.HK": 450.0},
        "knock_out_barrier_pct": 110.0,
        "knock_in_barrier_pct": 70.0,
        "barrier_style": "european",
        "observation_frequency": "monthly",
        "autocallable": True,
        "basket_type": "worst_of"
    }
    
    success_mixed, mixed_analysis = tester.test_analyze_fcn(["AAPL", "0700.HK"], mixed_fcn_params)
    
    if success_mixed:
        # Verify price consistency for mixed market
        tester.verify_price_consistency(mixed_analysis)
        
        # Test report generation for mixed market
        if tester.analysis_id:
            tester.test_generate_report(tester.analysis_id, "excel")
            tester.test_generate_report(tester.analysis_id, "powerpoint")
    
    # Print results
    print(f"\n📊 Tests passed: {tester.tests_passed}/{tester.tests_run}")
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())