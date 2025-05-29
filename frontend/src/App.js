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
    reference_prices: {}, // Will be populated when stocks are added
    strike_prices: {}, // Will be populated when stocks are added  
    put_strike_prices: {}, // Put strike prices for equity conversion
    knock_out_barrier_pct: 110.0, // 110% of reference price
    knock_in_barrier_pct: 70.0, // 70% of reference price
    barrier_style: 'american',
    observation_frequency: 'monthly',
    autocallable: true,
    basket_type: 'worst_of'
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
        
        // Auto-set FCN parameters for basket structure
        setFcnParams(prev => ({
          ...prev,
          reference_prices: {
            ...prev.reference_prices,
            [upperSymbol]: currentPrice
          },
          strike_prices: {
            ...prev.strike_prices,
            [upperSymbol]: currentPrice  // Usually same as reference price
          },
          put_strike_prices: {
            ...prev.put_strike_prices,
            [upperSymbol]: currentPrice * 0.9  // Typically 90% of reference price
          }
        }));
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
        
        // Auto-set FCN parameters for basket structure
        setFcnParams(prev => ({
          ...prev,
          reference_prices: {
            ...prev.reference_prices,
            [upperSymbol]: currentPrice
          },
          strike_prices: {
            ...prev.strike_prices,
            [upperSymbol]: currentPrice  // Usually same as reference price
          },
          put_strike_prices: {
            ...prev.put_strike_prices,
            [upperSymbol]: currentPrice * 0.9  // Typically 90% of reference price
          }
        }));
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
    
    // Remove from FCN parameters
    const newReferencePrices = { ...fcnParams.reference_prices };
    const newStrikePrices = { ...fcnParams.strike_prices };
    const newPutStrikePrices = { ...fcnParams.put_strike_prices };
    delete newReferencePrices[symbolToRemove];
    delete newStrikePrices[symbolToRemove];
    delete newPutStrikePrices[symbolToRemove];
    
    setFcnParams(prev => ({
      ...prev,
      reference_prices: newReferencePrices,
      strike_prices: newStrikePrices,
      put_strike_prices: newPutStrikePrices
    }));
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
    if (symbols.length < 2) {
      setError('FCN requires at least 2 stocks for basket structure');
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
      setError(''); // Clear any previous errors
      const response = await axios.post(`${API}/generate-report`, {
        analysis_id: analysis.id,
        report_type: reportType,
        include_charts: true
      });

      if (response.data && response.data.filename) {
        // Create download link
        const downloadUrl = `${API}/download/${response.data.filename}`;
        window.open(downloadUrl, '_blank');
      } else {
        setError('Report generated but download link not available');
      }
    } catch (err) {
      console.error('Report generation error:', err);
      setError(`Error generating ${reportType} report: ${err.response?.data?.detail || err.message}`);
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

              {/* FCN Basket Info */}
              <div className="mb-4 p-3 bg-blue-50 rounded-lg">
                <div className="text-sm text-blue-800">
                  <strong>FCN Basket Structure:</strong> FCNs typically require exactly 2 underlying stocks. 
                  The performance is based on the <strong>worst-performing</strong> stock in the basket.
                  {symbols.length < 2 && (
                    <div className="mt-1 text-red-600 font-medium">
                      ⚠️ Please add {2 - symbols.length} more stock{2 - symbols.length > 1 ? 's' : ''} to complete the basket.
                    </div>
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
                          {getCurrencySymbol(stockInfo[symbol].exchange)}{stockInfo[symbol].current_price?.toFixed(4)} | {stockInfo[symbol].name}
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
                    Basket Type
                  </label>
                  <select
                    value={fcnParams.basket_type}
                    onChange={(e) => setFcnParams({...fcnParams, basket_type: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="worst_of">Worst-Of (Standard FCN)</option>
                    <option value="best_of">Best-Of</option>
                    <option value="average">Average Performance</option>
                  </select>
                  <p className="text-xs text-gray-500 mt-1">How basket performance is calculated</p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Reference Prices
                  </label>
                  <div className="space-y-2">
                    {symbols.map(symbol => (
                      <div key={symbol} className="flex justify-between items-center p-2 bg-gray-50 rounded">
                        <span className="text-sm font-medium">{symbol}:</span>
                        <div className="flex items-center gap-2">
                          <input
                            type="number"
                            step="0.0001"
                            value={fcnParams.reference_prices[symbol] || 0}
                            onChange={(e) => setFcnParams({
                              ...fcnParams,
                              reference_prices: {
                                ...fcnParams.reference_prices,
                                [symbol]: parseFloat(e.target.value)
                              }
                            })}
                            className="w-32 px-2 py-1 text-sm border border-gray-300 rounded"
                          />
                          <span className="text-xs text-gray-500">
                            {getCurrencySymbol(stockInfo[symbol]?.exchange || 'NMS')}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                  <p className="text-xs text-gray-500 mt-1">Initial fixing prices for each stock in the basket</p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Put Strike Prices
                  </label>
                  <div className="space-y-2">
                    {symbols.map(symbol => (
                      <div key={symbol} className="flex justify-between items-center p-2 bg-gray-50 rounded">
                        <span className="text-sm font-medium">{symbol}:</span>
                        <div className="flex items-center gap-2">
                          <input
                            type="number"
                            step="0.0001"
                            value={fcnParams.put_strike_prices[symbol] || 0}
                            onChange={(e) => setFcnParams({
                              ...fcnParams,
                              put_strike_prices: {
                                ...fcnParams.put_strike_prices,
                                [symbol]: parseFloat(e.target.value)
                              }
                            })}
                            className="w-32 px-2 py-1 text-sm border border-gray-300 rounded"
                          />
                          <span className="text-xs text-gray-500">
                            {getCurrencySymbol(stockInfo[symbol]?.exchange || 'NMS')}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                  <p className="text-xs text-gray-500 mt-1">Put strike prices for equity conversion if knock-in occurs</p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Knock-Out Barrier (%)
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    value={fcnParams.knock_out_barrier_pct}
                    onChange={(e) => setFcnParams({...fcnParams, knock_out_barrier_pct: parseFloat(e.target.value)})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Early redemption trigger (% of reference price)
                    {symbols.length > 0 && (
                      <div className="mt-1">
                        {symbols.map(symbol => (
                          <div key={symbol}>
                            {symbol}: {getCurrencySymbol(stockInfo[symbol]?.exchange || 'NMS')}{((fcnParams.reference_prices[symbol] || 0) * fcnParams.knock_out_barrier_pct / 100).toFixed(4)}
                          </div>
                        ))}
                      </div>
                    )}
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Knock-In Barrier (%)
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    value={fcnParams.knock_in_barrier_pct}
                    onChange={(e) => setFcnParams({...fcnParams, knock_in_barrier_pct: parseFloat(e.target.value)})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Capital protection loss trigger (% of reference price)
                    {symbols.length > 0 && (
                      <div className="mt-1">
                        {symbols.map(symbol => (
                          <div key={symbol}>
                            {symbol}: {getCurrencySymbol(stockInfo[symbol]?.exchange || 'NMS')}{((fcnParams.reference_prices[symbol] || 0) * fcnParams.knock_in_barrier_pct / 100).toFixed(4)}
                          </div>
                        ))}
                      </div>
                    )}
                  </p>
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
              disabled={loading || symbols.length < 2}
              className="w-full py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-semibold rounded-lg hover:from-blue-700 hover:to-indigo-700 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <div className="flex items-center justify-center">
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
                  Analyzing Basket...
                </div>
              ) : (
                `Run FCN Basket Analysis ${symbols.length < 2 ? `(${2 - symbols.length} more stock${2 - symbols.length > 1 ? 's' : ''} needed)` : ''}`
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
                    <h4 className="text-lg font-semibold text-gray-800 mb-2">Basket Type</h4>
                    <p className="text-2xl font-bold text-orange-600 capitalize">
                      {analysis.request_params.fcn_params.basket_type.replace('_', '-')}
                    </p>
                  </div>
                </div>

                {/* Basket Performance Summary */}
                <div className="bg-white rounded-xl shadow-lg p-6">
                  <h3 className="text-xl font-semibold mb-4 text-gray-800">Basket Performance Summary</h3>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="bg-gradient-to-r from-blue-50 to-blue-100 p-4 rounded-lg">
                      <h4 className="font-semibold text-blue-800 mb-2">Expected Payoff</h4>
                      <p className="text-2xl font-bold text-blue-600">
                        ${analysis.risk_metrics.basket_metrics?.expected_payoff?.toFixed(2) || 'N/A'}
                      </p>
                    </div>
                    <div className="bg-gradient-to-r from-green-50 to-green-100 p-4 rounded-lg">
                      <h4 className="font-semibold text-green-800 mb-2">Knock-Out Probability</h4>
                      <p className="text-2xl font-bold text-green-600">
                        {analysis.risk_metrics.basket_metrics?.knock_out_probability?.toFixed(2) || 'N/A'}%
                      </p>
                    </div>
                    <div className="bg-gradient-to-r from-red-50 to-red-100 p-4 rounded-lg">
                      <h4 className="font-semibold text-red-800 mb-2">Knock-In Probability</h4>
                      <p className="text-2xl font-bold text-red-600">
                        {analysis.risk_metrics.basket_metrics?.knock_in_probability?.toFixed(2) || 'N/A'}%
                      </p>
                    </div>
                  </div>
                  {analysis.risk_metrics.basket_metrics?.most_frequent_worst !== "N/A" && (
                    <div className="mt-4 p-3 bg-yellow-50 rounded-lg">
                      <p className="text-sm text-yellow-800">
                        <strong>Most Frequent Worst Performer:</strong> {analysis.risk_metrics.basket_metrics.most_frequent_worst}
                      </p>
                    </div>
                  )}
                </div>

                {/* Stock Information */}
                <div className="bg-white rounded-xl shadow-lg p-6">
                  <h3 className="text-xl font-semibold mb-4 text-gray-800">FCN Basket Analysis</h3>
                  <div className="overflow-x-auto">
                    <table className="w-full table-auto">
                      <thead>
                        <tr className="bg-gray-50">
                          <th className="px-4 py-3 text-left font-semibold text-gray-700">Symbol</th>
                          <th className="px-4 py-3 text-left font-semibold text-gray-700">Current Price</th>
                          <th className="px-4 py-3 text-left font-semibold text-gray-700">Reference Price</th>
                          <th className="px-4 py-3 text-left font-semibold text-gray-700">Performance vs Ref</th>
                          <th className="px-4 py-3 text-left font-semibold text-gray-700">Worst Performer</th>
                          <th className="px-4 py-3 text-left font-semibold text-gray-700">Barriers</th>
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
                              {getCurrencySymbol(stock.exchange)}{stock.current_price.toFixed(4)}
                            </td>
                            <td className="px-4 py-3">
                              {getCurrencySymbol(stock.exchange)}{analysis.request_params.fcn_params.reference_prices[stock.symbol]?.toFixed(4) || 'N/A'}
                            </td>
                            <td className="px-4 py-3">
                              <span className={analysis.fcn_metrics[stock.symbol]?.performance_vs_reference >= 0 ? 'text-green-600' : 'text-red-600'}>
                                {analysis.fcn_metrics[stock.symbol]?.performance_vs_reference >= 0 ? '+' : ''}{analysis.fcn_metrics[stock.symbol]?.performance_vs_reference?.toFixed(4) || 'N/A'}%
                              </span>
                            </td>
                            <td className="px-4 py-3">
                              {analysis.fcn_metrics[stock.symbol]?.is_worst_performer ? (
                                <span className="px-2 py-1 bg-red-100 text-red-800 text-xs font-semibold rounded">
                                  WORST
                                </span>
                              ) : (
                                <span className="text-gray-400">-</span>
                              )}
                            </td>
                            <td className="px-4 py-3">
                              <div className="text-xs">
                                <div className="text-green-600">
                                  KO: {getCurrencySymbol(stock.exchange)}{analysis.fcn_metrics[stock.symbol]?.knockout_barrier?.toFixed(4) || 'N/A'}
                                </div>
                                <div className="text-red-600">
                                  KI: {getCurrencySymbol(stock.exchange)}{analysis.fcn_metrics[stock.symbol]?.knockin_barrier?.toFixed(4) || 'N/A'}
                                </div>
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Risk Metrics */}
                <div className="bg-white rounded-xl shadow-lg p-6">
                  <h3 className="text-xl font-semibold mb-4 text-gray-800">Individual Stock Risk Analysis</h3>
                  <div className="overflow-x-auto">
                    <table className="w-full table-auto">
                      <thead>
                        <tr className="bg-gray-50">
                          <th className="px-4 py-3 text-left font-semibold text-gray-700">Symbol</th>
                          <th className="px-4 py-3 text-left font-semibold text-gray-700">Volatility</th>
                          <th className="px-4 py-3 text-left font-semibold text-gray-700">Sharpe Ratio</th>
                          <th className="px-4 py-3 text-left font-semibold text-gray-700">Max Drawdown</th>
                          <th className="px-4 py-3 text-left font-semibold text-gray-700">Performance vs Ref</th>
                          <th className="px-4 py-3 text-left font-semibold text-gray-700">Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {Object.entries(analysis.risk_metrics).filter(([key]) => key !== 'basket_metrics').map(([symbol, risk], index) => {
                          const stock = analysis.stocks_info.find(s => s.symbol === symbol);
                          const currencySymbol = stock ? getCurrencySymbol(stock.exchange) : '$';
                          
                          return (
                            <tr key={symbol} className={index % 2 === 0 ? 'bg-gray-50' : 'bg-white'}>
                              <td className="px-4 py-3">
                                <div className="flex items-center gap-2">
                                  <span className="font-semibold text-blue-600">{symbol}</span>
                                  {stock && (
                                    <span className="text-xs px-2 py-1 bg-gray-100 text-gray-600 rounded">
                                      {stock.exchange}
                                    </span>
                                  )}
                                </div>
                              </td>
                              <td className="px-4 py-3">{risk.volatility_annualized?.toFixed(2) || 'N/A'}%</td>
                              <td className="px-4 py-3">{risk.sharpe_ratio?.toFixed(2) || 'N/A'}</td>
                              <td className="px-4 py-3">
                                <span className="text-red-600">
                                  {risk.max_drawdown?.toFixed(2) || 'N/A'}%
                                </span>
                              </td>
                              <td className="px-4 py-3">
                                <span className={risk.performance_vs_reference >= 0 ? 'text-green-600' : 'text-red-600'}>
                                  {risk.performance_vs_reference >= 0 ? '+' : ''}{risk.performance_vs_reference?.toFixed(2) || 'N/A'}%
                                </span>
                              </td>
                              <td className="px-4 py-3">
                                {risk.is_worst_performer ? (
                                  <span className="px-2 py-1 bg-red-100 text-red-800 text-xs font-semibold rounded">
                                    WORST PERFORMER
                                  </span>
                                ) : (
                                  <span className="px-2 py-1 bg-green-100 text-green-800 text-xs font-semibold rounded">
                                    OUTPERFORMING
                                  </span>
                                )}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Scenario Analysis */}
                <div className="bg-white rounded-xl shadow-lg p-6">
                  <h3 className="text-xl font-semibold mb-4 text-gray-800">Basket Scenario Analysis</h3>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {Object.entries(analysis.scenario_analysis).map(([scenarioName, scenarioData]) => (
                      <div key={scenarioName} className="bg-gray-50 rounded-lg p-4">
                        <h4 className="font-semibold text-gray-800 mb-3 capitalize">
                          {scenarioName.replace('_', ' ')}
                        </h4>
                        
                        {/* Basket Summary */}
                        <div className="mb-4 p-3 bg-white rounded border-l-4 border-blue-500">
                          <div className="text-sm font-semibold text-blue-800 mb-2">Basket Result</div>
                          <div className="space-y-1">
                            <div className="flex justify-between">
                              <span>Performance:</span>
                              <span className={`font-semibold ${scenarioData.basket_performance >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                {scenarioData.basket_performance >= 0 ? '+' : ''}{scenarioData.basket_performance?.toFixed(2) || 'N/A'}%
                              </span>
                            </div>
                            <div className="flex justify-between">
                              <span>Total Payoff:</span>
                              <span className="font-semibold">${scenarioData.payoff?.toFixed(4) || 'N/A'}</span>
                            </div>
                            <div className="flex justify-between">
                              <span>Total Return:</span>
                              <span className={`font-semibold ${scenarioData.total_return >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                {scenarioData.total_return >= 0 ? '+' : ''}{scenarioData.total_return?.toFixed(2) || 'N/A'}%
                              </span>
                            </div>
                            <div className="flex justify-between">
                              <span>Worst Performer:</span>
                              <span className="font-semibold text-red-600">{scenarioData.worst_performer || 'N/A'}</span>
                            </div>
                            <div className="text-xs text-gray-600 mt-2">
                              Type: {scenarioData.redemption_type?.replace('_', ' ') || 'N/A'}
                            </div>
                          </div>
                        </div>

                        {/* Individual Stock Performances */}
                        <div className="space-y-2">
                          <div className="text-sm font-semibold text-gray-700 mb-1">Individual Performances:</div>
                          {scenarioData.individual_performances && Object.entries(scenarioData.individual_performances).map(([symbol, performance]) => (
                            <div key={symbol} className="flex justify-between text-sm p-2 bg-white rounded">
                              <span className="font-medium">{symbol}:</span>
                              <span className={`font-semibold ${performance >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                {performance >= 0 ? '+' : ''}{performance?.toFixed(2) || 'N/A'}%
                              </span>
                            </div>
                          ))}
                        </div>
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
