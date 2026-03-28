from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict
import uuid
from datetime import datetime, timezone
import pandas as pd

# Load environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Imports
from data.loader import DatasetLoader
from services.insights_engine import InsightsEngine

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ==================== Data Store ====================

class DataStore:
    """In-memory data store."""
    df_expenses: Optional[pd.DataFrame] = None
    df_aggregated: Optional[pd.DataFrame] = None
    scaler = None
    loader: Optional[DatasetLoader] = None
    data_loaded: bool = False

    @classmethod
    def engine(cls) -> InsightsEngine:
        """Return a fresh InsightsEngine wired to current data."""
        return InsightsEngine(cls.df_expenses, cls.df_aggregated)

    @classmethod
    def get_expenses_list(cls) -> List[Dict]:
        if cls.df_expenses is None or cls.df_expenses.empty:
            return []
        expenses = []
        for _, row in cls.df_expenses.iterrows():
            eid = row.get('id')
            if pd.isna(eid) if isinstance(eid, float) else not eid:
                eid = str(uuid.uuid4())
            cat = row.get('created_at')
            if pd.isna(cat) if isinstance(cat, float) else not cat:
                cat = datetime.now(timezone.utc).isoformat()
            expenses.append({
                'id': str(eid),
                'amount': float(row['amount']),
                'category': str(row.get('category', 'Other')) if not (isinstance(row.get('category'), float) and pd.isna(row.get('category'))) else 'Other',
                'description': str(row.get('description', 'Expense')) if not (isinstance(row.get('description'), float) and pd.isna(row.get('description'))) else 'Expense',
                'date': str(row['date']),
                'created_at': str(cat),
            })
        return expenses

    @classmethod
    def add_expense(cls, data: Dict) -> Dict:
        if cls.df_expenses is None:
            return data
        if 'id' not in data:
            data['id'] = str(uuid.uuid4())
        if 'created_at' not in data:
            data['created_at'] = datetime.now(timezone.utc).isoformat()
        cls.df_expenses = pd.concat([cls.df_expenses, pd.DataFrame([data])], ignore_index=True)
        # Rebuild aggregated
        cls._rebuild_aggregated()
        return data

    @classmethod
    def delete_expense(cls, expense_id: str) -> bool:
        if cls.df_expenses is None:
            return False
        before = len(cls.df_expenses)
        mask = cls.df_expenses['id'].astype(str) == expense_id
        cls.df_expenses = cls.df_expenses[~mask]
        deleted = len(cls.df_expenses) < before
        if deleted:
            cls._rebuild_aggregated()
        return deleted

    @classmethod
    def _rebuild_aggregated(cls):
        """Rebuild time-series aggregation after data mutation."""
        if cls.df_expenses is None or cls.df_expenses.empty:
            cls.df_aggregated = pd.DataFrame(columns=['date', 'total_amount'])
            return
        df = cls.df_expenses.copy()
        daily = df.groupby('date')['amount'].sum().reset_index()
        daily.columns = ['date', 'total_amount']
        daily['date'] = pd.to_datetime(daily['date'])
        dr = pd.date_range(start=daily['date'].min(), end=daily['date'].max(), freq='D')
        full = pd.DataFrame({'date': dr})
        daily = full.merge(daily, on='date', how='left')
        daily['total_amount'] = daily['total_amount'].fillna(0)
        daily['date'] = daily['date'].dt.strftime('%Y-%m-%d')
        cls.df_aggregated = daily


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


# ==================== App & Router ====================

app = FastAPI(title="FinFusion API", version="2.0.0")
api_router = APIRouter(prefix="/api")


# ==================== Health ====================

@api_router.get("/health")
async def health():
    return {
        'data': {
            'ok': True,
            'data_loaded': DataStore.data_loaded,
            'expenses_count': len(DataStore.df_expenses) if DataStore.df_expenses is not None else 0,
        },
        'metadata': {'version': '2.0.0'},
        'error': None,
    }

@api_router.get("/")
async def root():
    return {
        'data': {'message': 'FinFusion API v2.0 — Data-driven insights'},
        'metadata': {},
        'error': None,
    }


# ==================== Expenses ====================

@api_router.post("/expenses", response_model=Expense)
async def create_expense(expense: ExpenseCreate):
    result = DataStore.add_expense(expense.model_dump())
    return Expense(**result)

@api_router.get("/expenses")
async def get_expenses():
    expenses = DataStore.get_expenses_list()
    return {
        'data': expenses,
        'metadata': {'count': len(expenses)},
        'error': None,
    }

@api_router.delete("/expenses/{expense_id}")
async def delete_expense(expense_id: str):
    deleted = DataStore.delete_expense(expense_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Expense not found")
    return {
        'data': {'deleted': True},
        'metadata': {},
        'error': None,
    }


# ==================== Analytics ====================

@api_router.get("/analytics/spending")
async def analytics_spending():
    """Spending analytics for the latest period, with month-over-month comparison."""
    return DataStore.engine().get_analytics()


# ==================== Insights / Suggestions ====================

@api_router.get("/suggestions")
async def suggestions():
    """
    Central insights endpoint.  All insights are computed by InsightsEngine.
    Returns structured insight objects — no static strings.
    """
    return DataStore.engine().get_insights()


# ==================== Forecast ====================

@api_router.get("/forecast")
async def forecast_simple():
    return DataStore.engine().get_forecast(days_ahead=30)

@api_router.get("/forecast/lstm")
async def forecast_lstm():
    """LSTM not trained — returns statistical fallback, clearly labeled."""
    return DataStore.engine().get_forecast(days_ahead=30)


# ==================== Budgets ====================

@api_router.get("/budget/smart")
async def get_smart_budget():
    return DataStore.engine().get_budgets()


# ==================== Anomalies ====================

@api_router.get("/expenses/anomalies")
async def get_anomalies():
    return DataStore.engine().get_anomalies()


# ==================== Startup / Shutdown ====================

@app.on_event("startup")
async def startup_event():
    logger.info("=" * 60)
    logger.info("FinFusion API v2.0 Starting...")
    logger.info("=" * 60)

    dataset_path = os.getenv('DATASET_PATH', './backend/data/budgetwise.csv')
    logger.info(f"Dataset path: {dataset_path}")

    try:
        DataStore.loader = DatasetLoader(dataset_path)
        df_expenses, df_aggregated = DataStore.loader.load_and_preprocess()

        DataStore.df_expenses = df_expenses
        DataStore.df_aggregated = df_aggregated
        DataStore.scaler = DataStore.loader.scaler
        DataStore.data_loaded = True

        logger.info(f"Dataset loaded: {len(df_expenses)} expenses, {len(df_aggregated)} time periods")
        logger.info(f"Date range: {df_expenses['date'].min()} to {df_expenses['date'].max()}")

        # Quick engine test
        engine = DataStore.engine()
        _ = engine.get_analytics()
        insight_count = len(engine.get_insights().get('data', []))
        logger.info(f"InsightsEngine ready — {insight_count} insights generated")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"FATAL: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("FinFusion API shutting down...")


# ==================== Router & CORS ====================

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)
