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
            # Print raw response for debugging
            print("\n🔍 Raw API Response Structure:")
            print(json.dumps(response.get('fcn_metrics', {}), indent=2))
            self.print_fcn_analysis_results(response)
            
        return success, response
    
    def print_fcn_analysis_results(self, analysis):
        """Print key FCN analysis results for verification"""
        print("\n📊 FCN Analysis Results:")
        
        # Print FCN parameters
        fcn_params = analysis.get('request_params', {}).get('fcn_params', {})
        print(f"FCN Parameters:")
        print(f"  Coupon Rate: {fcn_params.get('coupon_rate', 0)}%")
        print(f"  Face Value: ${fcn_params.get('face_value', 0):,.2f}")
        print(f"  Maturity: {fcn_params.get('maturity_months', 0)} months")
        print(f"  Basket Type: {fcn_params.get('basket_type', 'N/A')}")
        print(f"  Knock-Out Barrier %: {fcn_params.get('knock_out_barrier_pct', 0)}%")
        print(f"  Knock-In Barrier %: {fcn_params.get('knock_in_barrier_pct', 0)}%")
        print(f"  Barrier Style: {fcn_params.get('barrier_style', 'N/A')}")
        print(f"  Autocallable: {fcn_params.get('autocallable', False)}")
        
        # Print reference prices
        reference_prices = fcn_params.get('reference_prices', {})
        print("\nReference Prices:")
        for symbol, price in reference_prices.items():
            print(f"  {symbol}: ${price:,.2f}")
        
        # Print stock info
        stocks_info = analysis.get('stocks_info', [])
        print("\nStock Information:")
        for stock in stocks_info:
            symbol = stock.get('symbol', 'N/A')
            exchange = stock.get('exchange', 'N/A')
            current_price = stock.get('current_price', 0)
            
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
            print(f"    Reference Price: {currency_symbol}{metrics.get('reference_price', 0):,.2f}")
            print(f"    Knock-Out Barrier: {currency_symbol}{metrics.get('knockout_barrier', 0):,.2f} ({metrics.get('knockout_barrier_pct', 0)}%)")
            print(f"    Knock-In Barrier: {currency_symbol}{metrics.get('knockin_barrier', 0):,.2f} ({metrics.get('knockin_barrier_pct', 0)}%)")
            
            perf_vs_ref = metrics.get('performance_vs_reference')
            if perf_vs_ref is not None:
                print(f"    Performance vs Reference: {perf_vs_ref:,.2f}%")
            else:
                print(f"    Performance vs Reference: N/A")
            
            print(f"    Distance to Knock-Out: {metrics.get('distance_to_knockout', 0):,.2f}%")
            print(f"    Distance to Knock-In: {metrics.get('distance_to_knockin', 0):,.2f}%")
            print(f"    Monthly Coupon: {currency_symbol}{metrics.get('monthly_coupon', 0):,.2f}")
            print(f"    Is Worst Performer: {metrics.get('is_worst_performer', False)}")
        
        # Print risk metrics
        risk_metrics = analysis.get('risk_metrics', {})
        basket_metrics = risk_metrics.get('basket_metrics', {})
        print("\nBasket Risk Metrics:")
        
        expected_payoff = basket_metrics.get('expected_payoff')
        if expected_payoff is not None:
            print(f"  Expected Payoff: ${expected_payoff:,.2f}")
        else:
            print(f"  Expected Payoff: N/A")
            
        ko_prob = basket_metrics.get('knock_out_probability')
        if ko_prob is not None:
            print(f"  Knock-Out Probability: {ko_prob:,.2f}%")
        else:
            print(f"  Knock-Out Probability: N/A")
            
        ki_prob = basket_metrics.get('knock_in_probability')
        if ki_prob is not None:
            print(f"  Knock-In Probability: {ki_prob:,.2f}%")
        else:
            print(f"  Knock-In Probability: N/A")
            
        avg_redemption = basket_metrics.get('avg_redemption_month')
        if avg_redemption is not None:
            print(f"  Avg Redemption Month: {avg_redemption:,.2f}")
        else:
            print(f"  Avg Redemption Month: N/A")
            
        print(f"  Most Frequent Worst Performer: {basket_metrics.get('most_frequent_worst', 'N/A')}")
        
        # Print individual stock risk metrics
        print("\nIndividual Stock Risk Metrics:")
        for symbol, metrics in risk_metrics.items():
            if symbol == 'basket_metrics':
                continue
                
            print(f"  {symbol}:")
            
            volatility = metrics.get('volatility_annualized')
            if volatility is not None:
                print(f"    Volatility: {volatility:,.2f}%")
            else:
                print(f"    Volatility: N/A")
                
            sharpe = metrics.get('sharpe_ratio')
            if sharpe is not None:
                print(f"    Sharpe Ratio: {sharpe:,.2f}")
            else:
                print(f"    Sharpe Ratio: N/A")
                
            drawdown = metrics.get('max_drawdown')
            if drawdown is not None:
                print(f"    Max Drawdown: {drawdown:,.2f}%")
            else:
                print(f"    Max Drawdown: N/A")
                
            print(f"    Is Worst Performer: {metrics.get('is_worst_performer', False)}")
        
        # Print scenario analysis
        scenario_analysis = analysis.get('scenario_analysis', {})
        print("\nScenario Analysis:")
        for scenario, data in scenario_analysis.items():
            print(f"  {scenario}:")
            
            basket_perf = data.get('basket_performance')
            if basket_perf is not None:
                print(f"    Basket Performance: {basket_perf:,.2f}%")
            else:
                print(f"    Basket Performance: N/A")
                
            print(f"    Worst Performer: {data.get('worst_performer', 'N/A')}")
            
            payoff = data.get('payoff')
            if payoff is not None:
                print(f"    Payoff: ${payoff:,.2f}")
            else:
                print(f"    Payoff: N/A")
                
            total_return = data.get('total_return')
            if total_return is not None:
                print(f"    Total Return: {total_return:+.2f}%")
            else:
                print(f"    Total Return: N/A")
                
            print(f"    Redemption Type: {data.get('redemption_type', 'N/A')}")
            
            # Print individual performances
            individual_performances = data.get('individual_performances', {})
            print(f"    Individual Performances:")
            for symbol, performance in individual_performances.items():
                if performance is not None:
                    print(f"      {symbol}: {performance:+.2f}%")
                else:
                    print(f"      {symbol}: N/A")

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
    us_test_symbols = ["AAPL", "MSFT"]
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
    hk_test_symbols = ["0700.HK"]
    hk_stock_info_results = {}
    
    for symbol in hk_test_symbols:
        success, response = tester.test_get_stock(symbol)
        if success:
            hk_stock_info_results[symbol] = response
            print(f"  Symbol: {symbol}")
            print(f"  Current Price: HK${response.get('current_price'):,.2f}")
            print(f"  Exchange: {response.get('exchange')}")
            print(f"  Name: {response.get('name')}")
            print("")
    
    # Test Case 1: Full US Basket Analysis
    print("\n🔍 Test Case 1: Full US Basket Analysis")
    
    fcn_params_us_basket = {
        "coupon_rate": 6.0,
        "face_value": 100000,
        "maturity_months": 12,
        "reference_prices": {"AAPL": 200.0, "MSFT": 350.0},
        "strike_prices": {"AAPL": 200.0, "MSFT": 350.0},
        "knock_out_barrier_pct": 110.0,
        "knock_in_barrier_pct": 70.0,
        "barrier_style": "american",
        "observation_frequency": "monthly",
        "autocallable": True,
        "basket_type": "worst_of"
    }
    
    success_us_basket, analysis_us_basket = tester.test_analyze_fcn(["AAPL", "MSFT"], fcn_params_us_basket)
    
    # Test Case 2: Mixed US/HK Basket
    print("\n🔍 Test Case 2: Mixed US/HK Basket")
    
    fcn_params_mixed_basket = {
        "coupon_rate": 5.5,
        "face_value": 50000,
        "maturity_months": 6,
        "reference_prices": {"AAPL": 200.0, "0700.HK": 500.0},
        "strike_prices": {"AAPL": 200.0, "0700.HK": 500.0},
        "knock_out_barrier_pct": 115.0,
        "knock_in_barrier_pct": 75.0,
        "barrier_style": "european",
        "observation_frequency": "monthly",
        "autocallable": False,
        "basket_type": "worst_of"
    }
    
    success_mixed_basket, analysis_mixed_basket = tester.test_analyze_fcn(["AAPL", "0700.HK"], fcn_params_mixed_basket)
    
    # Test validation - Only 1 stock (should fail)
    print("\n🔍 Testing Validation: Only 1 stock (should fail)")
    
    fcn_params_single_stock = {
        "coupon_rate": 6.0,
        "face_value": 100000,
        "maturity_months": 12,
        "reference_prices": {"AAPL": 200.0},
        "strike_prices": {"AAPL": 200.0},
        "knock_out_barrier_pct": 110.0,
        "knock_in_barrier_pct": 70.0,
        "barrier_style": "american",
        "observation_frequency": "monthly",
        "autocallable": True,
        "basket_type": "worst_of"
    }
    
    # This should fail with a 400 error
    tester.run_test(
        "FCN Analysis with Single Stock (Should Fail)",
        "POST",
        "analyze",
        400,
        data={
            "symbols": ["AAPL"],
            "fcn_params": fcn_params_single_stock,
            "analysis_period": 252,
            "scenarios": {
                "base_case": 0.0,
                "bull_case": 0.15,
                "bear_case": -0.20
            }
        }
    )
    
    # Test report generation if any test succeeded
    if tester.analysis_id:
        # Test retrieving the analysis
        tester.test_get_analysis(tester.analysis_id)
        
        # Test listing analyses
        tester.test_list_analyses()
        
        # Test report generation - Excel
        print("\n🔍 Testing Excel Report Generation")
        tester.test_generate_report(tester.analysis_id, "excel")
        
        # Test report generation - PowerPoint
        print("\n🔍 Testing PowerPoint Report Generation")
        tester.test_generate_report(tester.analysis_id, "powerpoint")
    
    # Print results
    print(f"\n📊 Tests passed: {tester.tests_passed}/{tester.tests_run}")
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())