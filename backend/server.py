from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict
import uuid
from datetime import datetime, timezone, timedelta
import pandas as pd
import numpy as np

# Load environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Import data loader
from data.loader import DatasetLoader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== Global Data Store ====================

class DataStore:
    """In-memory data store for dataset and models."""
    # Data
    df_expenses: Optional[pd.DataFrame] = None
    df_aggregated: Optional[pd.DataFrame] = None
    scaler = None
    loader: Optional[DatasetLoader] = None
    
    # Models (will be populated by model training)
    lstm_model = None
    anomaly_model = None
    
    # Training status flags
    data_loaded: bool = False
    lstm_trained: bool = False
    anomaly_trained: bool = False
    
    # Validation thresholds
    min_rows_lstm: int = int(os.getenv('MIN_ROWS_FOR_LSTM', 14))
    min_rows_anomaly: int = int(os.getenv('MIN_ROWS_FOR_ANOMALY', 50))
    
    @classmethod
    def get_expenses_list(cls) -> List[Dict]:
        """Convert DataFrame to list of expense dictionaries."""
        if cls.df_expenses is None or cls.df_expenses.empty:
            return []
        
        expenses = []
        for idx, row in cls.df_expenses.iterrows():
            # Generate ID if not present or is NaN
            expense_id = row.get('id')
            if pd.isna(expense_id):
                expense_id = str(uuid.uuid4())
            
            # Get created_at or use current time
            created_at = row.get('created_at')
            if pd.isna(created_at):
                created_at = datetime.now(timezone.utc).isoformat()
            
            expense = {
                'id': str(expense_id),
                'amount': float(row['amount']),
                'category': str(row.get('category', 'Other')) if not pd.isna(row.get('category')) else 'Other',
                'description': str(row.get('description', 'Expense')) if not pd.isna(row.get('description')) else 'Expense',
                'date': str(row['date']),
                'created_at': str(created_at)
            }
            expenses.append(expense)
        
        return expenses
    
    @classmethod
    def add_expense(cls, expense_data: Dict) -> Dict:
        """Add new expense to DataFrame."""
        if cls.df_expenses is None:
            return expense_data
        
        # Add ID if not present
        if 'id' not in expense_data:
            expense_data['id'] = str(uuid.uuid4())
        
        # Add created_at if not present
        if 'created_at' not in expense_data:
            expense_data['created_at'] = datetime.now(timezone.utc).isoformat()
        
        # Convert to DataFrame row and append
        new_row = pd.DataFrame([expense_data])
        cls.df_expenses = pd.concat([cls.df_expenses, new_row], ignore_index=True)
        
        return expense_data
    
    @classmethod
    def delete_expense(cls, expense_id: str) -> bool:
        """Delete expense from DataFrame."""
        if cls.df_expenses is None:
            return False
        
        initial_len = len(cls.df_expenses)
        cls.df_expenses = cls.df_expenses[cls.df_expenses.get('id', pd.Series()) != expense_id]
        
        return len(cls.df_expenses) < initial_len


# Create FastAPI app
app = FastAPI(title="FinFusion API", version="1.0.0")
api_router = APIRouter(prefix="/api")

# ==================== Pydantic Models ====================

