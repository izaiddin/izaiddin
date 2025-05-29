import requests
import sys
import json

class FCNAPITester:
    def __init__(self, base_url="https://0bf3f961-4ee9-49fc-8ed6-5c5ee1eccf8e.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0

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

    def test_analyze_fcn_with_reference_price(self, symbols, fcn_params):
        """Test FCN analysis with reference price"""
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
        
        print(f"\n📝 Request Data:")
        print(json.dumps(data, indent=2))
        
        success, response = self.run_test(
            "FCN Analysis with Reference Price",
            "POST",
            "analyze",
            200,
            data=data
        )
        
        if success and response:
            print("\n📊 Response Summary:")
            
            # Print FCN parameters from request
            fcn_params = response.get('request_params', {}).get('fcn_params', {})
            if fcn_params:
                print(f"FCN Parameters:")
                print(f"  Reference Price: ${fcn_params.get('reference_price', 'N/A')}")
                print(f"  Strike Price: ${fcn_params.get('strike_price', 'N/A')}")
                print(f"  Knock-Out Barrier %: {fcn_params.get('knock_out_barrier_pct', 'N/A')}%")
                print(f"  Knock-In Barrier %: {fcn_params.get('knock_in_barrier_pct', 'N/A')}%")
            
            # Print stock info
            stocks_info = response.get('stocks_info', [])
            if stocks_info:
                print("\nStock Information:")
                for stock in stocks_info:
                    symbol = stock.get('symbol', 'N/A')
                    exchange = stock.get('exchange', 'N/A')
                    current_price = stock.get('current_price', 'N/A')
                    print(f"  {symbol} ({exchange}): ${current_price}")
            
            # Print FCN metrics (simplified)
            fcn_metrics = response.get('fcn_metrics', {})
            if fcn_metrics:
                print("\nFCN Metrics (Raw):")
                print(json.dumps(fcn_metrics, indent=2))
            
            # Print risk metrics (simplified)
            risk_metrics = response.get('risk_metrics', {})
            if risk_metrics:
                print("\nRisk Metrics (Raw):")
                print(json.dumps(risk_metrics, indent=2))
            
        return success, response

def main():
    # Setup
    tester = FCNAPITester()
    
    # Test health check
    tester.test_health_check()
    
    # Test Case 1: Single US Stock with Reference Price
    print("\n🔍 Test Case 1: Single US Stock with Reference Price")
    fcn_params_us = {
        "coupon_rate": 6.0,
        "face_value": 100000,
        "maturity_months": 12,
        "reference_price": 200.0,  # Fixed reference price
        "strike_price": 200.0,     # Usually same as reference
        "knock_out_barrier_pct": 110.0,  # 110% of reference = $220
        "knock_in_barrier_pct": 70.0,    # 70% of reference = $140
        "barrier_style": "american",
        "observation_frequency": "monthly",
        "autocallable": True
    }
    
    tester.test_analyze_fcn_with_reference_price(["AAPL"], fcn_params_us)
    
    # Test Case 2: HK Stock with Reference Price
    print("\n🔍 Test Case 2: HK Stock with Reference Price")
    fcn_params_hk = {
        "coupon_rate": 6.0,
        "face_value": 1000000,
        "maturity_months": 12,
        "reference_price": 500.0,  # Fixed reference price
        "strike_price": 500.0,     # Usually same as reference
        "knock_out_barrier_pct": 110.0,  # 110% of reference = HK$550
        "knock_in_barrier_pct": 70.0,    # 70% of reference = HK$350
        "barrier_style": "american",
        "observation_frequency": "monthly",
        "autocallable": True
    }
    
    tester.test_analyze_fcn_with_reference_price(["0700.HK"], fcn_params_hk)
    
    # Test Case 3: Mixed US/HK Portfolio with Reference Price
    print("\n🔍 Test Case 3: Mixed US/HK Portfolio with Reference Price")
    fcn_params_mixed = {
        "coupon_rate": 5.8,
        "face_value": 500000,
        "maturity_months": 6,
        "reference_price": 150.0,  # Fixed reference price
        "strike_price": 150.0,     # Usually same as reference
        "knock_out_barrier_pct": 110.0,  # 110% of reference = $165
        "knock_in_barrier_pct": 70.0,    # 70% of reference = $105
        "barrier_style": "european",
        "observation_frequency": "monthly",
        "autocallable": True
    }
    
    tester.test_analyze_fcn_with_reference_price(["AAPL", "0700.HK"], fcn_params_mixed)
    
    # Print results
    print(f"\n📊 Tests passed: {tester.tests_passed}/{tester.tests_run}")
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())