import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const FCNCalculator = () => {
  const [symbols, setSymbols] = useState(['AAPL']);
  const [newSymbol, setNewSymbol] = useState('');
  const [selectedMarket, setSelectedMarket] = useState('US');

  // Popular stocks by market
  const popularStocks = {
    US: [
      { symbol: 'AAPL', name: 'Apple Inc.' },
      { symbol: 'MSFT', name: 'Microsoft' },
      { symbol: 'GOOGL', name: 'Alphabet' },
      { symbol: 'TSLA', name: 'Tesla' },
      { symbol: 'NVDA', name: 'NVIDIA' }
    ],
    HK: [
      { symbol: '0700.HK', name: 'Tencent Holdings' },
      { symbol: '9988.HK', name: 'Alibaba Group' },
      { symbol: '0005.HK', name: 'HSBC Holdings' },
      { symbol: '1299.HK', name: 'AIA Group' },
      { symbol: '3690.HK', name: 'Meituan' },
      { symbol: '2318.HK', name: 'Ping An Insurance' }
    ]
  };
  const [fcnParams, setFcnParams] = useState({
    coupon_rate: 5.5,
    face_value: 100000,
    maturity_months: 12,
    strike_price: 0, // Will be set to current market price
    knock_out_barrier: 0, // Will be set to 110% of current price
    knock_in_barrier: 0, // Will be set to 70% of current price
    barrier_style: 'american',
    observation_frequency: 'monthly',
    autocallable: true
  });
  const [scenarios, setScenarios] = useState({
    base_case: 0.0,
    bull_case: 0.15,
    bear_case: -0.20
  });
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [stockInfo, setStockInfo] = useState({});
  const [error, setError] = useState('');
  const [analyses, setAnalyses] = useState([]);

  useEffect(() => {
    loadRecentAnalyses();
  }, []);

  const loadRecentAnalyses = async () => {
    try {
      const response = await axios.get(`${API}/analyses`);
      setAnalyses(response.data);
    } catch (err) {
      console.error('Error loading analyses:', err);
    }
  };

  const addPopularStock = async (stockSymbol) => {
    if (!symbols.includes(stockSymbol)) {
      const upperSymbol = stockSymbol.toUpperCase();
      setSymbols([...symbols, upperSymbol]);
      
      // Fetch stock info and set FCN parameters
      try {
        const response = await axios.get(`${API}/stock/${upperSymbol}`);
        const stockData = response.data;
        const currentPrice = stockData.current_price;
        
        setStockInfo(prev => ({
          ...prev,
          [upperSymbol]: stockData
        }));
        
        // Auto-set FCN parameters based on market price (for first stock or if not set)
        if (fcnParams.strike_price === 0 || symbols.length === 0) {
          setFcnParams(prev => ({
            ...prev,
            strike_price: currentPrice,
            knock_out_barrier: currentPrice * 1.10, // 110% of current price
            knock_in_barrier: currentPrice * 0.70   // 70% of current price
          }));
        }
      } catch (err) {
        console.error(`Error fetching info for ${upperSymbol}:`, err);
      }
    }
  };

  const getCurrencySymbol = (exchange) => {
    if (exchange === 'HKG') return 'HK$';
    return '$';
  };

  const addSymbol = async () => {
    if (newSymbol && !symbols.includes(newSymbol.toUpperCase())) {
      const upperSymbol = newSymbol.toUpperCase();
      setSymbols([...symbols, upperSymbol]);
      setNewSymbol('');
      
      // Fetch stock info and set FCN parameters
      try {
        const response = await axios.get(`${API}/stock/${upperSymbol}`);
        const stockData = response.data;
        const currentPrice = stockData.current_price;
        
        setStockInfo(prev => ({
          ...prev,
          [upperSymbol]: stockData
        }));
        
        // Auto-set FCN parameters based on market price (for first stock or if not set)
        if (fcnParams.strike_price === 0 || symbols.length === 0) {
          setFcnParams(prev => ({
            ...prev,
            strike_price: currentPrice,
            knock_out_barrier: currentPrice * 1.10, // 110% of current price
            knock_in_barrier: currentPrice * 0.70   // 70% of current price
          }));
        }
      } catch (err) {
        console.error(`Error fetching info for ${upperSymbol}:`, err);
      }
    }
  };

  const removeSymbol = (symbolToRemove) => {
    setSymbols(symbols.filter(symbol => symbol !== symbolToRemove));
    const newStockInfo = { ...stockInfo };
    delete newStockInfo[symbolToRemove];
    setStockInfo(newStockInfo);
  };

  const fetchStockInfo = async (symbol) => {
    try {
      const response = await axios.get(`${API}/stock/${symbol}`);
      setStockInfo(prev => ({
        ...prev,
        [symbol]: response.data
      }));
    } catch (err) {
      console.error(`Error fetching info for ${symbol}:`, err);
    }
  };

  const runAnalysis = async () => {
    if (symbols.length === 0) {
      setError('Please add at least one stock symbol');
      return;
    }

    setLoading(true);
    setError('');
    
    try {
      const analysisRequest = {
        symbols,
        fcn_params: fcnParams,
        analysis_period: 252,
        scenarios
      };

      const response = await axios.post(`${API}/analyze`, analysisRequest);
      setAnalysis(response.data);
      loadRecentAnalyses();
    } catch (err) {
      setError(err.response?.data?.detail || 'Analysis failed');
    } finally {
      setLoading(false);
    }
  };

  const loadAnalysis = async (analysisId) => {
    try {
      const response = await axios.get(`${API}/analysis/${analysisId}`);
      setAnalysis(response.data);
      setSymbols(response.data.request_params.symbols);
      setFcnParams(response.data.request_params.fcn_params);
      setScenarios(response.data.request_params.scenarios);
    } catch (err) {
      setError('Error loading analysis');
    }
  };

  const generateReport = async (reportType) => {
    if (!analysis) return;

    try {
      const response = await axios.post(`${API}/generate-report`, {
        analysis_id: analysis.id,
        report_type: reportType,
        include_charts: true
      });

      // Create download link
      const downloadUrl = `${API}/download/${response.data.filename}`;
      window.open(downloadUrl, '_blank');
    } catch (err) {
      setError('Error generating report');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-800 mb-2">
            FCN Investment Analysis Calculator
          </h1>
          <p className="text-gray-600 text-lg">
            Professional Fixed Coupon Notes analysis for informed investment decisions
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Input Panel */}
          <div className="lg:col-span-1 space-y-6">
            {/* Stock Selection */}
            <div className="bg-white rounded-xl shadow-lg p-6">
              <h3 className="text-xl font-semibold mb-4 text-gray-800">Underlying Stocks</h3>
              
              {/* Market Selection */}
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">Market</label>
                <div className="flex gap-2">
                  <button
                    onClick={() => setSelectedMarket('US')}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                      selectedMarket === 'US'
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    🇺🇸 US Market
                  </button>
                  <button
                    onClick={() => setSelectedMarket('HK')}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                      selectedMarket === 'HK'
                        ? 'bg-red-600 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    🇭🇰 HK Market
                  </button>
                </div>
              </div>

              {/* Popular Stocks */}
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Popular {selectedMarket} Stocks
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {popularStocks[selectedMarket].map(stock => (
                    <button
                      key={stock.symbol}
                      onClick={() => addPopularStock(stock.symbol)}
                      disabled={symbols.includes(stock.symbol)}
                      className={`p-2 text-left text-xs rounded border transition-colors ${
                        symbols.includes(stock.symbol)
                          ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                          : 'bg-gray-50 hover:bg-blue-50 hover:border-blue-300'
                      }`}
                    >
                      <div className="font-semibold">{stock.symbol}</div>
                      <div className="text-gray-600 truncate">{stock.name}</div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Manual Symbol Input */}
              <div className="flex gap-2 mb-4">
                <input
                  type="text"
                  value={newSymbol}
                  onChange={(e) => setNewSymbol(e.target.value.toUpperCase())}
                  placeholder={selectedMarket === 'HK' ? 'Enter symbol (e.g., 0700.HK)' : 'Enter symbol (e.g., AAPL)'}
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  onKeyPress={(e) => e.key === 'Enter' && addSymbol()}
                />
                <button
                  onClick={addSymbol}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  Add
                </button>
              </div>

              {/* Symbol Format Helper */}
              <div className="mb-4 p-3 bg-blue-50 rounded-lg">
                <div className="text-sm text-blue-800">
                  <strong>Symbol Format:</strong>
                  {selectedMarket === 'US' ? (
                    <div>US stocks: Use ticker symbols (e.g., AAPL, MSFT, GOOGL)</div>
                  ) : (
                    <div>HK stocks: Use format XXXX.HK (e.g., 0700.HK, 9988.HK)</div>
                  )}
                </div>
              </div>

              <div className="space-y-2">
                {symbols.map(symbol => (
                  <div key={symbol} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-gray-800">{symbol}</span>
                        {stockInfo[symbol] && (
                          <span className="text-xs px-2 py-1 bg-blue-100 text-blue-800 rounded">
                            {stockInfo[symbol].exchange}
                          </span>
                        )}
                      </div>
                      {stockInfo[symbol] && (
                        <div className="text-sm text-gray-600">
                          {getCurrencySymbol(stockInfo[symbol].exchange)}{stockInfo[symbol].current_price?.toFixed(2)} | {stockInfo[symbol].name}
                        </div>
                      )}
                    </div>
                    <button
                      onClick={() => removeSymbol(symbol)}
                      className="text-red-500 hover:text-red-700 p-1"
                    >
                      ✕
                    </button>
                  </div>
                ))}
              </div>
            </div>

            {/* FCN Parameters */}
            <div className="bg-white rounded-xl shadow-lg p-6">
              <h3 className="text-xl font-semibold mb-4 text-gray-800">FCN Structure</h3>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Coupon Rate (% p.a.)
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    value={fcnParams.coupon_rate}
                    onChange={(e) => setFcnParams({...fcnParams, coupon_rate: parseFloat(e.target.value)})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Face Value ($)
                  </label>
                  <input
                    type="number"
                    value={fcnParams.face_value}
                    onChange={(e) => setFcnParams({...fcnParams, face_value: parseFloat(e.target.value)})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Maturity (Months)
                  </label>
                  <input
                    type="number"
                    value={fcnParams.maturity_months}
                    onChange={(e) => setFcnParams({...fcnParams, maturity_months: parseInt(e.target.value)})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Strike Price ($)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    value={fcnParams.strike_price}
                    onChange={(e) => setFcnParams({...fcnParams, strike_price: parseFloat(e.target.value)})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Knock-Out Barrier ($)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    value={fcnParams.knock_out_barrier}
                    onChange={(e) => setFcnParams({...fcnParams, knock_out_barrier: parseFloat(e.target.value)})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                  <p className="text-xs text-gray-500 mt-1">Early redemption trigger (usually above current price)</p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Knock-In Barrier ($)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    value={fcnParams.knock_in_barrier}
                    onChange={(e) => setFcnParams({...fcnParams, knock_in_barrier: parseFloat(e.target.value)})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                  <p className="text-xs text-gray-500 mt-1">Capital protection loss trigger (usually below current price)</p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Barrier Style
                  </label>
                  <select
                    value={fcnParams.barrier_style}
                    onChange={(e) => setFcnParams({...fcnParams, barrier_style: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="american">American (Continuous Monitoring)</option>
                    <option value="european">European (Observation Dates Only)</option>
                  </select>
                </div>

                <div className="flex items-center">
                  <input
                    type="checkbox"
                    id="autocallable"
                    checked={fcnParams.autocallable}
                    onChange={(e) => setFcnParams({...fcnParams, autocallable: e.target.checked})}
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  <label htmlFor="autocallable" className="ml-2 block text-sm text-gray-700">
                    Autocallable (Early redemption on knock-out)
                  </label>
                </div>
              </div>
            </div>

            {/* Scenario Parameters */}
            <div className="bg-white rounded-xl shadow-lg p-6">
              <h3 className="text-xl font-semibold mb-4 text-gray-800">Scenario Analysis</h3>
              
              <div className="space-y-4">
                {Object.entries(scenarios).map(([scenarioName, value]) => (
                  <div key={scenarioName}>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      {scenarioName.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())} (%)
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      value={value * 100}
                      onChange={(e) => setScenarios({
                        ...scenarios,
                        [scenarioName]: parseFloat(e.target.value) / 100
                      })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                ))}
              </div>
            </div>

            <button
              onClick={runAnalysis}
              disabled={loading || symbols.length === 0}
              className="w-full py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-semibold rounded-lg hover:from-blue-700 hover:to-indigo-700 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <div className="flex items-center justify-center">
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
                  Analyzing...
                </div>
              ) : (
                'Run FCN Analysis'
              )}
            </button>
          </div>

          {/* Results Panel */}
          <div className="lg:col-span-2 space-y-6">
            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
                {error}
              </div>
            )}

            {analysis && (
              <>
                {/* Summary Cards */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <div className="bg-white rounded-xl shadow-lg p-6">
                    <h4 className="text-lg font-semibold text-gray-800 mb-2">Face Value</h4>
                    <p className="text-3xl font-bold text-blue-600">
                      ${analysis.request_params.fcn_params.face_value.toLocaleString()}
                    </p>
                  </div>
                  
                  <div className="bg-white rounded-xl shadow-lg p-6">
                    <h4 className="text-lg font-semibold text-gray-800 mb-2">Coupon Rate</h4>
                    <p className="text-3xl font-bold text-green-600">
                      {analysis.request_params.fcn_params.coupon_rate}% p.a.
                    </p>
                  </div>
                  
                  <div className="bg-white rounded-xl shadow-lg p-6">
                    <h4 className="text-lg font-semibold text-gray-800 mb-2">Maturity</h4>
                    <p className="text-3xl font-bold text-purple-600">
                      {analysis.request_params.fcn_params.maturity_months} months
                    </p>
                  </div>

                  <div className="bg-white rounded-xl shadow-lg p-6">
                    <h4 className="text-lg font-semibold text-gray-800 mb-2">Barrier Style</h4>
                    <p className="text-2xl font-bold text-orange-600 capitalize">
                      {analysis.request_params.fcn_params.barrier_style}
                    </p>
                  </div>
                </div>

                {/* Stock Information */}
                <div className="bg-white rounded-xl shadow-lg p-6">
                  <h3 className="text-xl font-semibold mb-4 text-gray-800">FCN Analysis</h3>
                  <div className="overflow-x-auto">
                    <table className="w-full table-auto">
                      <thead>
                        <tr className="bg-gray-50">
                          <th className="px-4 py-3 text-left font-semibold text-gray-700">Symbol</th>
                          <th className="px-4 py-3 text-left font-semibold text-gray-700">Current Price</th>
                          <th className="px-4 py-3 text-left font-semibold text-gray-700">Strike Price</th>
                          <th className="px-4 py-3 text-left font-semibold text-gray-700">Knock-Out</th>
                          <th className="px-4 py-3 text-left font-semibold text-gray-700">Knock-In</th>
                          <th className="px-4 py-3 text-left font-semibold text-gray-700">Monthly Coupon</th>
                        </tr>
                      </thead>
                      <tbody>
                        {analysis.stocks_info.map((stock, index) => (
                          <tr key={stock.symbol} className={index % 2 === 0 ? 'bg-gray-50' : 'bg-white'}>
                            <td className="px-4 py-3">
                              <div className="flex items-center gap-2">
                                <span className="font-semibold text-blue-600">{stock.symbol}</span>
                                <span className="text-xs px-2 py-1 bg-gray-100 text-gray-600 rounded">
                                  {stock.exchange}
                                </span>
                              </div>
                            </td>
                            <td className="px-4 py-3">
                              {getCurrencySymbol(stock.exchange)}{stock.current_price.toFixed(2)}
                            </td>
                            <td className="px-4 py-3">
                              {getCurrencySymbol(stock.exchange)}{analysis.request_params.fcn_params.strike_price.toFixed(2)}
                            </td>
                            <td className="px-4 py-3">
                              <span className={stock.current_price < analysis.request_params.fcn_params.knock_out_barrier ? 'text-green-600' : 'text-red-600'}>
                                {getCurrencySymbol(stock.exchange)}{analysis.request_params.fcn_params.knock_out_barrier.toFixed(2)}
                              </span>
                            </td>
                            <td className="px-4 py-3">
                              <span className={stock.current_price > analysis.request_params.fcn_params.knock_in_barrier ? 'text-green-600' : 'text-red-600'}>
                                {getCurrencySymbol(stock.exchange)}{analysis.request_params.fcn_params.knock_in_barrier.toFixed(2)}
                              </span>
                            </td>
                            <td className="px-4 py-3">
                              {getCurrencySymbol(stock.exchange)}{analysis.fcn_metrics[stock.symbol]?.monthly_coupon?.toFixed(2) || 'N/A'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Risk Metrics */}
                <div className="bg-white rounded-xl shadow-lg p-6">
                  <h3 className="text-xl font-semibold mb-4 text-gray-800">Risk Analysis</h3>
                  <div className="overflow-x-auto">
                    <table className="w-full table-auto">
                      <thead>
                        <tr className="bg-gray-50">
                          <th className="px-4 py-3 text-left font-semibold text-gray-700">Symbol</th>
                          <th className="px-4 py-3 text-left font-semibold text-gray-700">Volatility</th>
                          <th className="px-4 py-3 text-left font-semibold text-gray-700">Knock-out Prob</th>
                          <th className="px-4 py-3 text-left font-semibold text-gray-700">Knock-in Prob</th>
                          <th className="px-4 py-3 text-left font-semibold text-gray-700">Expected Payoff</th>
                          <th className="px-4 py-3 text-left font-semibold text-gray-700">Avg Redemption</th>
                        </tr>
                      </thead>
                      <tbody>
                        {Object.entries(analysis.risk_metrics).map(([symbol, risk], index) => (
                          <tr key={symbol} className={index % 2 === 0 ? 'bg-gray-50' : 'bg-white'}>
                            <td className="px-4 py-3 font-semibold text-blue-600">{symbol}</td>
                            <td className="px-4 py-3">{risk.volatility_annualized.toFixed(2)}%</td>
                            <td className="px-4 py-3">
                              <span className={risk.knock_out_probability > 30 ? 'text-green-600' : 'text-orange-600'}>
                                {risk.knock_out_probability.toFixed(2)}%
                              </span>
                            </td>
                            <td className="px-4 py-3">
                              <span className={risk.knock_in_probability < 20 ? 'text-green-600' : 'text-red-600'}>
                                {risk.knock_in_probability.toFixed(2)}%
                              </span>
                            </td>
                            <td className="px-4 py-3">${risk.expected_payoff.toFixed(2)}</td>
                            <td className="px-4 py-3">{risk.avg_redemption_month.toFixed(1)} months</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Scenario Analysis */}
                <div className="bg-white rounded-xl shadow-lg p-6">
                  <h3 className="text-xl font-semibold mb-4 text-gray-800">Scenario Analysis</h3>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {Object.entries(analysis.scenario_analysis).map(([scenarioName, scenarioData]) => (
                      <div key={scenarioName} className="bg-gray-50 rounded-lg p-4">
                        <h4 className="font-semibold text-gray-800 mb-3 capitalize">
                          {scenarioName.replace('_', ' ')}
                        </h4>
                        {Object.entries(scenarioData).map(([symbol, data]) => (
                          <div key={symbol} className="mb-4 p-3 bg-white rounded border">
                            <div className="font-semibold text-blue-600 mb-2">{symbol}</div>
                            <div className="text-sm space-y-1">
                              <div className="flex justify-between">
                                <span>Future Price:</span>
                                <span>${data.future_price.toFixed(2)}</span>
                              </div>
                              <div className="flex justify-between">
                                <span>Total Payoff:</span>
                                <span className="font-semibold">${data.payoff.toFixed(2)}</span>
                              </div>
                              <div className="flex justify-between">
                                <span>Total Return:</span>
                                <span className={`font-semibold ${data.total_return >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                  {data.total_return >= 0 ? '+' : ''}{data.total_return.toFixed(2)}%
                                </span>
                              </div>
                              <div className="flex justify-between">
                                <span>Coupons:</span>
                                <span>${data.coupons_received.toFixed(2)}</span>
                              </div>
                              <div className="text-xs text-gray-600 mt-2">
                                Type: {data.redemption_type.replace('_', ' ')}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    ))}
                  </div>
                </div>

                {/* Charts */}
                {analysis.charts && (
                  <div className="bg-white rounded-xl shadow-lg p-6">
                    <h3 className="text-xl font-semibold mb-4 text-gray-800">Market Analysis</h3>
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                      {analysis.charts.price_history && (
                        <div>
                          <h4 className="font-semibold text-gray-700 mb-2">Price History</h4>
                          <img 
                            src={`data:image/png;base64,${analysis.charts.price_history}`} 
                            alt="Price History"
                            className="w-full rounded-lg shadow-sm"
                          />
                        </div>
                      )}
                      {analysis.charts.payoff_distribution && (
                        <div>
                          <h4 className="font-semibold text-gray-700 mb-2">Payoff Distribution</h4>
                          <img 
                            src={`data:image/png;base64,${analysis.charts.payoff_distribution}`} 
                            alt="Payoff Distribution"
                            className="w-full rounded-lg shadow-sm"
                          />
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Report Generation */}
                <div className="bg-white rounded-xl shadow-lg p-6">
                  <h3 className="text-xl font-semibold mb-4 text-gray-800">Generate Reports</h3>
                  <div className="flex gap-4">
                    <button
                      onClick={() => generateReport('excel')}
                      className="flex-1 py-3 bg-green-600 text-white font-semibold rounded-lg hover:bg-green-700 transition-colors"
                    >
                      📊 Download Excel Report
                    </button>
                    <button
                      onClick={() => generateReport('powerpoint')}
                      className="flex-1 py-3 bg-orange-600 text-white font-semibold rounded-lg hover:bg-orange-700 transition-colors"
                    >
                      📈 Download PowerPoint
                    </button>
                  </div>
                </div>
              </>
            )}

            {/* Recent Analyses */}
            {analyses.length > 0 && (
              <div className="bg-white rounded-xl shadow-lg p-6">
                <h3 className="text-xl font-semibold mb-4 text-gray-800">Recent Analyses</h3>
                <div className="space-y-2">
                  {analyses.map(item => (
                    <div key={item.id} className="flex justify-between items-center p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors">
                      <div>
                        <span className="font-semibold text-gray-800">
                          {item.symbols.join(', ')}
                        </span>
                        <div className="text-sm text-gray-600">
                          {new Date(item.created_at).toLocaleDateString()}
                        </div>
                      </div>
                      <button
                        onClick={() => loadAnalysis(item.id)}
                        className="px-4 py-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                      >
                        Load
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default FCNCalculator;
