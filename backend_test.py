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
            
        return success, response

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
    test_symbols = ["AAPL", "MSFT", "TSLA"]
    stock_info_results = {}
    
    for symbol in test_symbols:
        success, response = tester.test_get_stock(symbol)
        if success:
            stock_info_results[symbol] = response
    
    # Test FCN analysis
    fcn_params = {
        "coupon_rate": 5.5,
        "face_value": 100000,
        "maturity_years": 1,
        "barrier_level": 70,
        "observation_frequency": "daily"
    }
    
    success, analysis_response = tester.test_analyze_fcn(test_symbols[:2], fcn_params)
    
    if success and tester.analysis_id:
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
    tester.test_analyze_fcn([], fcn_params)
    
    # Print results
    print(f"\n📊 Tests passed: {tester.tests_passed}/{tester.tests_run}")
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())
