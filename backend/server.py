from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd
import numpy as np
from openpyxl import Workbook
from openpyxl.chart import LineChart, Reference
from openpyxl.styles import Font, PatternFill, Alignment
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import seaborn as sns
import io
import base64
from scipy import stats
import json

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI(title="FCN Investment Analysis Calculator")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Ensure reports directory exists
REPORTS_DIR = ROOT_DIR / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

# Define Models
class StockInfo(BaseModel):
    symbol: str
    name: str
    current_price: float
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    dividend_yield: Optional[float] = None
    beta: Optional[float] = None
    exchange: str

class FCNParameters(BaseModel):
    coupon_rate: float  # Annual coupon rate (e.g., 5.5 for 5.5%)
    face_value: float  # Face value of the note
    maturity_months: int  # Maturity in months (FCNs typically use monthly terms)
    reference_price: float  # Initial fixing price of the underlying stock
    strike_price: float  # Strike price for payoff determination (often same as reference price)
    knock_out_barrier_pct: float  # Knock-out barrier as % of reference price (e.g., 110.0 for 110%)
    knock_in_barrier_pct: float  # Knock-in barrier as % of reference price (e.g., 70.0 for 70%)
    barrier_style: str = "american"  # "american" (continuous monitoring) or "european" (observation dates only)
    observation_frequency: str = "monthly"  # monthly, weekly, daily
    autocallable: bool = True  # Whether the note can be called early on knock-out

class FCNAnalysisRequest(BaseModel):
    symbols: List[str]  # List of stock symbols
    fcn_params: FCNParameters
    analysis_period: int = 252  # Trading days for historical analysis
    scenarios: Dict[str, float] = Field(default_factory=lambda: {
        "base_case": 0.0,
        "bull_case": 0.15,
        "bear_case": -0.20
    })

