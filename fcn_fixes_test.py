import requests
import sys
import time
import json
from pprint import pprint

# Get the backend URL from the frontend .env file
BACKEND_URL = "https://0bf3f961-4ee9-49fc-8ed6-5c5ee1eccf8e.preview.emergentagent.com"
API_URL = f"{BACKEND_URL}/api"

class FCNFixesTester:
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = {}

    def run_test(self, name, func):
        """Run a test and track results"""
        print(f"\n🔍 Running test: {name}")
        self.tests_run += 1
        
        try:
            start_time = time.time()
            result = func()
            end_time = time.time()
            
            if result.get("success", False):
                self.tests_passed += 1
                status = "✅ PASSED"
            else:
                status = "❌ FAILED"
                
            print(f"{status} - {name}")
            
            # Store test results
            self.test_results[name] = {
                "success": result.get("success", False),
                "details": result.get("details", {}),
                "duration": end_time - start_time
            }
            
            return result
        except Exception as e:
            print(f"❌ FAILED - {name} - Exception: {str(e)}")
            self.test_results[name] = {
                "success": False,
                "details": {"error": str(e)},
                "duration": 0
            }
            return {"success": False, "details": {"error": str(e)}}

    def test_chart_generation(self):
        """Test Case 1: Chart Generation Fix"""
        print("Testing chart generation with AAPL and MSFT...")
        
        payload = {
            "symbols": ["AAPL", "MSFT"],
            "fcn_params": {
                "coupon_rate": 6.0,
                "face_value": 100000,
                "maturity_months": 12,
                "reference_prices": {"AAPL": 200.0, "MSFT": 350.0},
                "strike_prices": {"AAPL": 200.0, "MSFT": 350.0},
                "put_strike_prices": {"AAPL": 180.0, "MSFT": 315.0},
                "knock_out_barrier_pct": 110.0,
                "knock_in_barrier_pct": 70.0,
                "barrier_style": "american",
                "autocallable": True,
                "basket_type": "worst_of"
            }
        }
        
        try:
            response = requests.post(f"{API_URL}/analyze", json=payload)
            response.raise_for_status()
            result = response.json()
            
            # Check if charts were generated
            charts_exist = "charts" in result and "price_history" in result["charts"] and "payoff_distribution" in result["charts"]
            
            # Check if charts have content
            charts_have_content = False
            if charts_exist:
                price_chart_length = len(result["charts"]["price_history"]) if result["charts"]["price_history"] else 0
                payoff_chart_length = len(result["charts"]["payoff_distribution"]) if result["charts"]["payoff_distribution"] else 0
                charts_have_content = price_chart_length > 0 and payoff_chart_length > 0
            
            success = charts_exist and charts_have_content
            
            return {
                "success": success,
                "details": {
                    "status_code": response.status_code,
                    "charts_exist": charts_exist,
                    "charts_have_content": charts_have_content,
                    "price_chart_size": len(result["charts"]["price_history"]) if charts_exist else 0,
                    "payoff_chart_size": len(result["charts"]["payoff_distribution"]) if charts_exist else 0,
                    "analysis_id": result.get("id")
                }
            }
        except Exception as e:
            return {
                "success": False,
                "details": {
                    "error": str(e),
                    "response_text": getattr(response, "text", "No response text")
                }
            }

    def test_mixed_market_chart_generation(self):
        """Test Case 3: Mixed Market with Chart Generation"""
        print("Testing chart generation with mixed market (AAPL and 0700.HK)...")
        
        payload = {
            "symbols": ["AAPL", "0700.HK"],
            "fcn_params": {
                "coupon_rate": 5.5,
                "face_value": 50000,
                "maturity_months": 6,
                "reference_prices": {"AAPL": 200.0, "0700.HK": 500.0},
                "strike_prices": {"AAPL": 200.0, "0700.HK": 500.0},
                "put_strike_prices": {"AAPL": 180.0, "0700.HK": 450.0},
                "knock_out_barrier_pct": 115.0,
                "knock_in_barrier_pct": 75.0,
                "barrier_style": "european",
                "autocallable": False,
                "basket_type": "worst_of"
            }
        }
        
        try:
            response = requests.post(f"{API_URL}/analyze", json=payload)
            response.raise_for_status()
            result = response.json()
            
            # Check if charts were generated
            charts_exist = "charts" in result and "price_history" in result["charts"] and "payoff_distribution" in result["charts"]
            
            # Check if charts have content
            charts_have_content = False
            if charts_exist:
                price_chart_length = len(result["charts"]["price_history"]) if result["charts"]["price_history"] else 0
                payoff_chart_length = len(result["charts"]["payoff_distribution"]) if result["charts"]["payoff_distribution"] else 0
                charts_have_content = price_chart_length > 0 and payoff_chart_length > 0
            
            success = charts_exist and charts_have_content
            
            return {
                "success": success,
                "details": {
                    "status_code": response.status_code,
                    "charts_exist": charts_exist,
                    "charts_have_content": charts_have_content,
                    "price_chart_size": len(result["charts"]["price_history"]) if charts_exist else 0,
                    "payoff_chart_size": len(result["charts"]["payoff_distribution"]) if charts_exist else 0,
                    "analysis_id": result.get("id")
                }
            }
        except Exception as e:
            return {
                "success": False,
                "details": {
                    "error": str(e),
                    "response_text": getattr(response, "text", "No response text")
                }
            }

    def test_recent_analyses_limit(self):
        """Test Case 2: Recent Analyses Limit"""
        print("Testing recent analyses limit (should be max 5)...")
        
        try:
            response = requests.get(f"{API_URL}/analyses")
            response.raise_for_status()
            analyses = response.json()
            
            # Check if analyses are limited to 5
            count_is_limited = len(analyses) <= 5
            
            # Check if analyses are sorted by created_at descending
            is_sorted = True
            for i in range(1, len(analyses)):
                if analyses[i-1]["created_at"] < analyses[i]["created_at"]:
                    is_sorted = False
                    break
            
            success = count_is_limited and is_sorted
            
            return {
                "success": success,
                "details": {
                    "status_code": response.status_code,
                    "analyses_count": len(analyses),
                    "count_is_limited": count_is_limited,
                    "is_sorted_by_created_at_desc": is_sorted,
                    "analyses": analyses
                }
            }
        except Exception as e:
            return {
                "success": False,
                "details": {
                    "error": str(e),
                    "response_text": getattr(response, "text", "No response text")
                }
            }

    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*50)
        print(f"TEST SUMMARY: {self.tests_passed}/{self.tests_run} tests passed")
        print("="*50)
        
        for name, result in self.test_results.items():
            status = "✅ PASSED" if result["success"] else "❌ FAILED"
            print(f"{status} - {name} ({result['duration']:.2f}s)")
            
            if not result["success"]:
                print(f"  Details: {json.dumps(result['details'], indent=2)}")
        
        print("="*50)
        
        return self.tests_passed == self.tests_run

def main():
    tester = FCNFixesTester()
    
    # Run tests
    tester.run_test("Chart Generation Fix", tester.test_chart_generation)
    tester.run_test("Recent Analyses Limit", tester.test_recent_analyses_limit)
    tester.run_test("Mixed Market Chart Generation", tester.test_mixed_market_chart_generation)
    
    # Print summary
    all_passed = tester.print_summary()
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())