"""
Dataset loader and preprocessor for BudgetWise personal finance dataset.
Loads CSV, cleans data, and prepares for ML models.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.preprocessing import MinMaxScaler
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class DatasetLoader:
    """Handles loading and preprocessing of the personal finance dataset."""
    
    def __init__(self, dataset_path: str):
        self.dataset_path = Path(dataset_path)
        self.df_expenses = None
        self.df_aggregated = None
        self.scaler = MinMaxScaler()
        
    def load_and_preprocess(self):
        """
        Load dataset from CSV and preprocess.
        
        Raises:
            FileNotFoundError: If dataset file doesn't exist
            ValueError: If dataset is empty or corrupt
        """
        # Check file exists
        if not self.dataset_path.exists():
            raise FileNotFoundError(
                f"Dataset file not found at '{self.dataset_path}'. "
                f"Please place the BudgetWise CSV file at this location before starting the server."
            )
        
        logger.info(f"Loading dataset from {self.dataset_path}")
        
        try:
            # Load CSV
            df = pd.read_csv(self.dataset_path)
            
            if df.empty:
                raise ValueError("Dataset is empty")
            
            logger.info(f"Loaded {len(df)} rows from dataset")
            
            # Preprocess
            df = self._clean_data(df)
            df = self._parse_dates(df)
            df = self._sort_by_date(df)
            
            self.df_expenses = df
            
            # Create aggregated time series
            self.df_aggregated = self._aggregate_time_series(df)
            
            # Normalize aggregated data
            if not self.df_aggregated.empty:
                self._normalize_data()
            
            logger.info(f"Preprocessing complete: {len(self.df_expenses)} expenses, {len(self.df_aggregated)} time periods")
            
            return self.df_expenses, self.df_aggregated
            
        except pd.errors.EmptyDataError:
            raise ValueError("Dataset file is empty or corrupt. Could not parse CSV.")
        except Exception as e:
            logger.error(f"Error loading dataset: {e}")
            raise ValueError(f"Failed to load dataset: {str(e)}")
    
    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean data: remove nulls, duplicates, invalid values."""
        original_len = len(df)
        
        # Remove rows with missing critical columns
        df = df.dropna(subset=['amount'])
        
        # Remove duplicates
        df = df.drop_duplicates()
        
        # Ensure amount is numeric and positive
        df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
        df = df[df['amount'] > 0]
        
        # Fill missing descriptions
        if 'description' in df.columns:
            df['description'] = df['description'].fillna('Expense')
        
        # Fill missing categories
        if 'category' in df.columns:
            df['category'] = df['category'].fillna('Other')
        
        cleaned_len = len(df)
        logger.info(f"Cleaned data: {original_len} -> {cleaned_len} rows")
        
        return df
    
    def _parse_dates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Parse date column to datetime."""
        date_col = None
        
        # Find date column (common variations)
        for col in ['date', 'Date', 'transaction_date', 'txn_date', 'created_at']:
            if col in df.columns:
                date_col = col
                break
        
        if date_col is None:
            logger.warning("No date column found, using today's date")
            df['date'] = datetime.now().strftime('%Y-%m-%d')
        else:
            df['date'] = pd.to_datetime(df[date_col], errors='coerce')
            # Remove rows with invalid dates
            df = df.dropna(subset=['date'])
            # Convert to string format YYYY-MM-DD
            df['date'] = df['date'].dt.strftime('%Y-%m-%d')
        
        return df
    
    def _sort_by_date(self, df: pd.DataFrame) -> pd.DataFrame:
        """Sort by date ascending."""
        df = df.sort_values('date')
        df = df.reset_index(drop=True)
        return df
    
    def _aggregate_time_series(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Aggregate expenses into daily time series.
        Returns DataFrame with columns: date, total_amount
        """
        if df.empty:
            return pd.DataFrame(columns=['date', 'total_amount'])
        
        # Group by date and sum amounts
        daily = df.groupby('date')['amount'].sum().reset_index()
        daily.columns = ['date', 'total_amount']
        
        # Fill missing dates with 0
        daily['date'] = pd.to_datetime(daily['date'])
        date_range = pd.date_range(start=daily['date'].min(), end=daily['date'].max(), freq='D')
        full_range = pd.DataFrame({'date': date_range})
        daily = full_range.merge(daily, on='date', how='left')
        daily['total_amount'] = daily['total_amount'].fillna(0)
        
        # Convert date back to string
        daily['date'] = daily['date'].dt.strftime('%Y-%m-%d')
        
        return daily
    
    def _normalize_data(self):
        """Normalize aggregated time series using MinMaxScaler."""
        if self.df_aggregated.empty:
            return
        
        values = self.df_aggregated['total_amount'].values.reshape(-1, 1)
        self.scaler.fit(values)
        self.df_aggregated['normalized'] = self.scaler.transform(values)
        
        logger.info("Data normalized using MinMaxScaler")
    
    def validate_for_lstm(self, min_days: int = 14) -> tuple[bool, str]:
        """
        Validate if dataset is sufficient for LSTM training.
        
        Returns:
            (is_valid, message)
        """
        if self.df_aggregated is None or self.df_aggregated.empty:
            return False, "No aggregated time series data available"
        
        if len(self.df_aggregated) < min_days:
            return False, f"Insufficient time series data: {len(self.df_aggregated)} days found, {min_days} required for LSTM training"
        
        if self.df_aggregated['total_amount'].sum() == 0:
            return False, "All spending amounts are zero"
        
        return True, "Dataset valid for LSTM training"
    
    def validate_for_anomaly(self, min_rows: int = 50) -> tuple[bool, str]:
        """
        Validate if dataset is sufficient for anomaly detection.
        
        Returns:
            (is_valid, message)
        """
        if self.df_expenses is None or self.df_expenses.empty:
            return False, "No expense data available"
        
        if len(self.df_expenses) < min_rows:
            return False, f"Insufficient transactions: {len(self.df_expenses)} found, {min_rows} required for anomaly detection"
        
        # Check required columns
        required = ['amount', 'date']
        missing = [col for col in required if col not in self.df_expenses.columns]
        if missing:
            return False, f"Missing required columns: {missing}"
        
        return True, "Dataset valid for anomaly detection"
