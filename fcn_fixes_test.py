
import requests
import json
import time
import sys
import matplotlib.pyplot as plt
import numpy as np
import base64
from datetime import datetime

class FCNFixesTester:
    def __init__(self, base_url):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = {}

    def run_test(self, name, method, endpoint, expected_status, data=None, params=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                if response.status_code != 204:  # No content
                    return success, response.json()
                return success, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"Response: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_chart_generation(self, test_data):
        """Test chart generation with small data range"""
        print("\n🔍 Testing chart generation with small data range...")
        
        success, response = self.run_test(
            "Chart Generation",
            "POST",
            "api/analyze",
            200,
            data=test_data
        )
        
        if success and 'charts' in response:
            # Check if charts were generated
            if 'payoff_distribution' in response['charts'] and response['charts']['payoff_distribution']:
                print("✅ Chart generated successfully")
                self.test_results["chart_generation"] = True
                return True, response
            else:
                print("❌ Chart generation failed - No payoff distribution chart")
                self.test_results["chart_generation"] = False
                return False, response
        else:
            print("❌ Chart generation failed")
            self.test_results["chart_generation"] = False
            return False, response

    def test_recent_analyses_limit(self):
        """Test that recent analyses are limited to 5"""
        print("\n🔍 Testing recent analyses limit...")
        
        success, response = self.run_test(
            "Recent Analyses Limit",
            "GET",
            "api/analyses",
            200
        )
        
        if success:
            analyses_count = len(response)
            if analyses_count <= 5:
                print(f"✅ Recent analyses limited to {analyses_count} (max 5)")
                self.test_results["recent_analyses_limit"] = True
                return True, response
            else:
                print(f"❌ Recent analyses not limited to 5 (got {analyses_count})")
                self.test_results["recent_analyses_limit"] = False
                return False, response
        else:
            self.test_results["recent_analyses_limit"] = False
            return False, response

    def run_all_tests(self):
        """Run all tests for the FCN fixes"""
        # Test Case 1: Chart Generation Error Fix
        test_data = {
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
        
        # Test chart generation
        chart_success, chart_response = self.test_chart_generation(test_data)
        
        # Test recent analyses limit
        analyses_success, analyses_response = self.test_recent_analyses_limit()
        
        # Print summary
        print("\n📊 Test Summary:")
        print(f"Chart Generation: {'✅ PASSED' if self.test_results.get('chart_generation', False) else '❌ FAILED'}")
        print(f"Recent Analyses Limit: {'✅ PASSED' if self.test_results.get('recent_analyses_limit', False) else '❌ FAILED'}")
        
        return self.test_results

def main():
    # Get backend URL from frontend .env
    backend_url = "https://0bf3f961-4ee9-49fc-8ed6-5c5ee1eccf8e.preview.emergentagent.com"
    
    # Run tests
    tester = FCNFixesTester(backend_url)
    results = tester.run_all_tests()
    
    # Return success if all tests passed
    return 0 if all(results.values()) else 1

if __name__ == "__main__":
    sys.exit(main())