class Expense(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    amount: float
    category: str
    description: str
    date: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class ExpenseCreate(BaseModel):
    amount: float
    category: str
    description: str
    date: str

class Budget(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    category: str
    limit: float
    period: str  # 'monthly'
    ai_recommendation: bool
    basis: str = "historical_average"
    buffer_percent: int = 10
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

# ==================== Helper Functions ====================

def get_latest_month_from_dataset() -> str:
    """Get the latest month available in the dataset."""
    if DataStore.df_expenses is None or DataStore.df_expenses.empty:
        return datetime.now(timezone.utc).strftime("%Y-%m")
    
    # Get the latest date from dataset
    latest_date = pd.to_datetime(DataStore.df_expenses['date']).max()
    return latest_date.strftime("%Y-%m")

def get_category_spending(days: int = 30, use_latest_month: bool = True) -> List[Dict]:
    """Calculate spending by category for last N days or latest month in dataset."""
    if DataStore.df_expenses is None or DataStore.df_expenses.empty:
        return []
    
    df = DataStore.df_expenses.copy()
    
    if use_latest_month:
        # Use latest month from dataset instead of current date
        latest_month = get_latest_month_from_dataset()
        df['date_parsed'] = pd.to_datetime(df['date'])
        df = df[df['date_parsed'].dt.strftime("%Y-%m") == latest_month]
    else:
        # Use last N days from current date (original logic)
        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
        df = df[df['date'] >= cutoff_date]
    
    # Group by category
    category_totals = df.groupby('category')['amount'].sum().to_dict()
    
    return [{"category": k, "amount": float(v)} for k, v in category_totals.items()]

def get_ai_suggestions() -> List[str]:
    """Generate AI suggestions based on spending patterns."""
    if DataStore.df_expenses is None or DataStore.df_expenses.empty:
        return ["Start tracking expenses to get personalized suggestions!"]
    
    try:
        df = DataStore.df_expenses
        suggestions = []
        
        # Category analysis
        category_spending = df.groupby('category')['amount'].sum().to_dict()
        if category_spending:
            highest_cat = max(category_spending.items(), key=lambda x: x[1])
            suggestions.append(
                f"Your highest spending is in {highest_cat[0]} (₹{highest_cat[1]:.2f}). Consider setting a limit."
            )
        
        # Small purchases
        small_purchases = df[df['amount'] < 200]
        if len(small_purchases) > 10:
            total_small = small_purchases['amount'].sum()
            suggestions.append(
                f"You have {len(small_purchases)} small purchases totaling ₹{total_small:.2f}. These add up quickly!"
            )
        
        # Average daily spend
        if 'date' in df.columns:
            unique_days = df['date'].nunique()
            total_spending = df['amount'].sum()
            avg_daily = total_spending / max(unique_days, 1)
            suggestions.append(
                f"Your average daily spend is ₹{avg_daily:.0f}. A daily cap can help rein it in."
            )
        
        return suggestions[:4]
    
    except Exception as e:
        logger.error(f"AI suggestions error: {e}")
        return [
            "Track your daily expenses to identify spending patterns.",
            "Review subscriptions and cancel unused ones.",
            "Cook at home more often to reduce food costs.",
            "Set specific budget limits per category."
        ]

def generate_simple_forecast(days_ahead: int = 30) -> Dict:
    """Simple forecasting using moving average (fallback method)."""
    if DataStore.df_aggregated is None or DataStore.df_aggregated.empty:
        return {
            "forecast": [],
            "trend": "insufficient_data",
            "confidence": 0.0,
            "fallback": True,
            "error": "No time-series data available for forecasting",
            "metadata": {"method": "none", "forecast_days": days_ahead}
        }
    
    try:
        # Use last 7 days average
        recent_data = DataStore.df_aggregated.tail(7)
        avg_amount = recent_data['total_amount'].mean()
        
        # Generate forecast
        forecast_data = []
        today = datetime.now(timezone.utc)
        
        for i in range(days_ahead):
            future_date = today + timedelta(days=i)
            forecast_data.append({
                "date": future_date.strftime("%Y-%m-%d"),
                "predicted_amount": round(float(avg_amount), 2)
            })
        
        # Simple trend
        if len(recent_data) >= 2:
            first_half = recent_data.head(len(recent_data) // 2)['total_amount'].mean()
            second_half = recent_data.tail(len(recent_data) // 2)['total_amount'].mean()
            
            if second_half > first_half * 1.1:
                trend = "increasing"
            elif second_half < first_half * 0.9:
                trend = "decreasing"
            else:
                trend = "stable"
        else:
            trend = "stable"
        
        return {
            "forecast": forecast_data,
            "trend": trend,
            "confidence": 0.45,
            "fallback": True,
            "error": "Using 7-day moving average (LSTM not trained)",
            "metadata": {
                "method": "moving_average",
                "training_days": len(recent_data),
                "forecast_days": days_ahead
            }
        }
    
    except Exception as e:
        logger.error(f"Fallback forecast error: {e}")
        return {
            "forecast": [],
            "trend": "error",
            "confidence": 0.0,
            "fallback": True,
            "error": str(e),
            "metadata": {"method": "error"}
        }

# ==================== API Routes ====================

@api_router.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "ok": True,
        "data_loaded": DataStore.data_loaded,
        "lstm_trained": DataStore.lstm_trained,
        "anomaly_trained": DataStore.anomaly_trained,
        "expenses_count": len(DataStore.df_expenses) if DataStore.df_expenses is not None else 0
    }

@api_router.get("/")
async def root():
    return {"message": "FinFusion API v1.0 - Dataset Mode"}

# ==================== Expenses Endpoints ====================

@api_router.post("/expenses", response_model=Expense)
async def create_expense(expense: ExpenseCreate):
    """Create new expense."""
    expense_dict = expense.model_dump()
    result = DataStore.add_expense(expense_dict)
    return Expense(**result)

@api_router.get("/expenses", response_model=List[Expense])
async def get_expenses():
    """Get all expenses."""
    expenses = DataStore.get_expenses_list()
    return expenses

@api_router.delete("/expenses/{expense_id}")
async def delete_expense(expense_id: str):
    """Delete expense by ID."""
    deleted = DataStore.delete_expense(expense_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Expense not found")
    return {"message": "Expense deleted"}

# ==================== Analytics Endpoints ====================

@api_router.get("/analytics/spending")
async def analytics_spending():
    """Get spending analytics for latest available month."""
    cs = get_category_spending(days=30, use_latest_month=True)
    total = sum(item['amount'] for item in cs)
    
    # Get latest month info
    latest_month = get_latest_month_from_dataset()
    month_start = f"{latest_month}-01"
    
    # Calculate month end
    if DataStore.df_expenses is not None and not DataStore.df_expenses.empty:
        df = DataStore.df_expenses.copy()
        df['date_parsed'] = pd.to_datetime(df['date'])
        month_data = df[df['date_parsed'].dt.strftime("%Y-%m") == latest_month]
        month_end = month_data['date'].max() if not month_data.empty else month_start
    else:
        month_end = month_start
    
    return {
        "total_monthly": round(total, 2),
        "by_category": cs,
        "error": None,
        "metadata": {
            "period_start": month_start,
            "period_end": month_end,
            "period_label": latest_month,
            "transaction_count": len(DataStore.df_expenses) if DataStore.df_expenses is not None else 0
        }
    }

@api_router.get("/suggestions")
async def suggestions():
    """Get AI suggestions."""
    return {"suggestions": get_ai_suggestions()}

# ==================== Forecast Endpoints ====================

@api_router.get("/forecast")
async def forecast_simple():
    """Simple forecast using linear regression (legacy endpoint)."""
    return generate_simple_forecast(days_ahead=30)

@api_router.get("/forecast/lstm")
async def forecast_lstm():
    """
    LSTM-based forecast endpoint.
    Returns consistent schema with fallback support.
    """
    if not DataStore.lstm_trained:
        # Return fallback response
        return generate_simple_forecast(days_ahead=30)
    
    # TODO: Will be implemented in Phase 2 with LSTM model
    return generate_simple_forecast(days_ahead=30)

# ==================== Budget Endpoints ====================

@api_router.get("/budget/smart")
async def get_smart_budget():
    """
    Auto-generate smart budgets based on spending patterns.
    Returns consistent schema with fallback support.
    """
    # Use latest month for budget calculation
    cs = get_category_spending(days=30, use_latest_month=True)
    
    if not cs:
        return {
            "budget": [],
            "total": 0,
            "current_spending": [],
            "fallback": True,
            "error": "No spending data available",
            "metadata": {"method": "none", "period": "monthly", "confidence": 0.0}
        }
    
    # Auto-generate budgets: average spending * 1.1 (10% buffer)
    budgets = []
    total_budget = 0
    current_spending = []
    
    for item in cs:
        # Set budget = current average * 1.1 (10% buffer)
        limit = round(item['amount'] * 1.1, 2)
        current = round(item['amount'], 2)
        
        budgets.append({
            "category": item['category'],
            "limit": limit,
            "current": current,
            "percentage": round((current / limit * 100) if limit > 0 else 0, 1),
            "basis": "historical_average",
            "buffer_percent": 10
        })
        
        current_spending.append({
            "category": item['category'],
            "amount": current
        })
        
        total_budget += limit
    
    method = "lstm_based" if DataStore.lstm_trained else "auto_generated"
    
    return {
        "budget": budgets,
        "total": round(total_budget, 2),
        "current_spending": current_spending,
        "fallback": not DataStore.lstm_trained,
        "error": "Auto-generated from spending patterns (avg × 1.1)" if not DataStore.lstm_trained else None,
        "metadata": {
            "method": method,
            "period": "monthly",
            "confidence": 0.85 if DataStore.lstm_trained else 0.65
        }
    }

# ==================== Anomaly Detection Endpoints ====================

@api_router.get("/expenses/anomalies")
async def get_anomalies():
    """
    Detect anomalies in expenses.
    Returns consistent schema with fallback support.
    """
    if DataStore.df_expenses is None or DataStore.df_expenses.empty:
        return {
            "alerts": [],
            "count": 0,
            "fallback": False,
            "error": "No expense data available",
            "metadata": {"method": "none", "total_transactions": 0, "contamination": 0.0}
        }
    
    if not DataStore.anomaly_trained:
        # Fallback: Use z-score method
        try:
            df = DataStore.df_expenses.copy()
            mean_amount = df['amount'].mean()
            std_amount = df['amount'].std()
            
            # Detect outliers (> 3 standard deviations)
            threshold = 3.0
            anomalies = []
            
            for _, row in df.iterrows():
                z_score = abs((row['amount'] - mean_amount) / std_amount) if std_amount > 0 else 0
                
                if z_score > threshold:
                    severity = "high" if z_score > 4 else "medium" if z_score > 3.5 else "low"
                    anomalies.append({
                        "expense_id": row.get('id', str(uuid.uuid4())),
                        "amount": float(row['amount']),
                        "category": row.get('category', 'Other'),
                        "date": str(row['date']),
                        "reason": "unusual_amount",
                        "anomaly_score": -float(z_score),  # Negative to match Isolation Forest convention
                        "severity": severity
                    })
            
            # Sort by severity and limit to top 10
            anomalies.sort(key=lambda x: x['anomaly_score'])
            anomalies = anomalies[:10]
            
            return {
                "alerts": anomalies,
                "count": len(anomalies),
                "fallback": True,
                "error": "Isolation Forest not trained, using z-score outlier detection (threshold=3.0)",
                "metadata": {
                    "method": "z_score",
                    "total_transactions": len(df),
                    "threshold": threshold
                }
            }
        
        except Exception as e:
            logger.error(f"Anomaly fallback error: {e}")
            return {
                "alerts": [],
                "count": 0,
                "fallback": True,
                "error": str(e),
                "metadata": {"method": "error"}
            }
    
    # TODO: Will be implemented in Phase 3 with Isolation Forest
    return {
        "alerts": [],
        "count": 0,
        "fallback": False,
        "error": None,
        "metadata": {"method": "isolation_forest", "total_transactions": len(DataStore.df_expenses)}
    }

# ==================== Startup/Shutdown Events ====================

@app.on_event("startup")
async def startup_event():
    """Load dataset and initialize models on startup."""
    logger.info("=" * 60)
    logger.info("FinFusion API Starting...")
    logger.info("=" * 60)
    
    # Get dataset path from environment
    dataset_path = os.getenv('DATASET_PATH', './backend/data/budgetwise.csv')
    logger.info(f"Dataset path: {dataset_path}")
    
    try:
        # Initialize loader
        DataStore.loader = DatasetLoader(dataset_path)
        
        # Load and preprocess dataset
        df_expenses, df_aggregated = DataStore.loader.load_and_preprocess()
        
        DataStore.df_expenses = df_expenses
        DataStore.df_aggregated = df_aggregated
        DataStore.scaler = DataStore.loader.scaler
        DataStore.data_loaded = True
        
        logger.info("✅ Dataset loaded successfully")
        logger.info(f"   - Total expenses: {len(df_expenses)}")
        logger.info(f"   - Time series days: {len(df_aggregated)}")
        logger.info(f"   - Date range: {df_expenses['date'].min()} to {df_expenses['date'].max()}")
        
        # Validate for LSTM
        lstm_valid, lstm_msg = DataStore.loader.validate_for_lstm(DataStore.min_rows_lstm)
        if lstm_valid:
            logger.info(f"✅ LSTM validation passed: {lstm_msg}")
            # TODO: Train LSTM model in Phase 2
            DataStore.lstm_trained = False
            logger.info("⚠️  LSTM model training not yet implemented (Phase 2)")
        else:
            logger.warning(f"⚠️  LSTM validation failed: {lstm_msg}")
            DataStore.lstm_trained = False
        
        # Validate for anomaly detection
        anomaly_valid, anomaly_msg = DataStore.loader.validate_for_anomaly(DataStore.min_rows_anomaly)
        if anomaly_valid:
            logger.info(f"✅ Anomaly detection validation passed: {anomaly_msg}")
            # TODO: Train Isolation Forest in Phase 3
            DataStore.anomaly_trained = False
            logger.info("⚠️  Anomaly detection model training not yet implemented (Phase 3)")
        else:
            logger.warning(f"⚠️  Anomaly detection validation failed: {anomaly_msg}")
            DataStore.anomaly_trained = False
        
        logger.info("=" * 60)
        logger.info("🚀 FinFusion API Ready")
        logger.info(f"   - Data loaded: {DataStore.data_loaded}")
        logger.info(f"   - LSTM trained: {DataStore.lstm_trained}")
        logger.info(f"   - Anomaly detection trained: {DataStore.anomaly_trained}")
        logger.info("=" * 60)
        
    except FileNotFoundError as e:
        logger.error("=" * 60)
        logger.error(f"❌ FATAL ERROR: {e}")
        logger.error("=" * 60)
        logger.error("Please download the BudgetWise dataset and place it at:")
        logger.error(f"   {dataset_path}")
        logger.error("")
        logger.error("Dataset source:")
        logger.error("   https://www.kaggle.com/datasets/mohammedarfathr/budgetwise-personal-finance-dataset")
        logger.error("=" * 60)
        raise
    
    except Exception as e:
        logger.error("=" * 60)
        logger.error(f"❌ FATAL ERROR during startup: {e}")
        logger.error("=" * 60)
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("FinFusion API shutting down...")

# ==================== Include Router & Middleware ====================

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)