class FCNAnalysisResult(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    request_params: FCNAnalysisRequest
    stocks_info: List[StockInfo]
    fcn_metrics: Dict[str, Any]
    scenario_analysis: Dict[str, Any]
    risk_metrics: Dict[str, Any]
    charts: Dict[str, str]  # Base64 encoded charts
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ReportRequest(BaseModel):
    analysis_id: str
    report_type: str  # "excel" or "powerpoint"
    include_charts: bool = True

# FCN Calculation Functions
def calculate_fcn_payoff(final_price: float, reference_price: float, strike_price: float,
                        knock_out_barrier_pct: float, knock_in_barrier_pct: float, 
                        coupon_rate: float, face_value: float, maturity_months: int,
                        barrier_breached: Dict[str, bool], early_redemption_month: Optional[int] = None) -> Dict[str, float]:
    """Calculate FCN payoff based on proper FCN structure with reference price"""
    
    # Calculate actual barrier levels from reference price
    knock_out_barrier = reference_price * (knock_out_barrier_pct / 100)
    knock_in_barrier = reference_price * (knock_in_barrier_pct / 100)
    
    # Monthly coupon
    monthly_coupon = face_value * (coupon_rate / 100) / 12
    
    if early_redemption_month:
        # Early redemption due to knock-out
        total_coupons = monthly_coupon * early_redemption_month
        return {
            "payoff": face_value + total_coupons,
            "total_return": (total_coupons) / face_value * 100,
            "coupons_received": total_coupons,
            "redemption_type": "early_knockout"
        }
    
    # Calculate total coupons for full term
    total_coupons = monthly_coupon * maturity_months
    
    if not barrier_breached["knock_in"]:
        # No knock-in occurred, receive face value + all coupons
        return {
            "payoff": face_value + total_coupons,
            "total_return": (total_coupons) / face_value * 100,
            "coupons_received": total_coupons,
            "redemption_type": "full_term_protected"
        }
    else:
        # Knock-in occurred, equity exposure based on performance vs strike
        equity_performance = final_price / strike_price
        equity_payoff = face_value * equity_performance
        
        return {
            "payoff": equity_payoff + total_coupons,
            "total_return": (equity_payoff + total_coupons - face_value) / face_value * 100,
            "coupons_received": total_coupons,
            "equity_performance": (equity_performance - 1) * 100,
            "redemption_type": "equity_exposure"
        }

def calculate_fcn_metrics(current_price: float, fcn_params: FCNParameters) -> Dict[str, float]:
    """Calculate FCN-specific metrics based on reference price"""
    
    # Calculate actual barrier levels from reference price percentages
    knock_out_barrier = fcn_params.reference_price * (fcn_params.knock_out_barrier_pct / 100)
    knock_in_barrier = fcn_params.reference_price * (fcn_params.knock_in_barrier_pct / 100)
    
    # Distance to barriers from current price
    distance_to_knockout = ((knock_out_barrier - current_price) / current_price) * 100
    distance_to_knockin = ((current_price - knock_in_barrier) / current_price) * 100
    
    # Performance vs reference price
    performance_vs_reference = (current_price / fcn_params.reference_price - 1) * 100
    
    # Moneyness relative to strike
    moneyness = (current_price / fcn_params.strike_price - 1) * 100
    
    # Annual coupon yield
    current_yield = fcn_params.coupon_rate
    
    # Maximum return if held to maturity (no knock-in)
    max_return = (fcn_params.coupon_rate / 12) * fcn_params.maturity_months
    
    return {
        "current_yield": current_yield,
        "distance_to_knockout": distance_to_knockout,
        "distance_to_knockin": distance_to_knockin,
        "performance_vs_reference": performance_vs_reference,
        "moneyness": moneyness,
        "max_return_no_knockin": max_return,
        "reference_price": fcn_params.reference_price,
        "knockout_barrier": knock_out_barrier,
        "knockin_barrier": knock_in_barrier,
        "knockout_barrier_pct": fcn_params.knock_out_barrier_pct,
        "knockin_barrier_pct": fcn_params.knock_in_barrier_pct,
        "monthly_coupon": fcn_params.face_value * (fcn_params.coupon_rate / 100) / 12
    }

def monte_carlo_simulation(stock_prices: pd.DataFrame, fcn_params: FCNParameters, 
                          num_simulations: int = 10000) -> Dict[str, Any]:
    """Run Monte Carlo simulation for FCN analysis with proper barrier monitoring"""
    results = []
    
    # Calculate actual barrier levels from reference price
    knock_out_barrier = fcn_params.reference_price * (fcn_params.knock_out_barrier_pct / 100)
    knock_in_barrier = fcn_params.reference_price * (fcn_params.knock_in_barrier_pct / 100)
    
    for symbol in stock_prices.columns:
        returns = stock_prices[symbol].pct_change().dropna()
        initial_price = fcn_params.reference_price  # Use reference price as starting point
        
        mu = returns.mean() * 252  # Annualized return
        sigma = returns.std() * np.sqrt(252)  # Annualized volatility
        
        # Monte Carlo simulation
        payoffs = []
        knock_in_events = 0
        knock_out_events = 0
        early_redemptions = []
        
        for sim in range(num_simulations):
            # Generate price path for the FCN term
            days = int(fcn_params.maturity_months * 21)  # Approximate trading days per month
            dt = 1/252  # Daily time step
            
            price_path = [initial_price]
            knocked_in = False
            knocked_out = False
            redemption_month = None
            
            for day in range(days):
                random_shock = np.random.normal(0, 1)
                price_change = mu * dt + sigma * np.sqrt(dt) * random_shock
                new_price = price_path[-1] * np.exp(price_change)
                price_path.append(new_price)
                
                # Check barriers based on style
                current_month = int(day / 21) + 1  # Current month
                
                if fcn_params.barrier_style == "american" or (
                    fcn_params.barrier_style == "european" and day % 21 == 0
                ):
                    # Check knock-out barrier
                    if new_price >= knock_out_barrier and fcn_params.autocallable:
                        knocked_out = True
                        redemption_month = current_month
                        knock_out_events += 1
                        break
                    
                    # Check knock-in barrier
                    if new_price <= knock_in_barrier:
                        knocked_in = True
                        knock_in_events += 1
            
            final_price = price_path[-1]
            
            # Calculate FCN payoff
            payoff_result = calculate_fcn_payoff(
                final_price=final_price,
                reference_price=fcn_params.reference_price,
                strike_price=fcn_params.strike_price,
                knock_out_barrier_pct=fcn_params.knock_out_barrier_pct,
                knock_in_barrier_pct=fcn_params.knock_in_barrier_pct,
                coupon_rate=fcn_params.coupon_rate,
                face_value=fcn_params.face_value,
                maturity_months=fcn_params.maturity_months,
                barrier_breached={"knock_in": knocked_in, "knock_out": knocked_out},
                early_redemption_month=redemption_month
            )
            
            payoffs.append(payoff_result["payoff"])
            if redemption_month:
                early_redemptions.append(redemption_month)
        
        # Calculate statistics
        avg_redemption_month = np.mean(early_redemptions) if early_redemptions else fcn_params.maturity_months
        
        results.append({
            'symbol': symbol,
            'reference_price': fcn_params.reference_price,
            'expected_payoff': np.mean(payoffs),
            'payoff_std': np.std(payoffs),
            'knock_in_probability': knock_in_events / num_simulations * 100,
            'knock_out_probability': knock_out_events / num_simulations * 100,
            'avg_redemption_month': avg_redemption_month,
            'var_95': np.percentile(payoffs, 5),
            'var_99': np.percentile(payoffs, 1),
            'max_payoff': np.max(payoffs),
            'min_payoff': np.min(payoffs)
        })
    
    return results

def create_price_chart(stock_prices: pd.DataFrame) -> str:
    """Create price chart and return as base64 string"""
    plt.figure(figsize=(12, 6))
    for symbol in stock_prices.columns:
        plt.plot(stock_prices.index, stock_prices[symbol], label=symbol, linewidth=2)
    
    plt.title('Stock Price History', fontsize=16, fontweight='bold')
    plt.xlabel('Date', fontsize=12)
    plt.ylabel('Price ($)', fontsize=12)
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    # Convert to base64
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode()
    plt.close()
    
    return image_base64

def create_payoff_distribution_chart(monte_carlo_results: List[Dict]) -> str:
    """Create payoff distribution chart"""
    fig, axes = plt.subplots(len(monte_carlo_results), 1, figsize=(10, 6*len(monte_carlo_results)))
    if len(monte_carlo_results) == 1:
        axes = [axes]
    
    for i, result in enumerate(monte_carlo_results):
        # This is simplified - in real implementation you'd store the full payoff distribution
        ax = axes[i] if len(monte_carlo_results) > 1 else axes[0]
        
        # Create sample distribution for visualization
        mean_payoff = result['expected_payoff']
        std_payoff = result['payoff_std']
        sample_payoffs = np.random.normal(mean_payoff, std_payoff, 1000)
        
        ax.hist(sample_payoffs, bins=50, alpha=0.7, edgecolor='black')
        ax.axvline(mean_payoff, color='red', linestyle='--', linewidth=2, label=f'Mean: ${mean_payoff:.2f}')
        ax.set_title(f'FCN Payoff Distribution - {result["symbol"]}', fontsize=14, fontweight='bold')
        ax.set_xlabel('Payoff ($)', fontsize=12)
        ax.set_ylabel('Frequency', fontsize=12)
        ax.legend()
        ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode()
    plt.close()
    
    return image_base64

# API Routes
@api_router.get("/")
async def root():
    return {"message": "FCN Investment Analysis Calculator API"}

@api_router.get("/stock/{symbol}")
async def get_stock_info(symbol: str):
    """Get current stock information"""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        hist = ticker.history(period="1d")
        
        if hist.empty:
            raise HTTPException(status_code=404, detail=f"Stock symbol {symbol} not found")
        
        current_price = hist['Close'].iloc[-1]
        
        stock_info = StockInfo(
            symbol=symbol.upper(),
            name=info.get('longName', symbol),
            current_price=float(current_price),
            market_cap=info.get('marketCap'),
            pe_ratio=info.get('forwardPE'),
            dividend_yield=info.get('dividendYield'),
            beta=info.get('beta'),
            exchange=info.get('exchange', 'Unknown')
        )
        
        return stock_info
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error fetching stock data: {str(e)}")

@api_router.post("/analyze", response_model=FCNAnalysisResult)
async def analyze_fcn(request: FCNAnalysisRequest):
    """Perform comprehensive FCN analysis"""
    try:
        # Fetch stock data
        stocks_info = []
        stock_prices = pd.DataFrame()
        
        for symbol in request.symbols:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # Get historical data
            hist = ticker.history(period=f"{request.analysis_period}d")
            if hist.empty:
                raise HTTPException(status_code=404, detail=f"No data found for {symbol}")
            
            stock_prices[symbol] = hist['Close']
            
            # Get current stock info
            current_price = hist['Close'].iloc[-1]
            stock_info = StockInfo(
                symbol=symbol.upper(),
                name=info.get('longName', symbol),
                current_price=float(current_price),
                market_cap=info.get('marketCap'),
                pe_ratio=info.get('forwardPE'),
                dividend_yield=info.get('dividendYield'),
                beta=info.get('beta'),
                exchange=info.get('exchange', 'Unknown')
            )
            stocks_info.append(stock_info)
        
        # Calculate FCN metrics for each stock
        fcn_metrics = {}
        for symbol in request.symbols:
            current_price = stock_prices[symbol].iloc[-1]
            
            metrics = calculate_fcn_metrics(current_price, request.fcn_params)
            fcn_metrics[symbol] = metrics
        
        # Monte Carlo simulation
        monte_carlo_results = monte_carlo_simulation(stock_prices, request.fcn_params)
        
        # Scenario analysis with proper FCN calculations
        scenario_analysis = {}
        for scenario_name, return_pct in request.scenarios.items():
            scenario_results = {}
            for symbol in request.symbols:
                current_price = stock_prices[symbol].iloc[-1]
                future_price = request.fcn_params.reference_price * (1 + return_pct)  # Apply scenario to reference price
                
                # Calculate barriers for scenario
                knock_out_barrier = request.fcn_params.reference_price * (request.fcn_params.knock_out_barrier_pct / 100)
                knock_in_barrier = request.fcn_params.reference_price * (request.fcn_params.knock_in_barrier_pct / 100)
                
                # For scenario analysis, assume no early redemption
                payoff_result = calculate_fcn_payoff(
                    final_price=future_price,
                    reference_price=request.fcn_params.reference_price,
                    strike_price=request.fcn_params.strike_price,
                    knock_out_barrier_pct=request.fcn_params.knock_out_barrier_pct,
                    knock_in_barrier_pct=request.fcn_params.knock_in_barrier_pct,
                    coupon_rate=request.fcn_params.coupon_rate,
                    face_value=request.fcn_params.face_value,
                    maturity_months=request.fcn_params.maturity_months,
                    barrier_breached={
                        "knock_in": future_price <= knock_in_barrier,
                        "knock_out": future_price >= knock_out_barrier
                    },
                    early_redemption_month=None
                )
                
                scenario_results[symbol] = {
                    "future_price": future_price,
                    "payoff": payoff_result["payoff"],
                    "total_return": payoff_result["total_return"],
                    "coupons_received": payoff_result["coupons_received"],
                    "redemption_type": payoff_result["redemption_type"]
                }
            
            scenario_analysis[scenario_name] = scenario_results
        
        # Risk metrics
        risk_metrics = {}
        for result in monte_carlo_results:
            symbol = result['symbol']
            returns = stock_prices[symbol].pct_change().dropna()
            
            risk_metrics[symbol] = {
                "volatility_annualized": returns.std() * np.sqrt(252) * 100,
                "sharpe_ratio": (returns.mean() * 252) / (returns.std() * np.sqrt(252)),
                "max_drawdown": ((stock_prices[symbol] / stock_prices[symbol].cummax()) - 1).min() * 100,
                "var_95": result['var_95'],
                "var_99": result['var_99'],
                "expected_payoff": result['expected_payoff'],
                "knock_in_probability": result['knock_in_probability'],
                "knock_out_probability": result['knock_out_probability'],
                "avg_redemption_month": result['avg_redemption_month'],
                "max_payoff": result['max_payoff'],
                "min_payoff": result['min_payoff']
            }
        
        # Create charts
        price_chart = create_price_chart(stock_prices)
        payoff_chart = create_payoff_distribution_chart(monte_carlo_results)
        
        charts = {
            "price_history": price_chart,
            "payoff_distribution": payoff_chart
        }
        
        # Create analysis result
        analysis = FCNAnalysisResult(
            request_params=request,
            stocks_info=stocks_info,
            fcn_metrics=fcn_metrics,
            scenario_analysis=scenario_analysis,
            risk_metrics=risk_metrics,
            charts=charts
        )
        
        # Save to database
        await db.fcn_analyses.insert_one(analysis.dict())
        
        return analysis
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis error: {str(e)}")

@api_router.get("/analysis/{analysis_id}")
async def get_analysis(analysis_id: str):
    """Get saved analysis by ID"""
    analysis = await db.fcn_analyses.find_one({"id": analysis_id})
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    return FCNAnalysisResult(**analysis)

@api_router.get("/analyses")
async def list_analyses(limit: int = 20):
    """List recent analyses"""
    analyses = await db.fcn_analyses.find().sort("created_at", -1).limit(limit).to_list(limit)
    return [{"id": a["id"], "created_at": a["created_at"], "symbols": a["request_params"]["symbols"]} for a in analyses]

def create_excel_report(analysis: FCNAnalysisResult, file_path: Path):
    """Create Excel report"""
    wb = Workbook()
    
    # Summary sheet
    ws_summary = wb.active
    ws_summary.title = "Executive Summary"
    
    # Header styling
    header_font = Font(bold=True, size=14)
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    
    # Title
    ws_summary['A1'] = "FCN Investment Analysis Report"
    ws_summary['A1'].font = Font(bold=True, size=16)
    ws_summary.merge_cells('A1:F1')
    
    # Analysis parameters
    row = 3
    ws_summary[f'A{row}'] = "Analysis Parameters"
    ws_summary[f'A{row}'].font = header_font
    row += 1
    
    params = analysis.request_params.fcn_params
    ws_summary[f'A{row}'] = "Coupon Rate:"
    ws_summary[f'B{row}'] = f"{params.coupon_rate}%"
    row += 1
    ws_summary[f'A{row}'] = "Face Value:"
    ws_summary[f'B{row}'] = f"${params.face_value:,.2f}"
    row += 1
    ws_summary[f'A{row}'] = "Maturity:"
    ws_summary[f'B{row}'] = f"{params.maturity_years} years"
    row += 1
    ws_summary[f'A{row}'] = "Barrier Level:"
    ws_summary[f'B{row}'] = f"{params.barrier_level}%"
    row += 2
    
    # Stock information
    ws_summary[f'A{row}'] = "Underlying Stocks"
    ws_summary[f'A{row}'].font = header_font
    row += 1
    
    headers = ["Symbol", "Name", "Current Price", "Market Cap", "P/E Ratio"]
    for col, header in enumerate(headers, 1):
        ws_summary.cell(row=row, column=col, value=header).font = Font(bold=True)
    row += 1
    
    for stock in analysis.stocks_info:
        ws_summary.cell(row=row, column=1, value=stock.symbol)
        ws_summary.cell(row=row, column=2, value=stock.name)
        ws_summary.cell(row=row, column=3, value=f"${stock.current_price:.2f}")
        ws_summary.cell(row=row, column=4, value=stock.market_cap if stock.market_cap else "N/A")
        ws_summary.cell(row=row, column=5, value=stock.pe_ratio if stock.pe_ratio else "N/A")
        row += 1
    
    # FCN Metrics sheet
    ws_metrics = wb.create_sheet("FCN Metrics")
    row = 1
    ws_metrics[f'A{row}'] = "FCN Performance Metrics"
    ws_metrics[f'A{row}'].font = Font(bold=True, size=14)
    row += 2
    
    headers = ["Symbol", "Current Yield", "YTM", "Barrier Price", "Distance to Barrier"]
    for col, header in enumerate(headers, 1):
        ws_metrics.cell(row=row, column=col, value=header).font = Font(bold=True)
    row += 1
    
    for symbol, metrics in analysis.fcn_metrics.items():
        ws_metrics.cell(row=row, column=1, value=symbol)
        ws_metrics.cell(row=row, column=2, value=f"{metrics['current_yield']:.2f}%")
        ws_metrics.cell(row=row, column=3, value=f"{metrics['yield_to_maturity']:.2f}%")
        ws_metrics.cell(row=row, column=4, value=f"${metrics['barrier_price']:.2f}")
        ws_metrics.cell(row=row, column=5, value=f"{metrics['distance_to_barrier']:.2f}%")
        row += 1
    
    # Risk Analysis sheet
    ws_risk = wb.create_sheet("Risk Analysis")
    row = 1
    ws_risk[f'A{row}'] = "Risk Metrics"
    ws_risk[f'A{row}'].font = Font(bold=True, size=14)
    row += 2
    
    headers = ["Symbol", "Volatility", "Sharpe Ratio", "Max Drawdown", "VaR 95%", "VaR 99%", "Knock-in Prob"]
    for col, header in enumerate(headers, 1):
        ws_risk.cell(row=row, column=col, value=header).font = Font(bold=True)
    row += 1
    
    for symbol, risk in analysis.risk_metrics.items():
        ws_risk.cell(row=row, column=1, value=symbol)
        ws_risk.cell(row=row, column=2, value=f"{risk['volatility_annualized']:.2f}%")
        ws_risk.cell(row=row, column=3, value=f"{risk['sharpe_ratio']:.2f}")
        ws_risk.cell(row=row, column=4, value=f"{risk['max_drawdown']:.2f}%")
        ws_risk.cell(row=row, column=5, value=f"${risk['var_95']:.2f}")
        ws_risk.cell(row=row, column=6, value=f"${risk['var_99']:.2f}")
        ws_risk.cell(row=row, column=7, value=f"{risk['knock_in_probability']:.2f}%")
        row += 1
    
    wb.save(file_path)

def create_powerpoint_report(analysis: FCNAnalysisResult, file_path: Path):
    """Create PowerPoint presentation"""
    prs = Presentation()
    
    # Title slide
    slide_layout = prs.slide_layouts[0]  # Title slide layout
    slide = prs.slides.add_slide(slide_layout)
    title = slide.shapes.title
    subtitle = slide.placeholders[1]
    
    title.text = "FCN Investment Analysis"
    subtitle.text = f"Analysis Date: {analysis.created_at.strftime('%B %d, %Y')}\nUnderlying Assets: {', '.join([s.symbol for s in analysis.stocks_info])}"
    
    # Executive Summary slide
    slide_layout = prs.slide_layouts[1]  # Title and Content layout
    slide = prs.slides.add_slide(slide_layout)
    title = slide.shapes.title
    content = slide.placeholders[1]
    
    title.text = "Executive Summary"
    
    params = analysis.request_params.fcn_params
    summary_text = f"""
    FCN Structure:
    • Coupon Rate: {params.coupon_rate}% per annum
    • Face Value: ${params.face_value:,.2f}
    • Maturity: {params.maturity_years} years
    • Barrier Level: {params.barrier_level}% of initial price
    
    Key Findings:
    • {len(analysis.stocks_info)} underlying stocks analyzed
    • Monte Carlo simulation with 10,000 scenarios
    • Comprehensive risk and scenario analysis performed
    """
    
    content.text = summary_text
    
    # Stock Analysis slide
    slide = prs.slides.add_slide(slide_layout)
    title = slide.shapes.title
    content = slide.placeholders[1]
    
    title.text = "Underlying Stock Analysis"
    
    stock_text = "Current Stock Positions:\n\n"
    for stock in analysis.stocks_info:
        stock_text += f"• {stock.symbol} ({stock.name})\n"
        stock_text += f"  Current Price: ${stock.current_price:.2f}\n"
        if stock.pe_ratio:
            stock_text += f"  P/E Ratio: {stock.pe_ratio:.2f}\n"
        stock_text += "\n"
    
    content.text = stock_text
    
    # FCN Metrics slide
    slide = prs.slides.add_slide(slide_layout)
    title = slide.shapes.title
    content = slide.placeholders[1]
    
    title.text = "FCN Performance Metrics"
    
    metrics_text = "Key Performance Indicators:\n\n"
    for symbol, metrics in analysis.fcn_metrics.items():
        metrics_text += f"• {symbol}:\n"
        metrics_text += f"  Current Yield: {metrics['current_yield']:.2f}%\n"
        metrics_text += f"  Yield to Maturity: {metrics['yield_to_maturity']:.2f}%\n"
        metrics_text += f"  Distance to Barrier: {metrics['distance_to_barrier']:.2f}%\n\n"
    
    content.text = metrics_text
    
    # Risk Analysis slide
    slide = prs.slides.add_slide(slide_layout)
    title = slide.shapes.title
    content = slide.placeholders[1]
    
    title.text = "Risk Analysis"
    
    risk_text = "Risk Assessment Summary:\n\n"
    for symbol, risk in analysis.risk_metrics.items():
        risk_text += f"• {symbol}:\n"
        risk_text += f"  Annual Volatility: {risk['volatility_annualized']:.2f}%\n"
        risk_text += f"  Knock-in Probability: {risk['knock_in_probability']:.2f}%\n"
        risk_text += f"  Expected Payoff: ${risk['expected_payoff']:.2f}\n\n"
    
    content.text = risk_text
    
    # Scenario Analysis slide
    slide = prs.slides.add_slide(slide_layout)
    title = slide.shapes.title
    content = slide.placeholders[1]
    
    title.text = "Scenario Analysis"
    
    scenario_text = "Investment Scenarios:\n\n"
    for scenario_name, scenario_data in analysis.scenario_analysis.items():
        scenario_text += f"{scenario_name.replace('_', ' ').title()}:\n"
        for symbol, data in scenario_data.items():
            scenario_text += f"• {symbol}: ${data['payoff']:.2f} ({data['return_pct']:+.2f}%)\n"
        scenario_text += "\n"
    
    content.text = scenario_text
    
    prs.save(file_path)

@api_router.post("/generate-report")
async def generate_report(request: ReportRequest, background_tasks: BackgroundTasks):
    """Generate Excel or PowerPoint report"""
    try:
        # Get analysis data
        analysis_data = await db.fcn_analyses.find_one({"id": request.analysis_id})
        if not analysis_data:
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        analysis = FCNAnalysisResult(**analysis_data)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        symbols_str = "_".join([s.symbol for s in analysis.stocks_info])
        
        if request.report_type == "excel":
            filename = f"FCN_Analysis_{symbols_str}_{timestamp}.xlsx"
            file_path = REPORTS_DIR / filename
            create_excel_report(analysis, file_path)
        elif request.report_type == "powerpoint":
            filename = f"FCN_Presentation_{symbols_str}_{timestamp}.pptx"
            file_path = REPORTS_DIR / filename
            create_powerpoint_report(analysis, file_path)
        else:
            raise HTTPException(status_code=400, detail="Invalid report type")
        
        return {"filename": filename, "download_url": f"/api/download/{filename}"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation error: {str(e)}")

@api_router.get("/download/{filename}")
async def download_report(filename: str):
    """Download generated report"""
    file_path = REPORTS_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type='application/octet-stream'
    )

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
