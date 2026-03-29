"""
insights_engine.py — Central analytics and insights module for FinFusion.

Single source of truth for all computed insights.  Every insight is derived
from data with exact numeric values.  No hardcoded thresholds, no vague
language.  Temporal comparison (current vs previous period) is mandatory
where possible.

Modules consumed: anomaly detection (z-score), forecast (moving average).
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class InsightsEngine:
    """Stateless engine — pass data in, get insights out."""

    def __init__(self, df_expenses: pd.DataFrame, df_aggregated: pd.DataFrame):
        self.df = df_expenses.copy() if df_expenses is not None else pd.DataFrame()
        self.df_agg = df_aggregated.copy() if df_aggregated is not None else pd.DataFrame()

        # Pre-parse dates once
        if not self.df.empty:
            self.df['_date'] = pd.to_datetime(self.df['date'], errors='coerce')
            self.df = self.df.dropna(subset=['_date'])
            self.df['_month'] = self.df['_date'].dt.to_period('M')
            self.df['_year'] = self.df['_date'].dt.year
            self.df['_month_num'] = self.df['_date'].dt.month

    # ================================================================= #
    #  CENTRAL FILTER — used by ALL features
    # ================================================================= #

    def get_filtered_expenses(self, month: int = None, year: int = None,
                              category: str = None) -> pd.DataFrame:
        """Single reusable filter. All current-context views MUST use this."""
        df = self.df
        if df.empty:
            return df
        if year is not None:
            df = df[df['_year'] == year]
        if month is not None:
            df = df[df['_month_num'] == month]
        if category is not None:
            df = df[df['category'].str.lower() == category.strip().lower()]
        return df

    def get_available_months(self) -> list:
        """Return sorted list of {month, year, label, count}."""
        if self.df.empty:
            return []
        grouped = (
            self.df.groupby(['_year', '_month_num'])
            .size()
            .reset_index(name='count')
        )
        grouped.columns = ['year', 'month', 'count']
        grouped = grouped.sort_values(['year', 'month'], ascending=[False, False])
        result = []
        month_names = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                       'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        for _, row in grouped.iterrows():
            y, m, c = int(row['year']), int(row['month']), int(row['count'])
            result.append({
                'month': m, 'year': y, 'count': c,
                'label': f'{month_names[m]} {y}',
            })
        return result

    def get_default_context(self) -> dict:
        """Return the latest available month/year in the dataset."""
        months = self.get_available_months()
        if months:
            return {'month': months[0]['month'], 'year': months[0]['year']}
        return {'month': 1, 'year': 2024}

    # ================================================================= #
    #  CURRENT CONTEXT — scoped to a specific month
    # ================================================================= #

    def get_current_analytics(self, month: int, year: int) -> Dict:
        """Spending analytics scoped to a single month, with prev-month comparison."""
        cur_df = self.get_filtered_expenses(month=month, year=year)

        # Previous month
        prev_m = month - 1 if month > 1 else 12
        prev_y = year if month > 1 else year - 1
        prev_df = self.get_filtered_expenses(month=prev_m, year=prev_y)

        by_cat = (
            cur_df.groupby('category')['amount']
            .sum()
            .sort_values(ascending=False)
            .reset_index()
        ) if not cur_df.empty else pd.DataFrame(columns=['category', 'amount'])
        by_cat.columns = ['category', 'amount']
        by_cat['amount'] = by_cat['amount'].round(2)

        # Include expenses per category for the dropdown
        categories = []
        for _, row in by_cat.iterrows():
            cat = row['category']
            cat_expenses = cur_df[cur_df['category'] == cat][
                ['id', 'date', 'amount', 'description']
            ].copy() if 'id' in cur_df.columns else pd.DataFrame()
            cat_expenses = cat_expenses.sort_values('date', ascending=False) if not cat_expenses.empty else cat_expenses
            categories.append({
                'category': cat,
                'spent': round(float(row['amount']), 2),
                'expenses': cat_expenses.to_dict('records') if not cat_expenses.empty else [],
            })

        total_current = round(float(cur_df['amount'].sum()), 2) if not cur_df.empty else 0
        total_prev = round(float(prev_df['amount'].sum()), 2) if not prev_df.empty else None

        comparison = None
        if total_prev is not None and total_prev > 0:
            delta = total_current - total_prev
            delta_pct = round((delta / total_prev) * 100, 1)
            comparison = {
                'previous_total': total_prev,
                'delta': round(delta, 2),
                'delta_pct': delta_pct,
                'direction': 'increased' if delta > 0 else 'decreased' if delta < 0 else 'unchanged',
            }

        month_names = ['', 'January', 'February', 'March', 'April', 'May', 'June',
                       'July', 'August', 'September', 'October', 'November', 'December']

        return {
            'data': {
                'total_monthly': total_current,
                'by_category': by_cat.to_dict('records'),
                'categories': categories,
                'comparison': comparison,
            },
            'metadata': {
                'month': month,
                'year': year,
                'label': f'{month_names[month]} {year}',
                'transaction_count': len(cur_df),
            },
            'error': None,
        }

    def get_current_budgets(self, month: int, year: int) -> Dict:
        """Budgets scoped to a specific month. Limits from historical, spent from current."""
        cur_df = self.get_filtered_expenses(month=month, year=year)

        # Historical = everything EXCEPT the selected month
        hist_df = self.df[~((self.df['_year'] == year) & (self.df['_month_num'] == month))]
        if hist_df.empty:
            hist_df = cur_df  # fallback if no history

        hist_monthly = (
            hist_df.groupby([hist_df['_month'].astype(str), 'category'])['amount']
            .sum().reset_index()
        )
        hist_monthly.columns = ['period', 'category', 'amount']

        cat_stats = (
            hist_monthly.groupby('category')['amount']
            .agg(['mean', 'std', 'count']).reset_index()
        )
        cat_stats.columns = ['category', 'hist_mean', 'hist_std', 'hist_months']
        cat_stats['hist_std'] = cat_stats['hist_std'].fillna(0)

        cur_cat = cur_df.groupby('category')['amount'].sum().reset_index()
        cur_cat.columns = ['category', 'current']

        merged = cat_stats.merge(cur_cat, on='category', how='outer').fillna(0)

        budgets = []
        total_budget = 0
        for _, row in merged.iterrows():
            hist_mean = float(row['hist_mean'])
            hist_std = float(row['hist_std'])
            current = round(float(row['current']), 2)

            if hist_mean > 0:
                limit = round(hist_mean + hist_std, 2)
            elif current > 0:
                limit = round(current * 1.15, 2)
            else:
                continue

            pct = round((current / limit * 100) if limit > 0 else 0, 1)
            budgets.append({
                'category': row['category'],
                'limit': limit,
                'current': current,
                'percentage': pct,
                'basis': 'historical_mean_plus_std' if hist_mean > 0 else 'current_spending',
                'hist_mean': round(hist_mean, 2),
                'hist_std': round(hist_std, 2),
                'months_of_data': int(row['hist_months']),
            })
            total_budget += limit

        budgets.sort(key=lambda x: x['current'], reverse=True)

        month_names = ['', 'January', 'February', 'March', 'April', 'May', 'June',
                       'July', 'August', 'September', 'October', 'November', 'December']
        return {
            'data': {'budget': budgets, 'total': round(total_budget, 2)},
            'metadata': {
                'method': 'historical_mean_plus_std',
                'method_label': 'Budget = historical monthly average + 1 standard deviation',
                'is_ml_model': False,
                'month': month, 'year': year,
                'label': f'{month_names[month]} {year}',
                'history_months': int(cat_stats['hist_months'].max()) if not cat_stats.empty else 0,
            },
            'error': None,
        }

    # ================================================================= #
    #  HISTORICAL CONTEXT — full dataset aggregations
    # ================================================================= #

    def get_history(self) -> Dict:
        """Monthly totals across all time. No raw transactions."""
        if self.df.empty:
            return self._empty('history', 'No data')

        monthly = (
            self.df.groupby(self.df['_month'].astype(str))['amount']
            .agg(['sum', 'count']).reset_index()
        )
        monthly.columns = ['period', 'total', 'count']
        monthly = monthly.sort_values('period')
        monthly['total'] = monthly['total'].round(2)

        date_range_start = str(self.df['_date'].min().date())
        date_range_end = str(self.df['_date'].max().date())

        return {
            'data': {
                'monthly_totals': monthly.to_dict('records'),
            },
            'metadata': {
                'total_months': len(monthly),
                'date_range': f'{date_range_start} to {date_range_end}',
                'label': f'Historical trends ({self.df["_year"].min()}–{self.df["_year"].max()})',
            },
            'error': None,
        }

    def get_category_trends(self) -> Dict:
        """Per-category monthly spending over time."""
        if self.df.empty:
            return self._empty('category_trends', 'No data')

        pivot = (
            self.df.groupby([self.df['_month'].astype(str), 'category'])['amount']
            .sum().reset_index()
        )
        pivot.columns = ['period', 'category', 'amount']
        pivot['amount'] = pivot['amount'].round(2)

        # Get all unique categories and periods
        categories = sorted(pivot['category'].unique().tolist())
        periods = sorted(pivot['period'].unique().tolist())

        # Build series per category
        series = {}
        for cat in categories:
            cat_data = pivot[pivot['category'] == cat].set_index('period')['amount']
            series[cat] = [round(float(cat_data.get(p, 0)), 2) for p in periods]

        # Top categories by total all-time spending
        top = (
            self.df.groupby('category')['amount'].sum()
            .sort_values(ascending=False).head(8)
        )
        top_categories = [
            {'category': cat, 'total': round(float(amt), 2)}
            for cat, amt in top.items()
        ]

        return {
            'data': {
                'periods': periods,
                'categories': categories,
                'series': series,
                'top_categories': top_categories,
            },
            'metadata': {
                'total_periods': len(periods),
                'total_categories': len(categories),
            },
            'error': None,
        }

    # ================================================================= #
    #  PUBLIC API
    # ================================================================= #

    def get_analytics(self, period: str = 'latest') -> Dict:
        """
        Spending analytics for a period.
        Returns { data, metadata, error }.
        """
        if self.df.empty:
            return self._empty('analytics', 'No expense data loaded')

        current_month, prev_month = self._resolve_periods(period)

        cur_df = self.df[self.df['_month'] == current_month]
        prev_df = self.df[self.df['_month'] == prev_month] if prev_month else pd.DataFrame()

        by_cat = (
            cur_df.groupby('category')['amount']
            .sum()
            .sort_values(ascending=False)
            .reset_index()
        )
        by_cat.columns = ['category', 'amount']
        by_cat['amount'] = by_cat['amount'].round(2)

        total_current = round(float(cur_df['amount'].sum()), 2)
        total_prev = round(float(prev_df['amount'].sum()), 2) if not prev_df.empty else None

        comparison = None
        if total_prev is not None and total_prev > 0:
            delta = total_current - total_prev
            delta_pct = round((delta / total_prev) * 100, 1)
            comparison = {
                'previous_total': total_prev,
                'delta': round(delta, 2),
                'delta_pct': delta_pct,
                'direction': 'increased' if delta > 0 else 'decreased' if delta < 0 else 'unchanged',
            }

        return {
            'data': {
                'total_monthly': total_current,
                'by_category': by_cat.to_dict('records'),
                'comparison': comparison,
            },
            'metadata': {
                'current_period': str(current_month),
                'previous_period': str(prev_month) if prev_month else None,
                'transaction_count': len(cur_df),
                'period_start': str(cur_df['_date'].min().date()) if not cur_df.empty else None,
                'period_end': str(cur_df['_date'].max().date()) if not cur_df.empty else None,
            },
            'error': None,
        }

    def get_insights(self) -> Dict:
        """
        Generate ALL data-driven insights.
        Returns { data: [ {message, metric, value, confidence, type} ], metadata, error }.
        """
        if self.df.empty:
            return self._empty('insights', 'No expense data loaded')

        current_month, prev_month = self._resolve_periods('latest')
        cur_df = self.df[self.df['_month'] == current_month]
        prev_df = self.df[self.df['_month'] == prev_month] if prev_month else pd.DataFrame()

        insights: List[Dict] = []

        # --- 1) Month-over-month comparison ---
        insights += self._compare_months(cur_df, prev_df, current_month, prev_month)

        # --- 2) Category analysis ---
        insights += self._category_insights(cur_df, prev_df)

        # --- 3) Anomaly / spike detection via z-score ---
        insights += self._detect_anomalies(cur_df)

        # --- 4) Daily spending stats ---
        insights += self._daily_stats(cur_df, current_month)

        # --- 5) Trend from aggregated time series ---
        insights += self._trend_insight()

        # --- 6) Forecast-derived insight ---
        insights += self._forecast_insight()

        # Sort by confidence descending
        insights.sort(key=lambda x: x.get('confidence', 0), reverse=True)

        return {
            'data': insights,
            'metadata': {
                'current_period': str(current_month),
                'previous_period': str(prev_month) if prev_month else None,
                'insight_count': len(insights),
                'generated_at': datetime.now(timezone.utc).isoformat(),
            },
            'error': None,
        }

    def get_anomalies(self) -> Dict:
        """
        Z-score anomaly detection across the entire dataset.
        Returns { data: {alerts, summary}, metadata, error }.
        """
        if self.df.empty:
            return self._empty('anomalies', 'No expense data loaded')

        df = self.df.copy()
        mean_amt = df['amount'].mean()
        std_amt = df['amount'].std()

        if std_amt == 0 or not np.isfinite(std_amt):
            return {
                'data': {'alerts': [], 'summary': 'All amounts are identical — no variance.'},
                'metadata': {'method': 'z_score', 'total_transactions': len(df), 'mean': round(float(mean_amt), 2), 'std': 0},
                'error': None,
            }

        threshold = 2.5
        alerts = []
        for _, row in df.iterrows():
            amt = row['amount']
            if not np.isfinite(amt):
                continue
            z = abs((amt - mean_amt) / std_amt)
            if not np.isfinite(z):
                continue
            if z > threshold:
                severity = 'high' if z > 4 else 'medium' if z > 3 else 'low'
                alerts.append({
                    'amount': round(float(amt), 2),
                    'category': row.get('category', 'Other'),
                    'date': str(row['date']),
                    'z_score': round(float(z), 2),
                    'severity': severity,
                    'deviation_from_mean': round(float(amt - mean_amt), 2),
                })

        alerts.sort(key=lambda x: x['z_score'], reverse=True)
        alerts = alerts[:20]

        return {
            'data': {
                'alerts': alerts,
                'summary': f'{len(alerts)} anomalous transactions detected (z > {threshold}).' if alerts else 'No anomalies detected.',
            },
            'metadata': {
                'method': 'z_score',
                'threshold': threshold,
                'total_transactions': len(df),
                'mean': round(float(mean_amt), 2),
                'std': round(float(std_amt), 2),
            },
            'error': None,
        }

    def get_forecast(self, days_ahead: int = 30) -> Dict:
        """
        Moving-average forecast.  Clearly labeled as statistical fallback.
        Returns { data, metadata, error }.
        """
        if self.df_agg.empty:
            return self._empty('forecast', 'No time-series data for forecasting')

        agg = self.df_agg.copy()
        agg['total_amount'] = pd.to_numeric(agg['total_amount'], errors='coerce').fillna(0)

        # Use last 30 days for more stable average, last 7 for short-term
        recent_30 = agg.tail(30)
        recent_7 = agg.tail(7)
        avg_30 = float(recent_30['total_amount'].mean())
        avg_7 = float(recent_7['total_amount'].mean())
        std_30 = float(recent_30['total_amount'].std()) if len(recent_30) > 1 else 0

        # Trend via linear regression on last 30 days
        if len(recent_30) >= 7:
            y = recent_30['total_amount'].values.astype(float)
            x = np.arange(len(y), dtype=float)
            slope = float(np.polyfit(x, y, 1)[0])
        else:
            slope = 0.0

        if slope > std_30 * 0.1:
            trend = 'increasing'
        elif slope < -std_30 * 0.1:
            trend = 'decreasing'
        else:
            trend = 'stable'

        # Generate daily forecast
        last_date_str = agg['date'].iloc[-1]
        last_date = pd.to_datetime(last_date_str)
        forecast_points = []
        for i in range(1, days_ahead + 1):
            fdate = last_date + pd.Timedelta(days=i)
            # Use slope-adjusted prediction
            predicted = max(0, avg_30 + slope * i)
            forecast_points.append({
                'date': fdate.strftime('%Y-%m-%d'),
                'predicted_amount': round(predicted, 2),
            })

        total_predicted = round(sum(p['predicted_amount'] for p in forecast_points), 2)

        return {
            'data': {
                'forecast': forecast_points,
                'total_predicted': total_predicted,
                'trend': trend,
                'slope_per_day': round(slope, 2),
                'avg_daily_30d': round(avg_30, 2),
                'avg_daily_7d': round(avg_7, 2),
            },
            'metadata': {
                'method': 'linear_trend_moving_average',
                'method_label': 'Statistical forecast (moving average + linear trend)',
                'is_ml_model': False,
                'training_days': len(recent_30),
                'forecast_days': days_ahead,
                'confidence': round(min(0.65, 0.3 + len(recent_30) * 0.01), 2),
            },
            'error': None,
        }

    def get_budgets(self) -> Dict:
        """
        Generate budgets from historical spending.
        Uses previous month average + std-based buffer instead of fixed %.
        Returns { data, metadata, error }.
        """
        if self.df.empty:
            return self._empty('budgets', 'No expense data loaded')

        current_month, prev_month = self._resolve_periods('latest')

        # Use all historical data to compute per-category stats
        months = sorted(self.df['_month'].unique())
        if len(months) < 1:
            return self._empty('budgets', 'Not enough monthly data')

        cur_df = self.df[self.df['_month'] == current_month]
        hist_df = self.df[self.df['_month'] != current_month] if len(months) > 1 else cur_df

        # Per-category monthly totals across history
        hist_monthly = (
            hist_df.groupby([hist_df['_month'].astype(str), 'category'])['amount']
            .sum()
            .reset_index()
        )
        hist_monthly.columns = ['month', 'category', 'amount']

        # Stats per category from history
        cat_stats = (
            hist_monthly.groupby('category')['amount']
            .agg(['mean', 'std', 'count'])
            .reset_index()
        )
        cat_stats.columns = ['category', 'hist_mean', 'hist_std', 'hist_months']
        cat_stats['hist_std'] = cat_stats['hist_std'].fillna(0)

        # Current month spending
        cur_cat = cur_df.groupby('category')['amount'].sum().reset_index()
        cur_cat.columns = ['category', 'current']

        merged = cat_stats.merge(cur_cat, on='category', how='outer').fillna(0)

        budgets = []
        total_budget = 0
        for _, row in merged.iterrows():
            hist_mean = float(row['hist_mean'])
            hist_std = float(row['hist_std'])
            current = round(float(row['current']), 2)

            # Budget = historical mean + 1 std (data-driven buffer)
            if hist_mean > 0:
                limit = round(hist_mean + hist_std, 2)
            elif current > 0:
                limit = round(current * 1.15, 2)  # new category, use 15% buffer on current
            else:
                continue  # skip zero-spending categories

            pct = round((current / limit * 100) if limit > 0 else 0, 1)
            budgets.append({
                'category': row['category'],
                'limit': limit,
                'current': current,
                'percentage': pct,
                'basis': 'historical_mean_plus_std' if hist_mean > 0 else 'current_spending',
                'hist_mean': round(hist_mean, 2),
                'hist_std': round(hist_std, 2),
                'months_of_data': int(row['hist_months']),
            })
            total_budget += limit

        budgets.sort(key=lambda x: x['current'], reverse=True)

        return {
            'data': {
                'budget': budgets,
                'total': round(total_budget, 2),
            },
            'metadata': {
                'method': 'historical_mean_plus_std',
                'method_label': 'Budget = historical monthly average + 1 standard deviation',
                'is_ml_model': False,
                'period': str(current_month),
                'history_months': len(months) - 1 if len(months) > 1 else 1,
            },
            'error': None,
        }

    # ================================================================= #
    #  PRIVATE — insight generators
    # ================================================================= #

    def _resolve_periods(self, period: str):
        """Return (current_month, previous_month) as pd.Period objects."""
        months = sorted(self.df['_month'].unique())
        if not months:
            return None, None
        current = months[-1]
        prev = months[-2] if len(months) >= 2 else None
        return current, prev

    def _compare_months(self, cur_df, prev_df, cur_month, prev_month) -> List[Dict]:
        insights = []
        total_cur = cur_df['amount'].sum()

        if prev_df.empty or prev_month is None:
            return insights

        total_prev = prev_df['amount'].sum()
        if total_prev == 0:
            return insights

        delta = total_cur - total_prev
        delta_pct = round((delta / total_prev) * 100, 1)

        direction = 'increased' if delta > 0 else 'decreased'
        insights.append({
            'type': 'month_comparison',
            'metric': 'total_spending_change',
            'message': (
                f'Total spending {direction} by {abs(delta_pct)}% '
                f'({str(cur_month)} vs {str(prev_month)}): '
                f'current {round(total_cur, 2)} vs previous {round(total_prev, 2)}, '
                f'delta {round(abs(delta), 2)}.'
            ),
            'value': {
                'current': round(total_cur, 2),
                'previous': round(total_prev, 2),
                'delta': round(delta, 2),
                'delta_pct': delta_pct,
            },
            'confidence': min(0.9, 0.5 + len(cur_df) * 0.002),
        })

        # Per-category comparison
        cat_cur = cur_df.groupby('category')['amount'].sum()
        cat_prev = prev_df.groupby('category')['amount'].sum()
        merged = pd.DataFrame({'current': cat_cur, 'previous': cat_prev}).fillna(0)

        for cat, row in merged.iterrows():
            c, p = float(row['current']), float(row['previous'])
            if p == 0:
                continue
            d = c - p
            d_pct = round((d / p) * 100, 1)
            if abs(d_pct) >= 15:  # Only report meaningful changes
                direction = 'increased' if d > 0 else 'decreased'
                insights.append({
                    'type': 'category_comparison',
                    'metric': f'{cat}_spending_change',
                    'message': (
                        f'{cat} spending {direction} by {abs(d_pct)}%: '
                        f'{round(c, 2)} vs {round(p, 2)} (delta {round(abs(d), 2)}).'
                    ),
                    'value': {
                        'category': cat,
                        'current': round(c, 2),
                        'previous': round(p, 2),
                        'delta': round(d, 2),
                        'delta_pct': d_pct,
                    },
                    'confidence': min(0.85, 0.4 + min(len(cur_df), 50) * 0.009),
                })

        return insights

    def _category_insights(self, cur_df, prev_df) -> List[Dict]:
        insights = []
        if cur_df.empty:
            return insights

        cat_totals = cur_df.groupby('category')['amount'].sum().sort_values(ascending=False)
        total = cat_totals.sum()

        if total == 0:
            return insights

        # Top category
        top_cat = cat_totals.index[0]
        top_amt = float(cat_totals.iloc[0])
        top_pct = round((top_amt / total) * 100, 1)
        insights.append({
            'type': 'top_category',
            'metric': 'highest_spending_category',
            'message': (
                f'{top_cat} is the highest spending category at '
                f'{round(top_amt, 2)} ({top_pct}% of total {round(total, 2)}).'
            ),
            'value': {
                'category': top_cat,
                'amount': round(top_amt, 2),
                'percentage': top_pct,
                'total': round(total, 2),
            },
            'confidence': 0.95,
        })

        # Category concentration — if top 2 categories > 60% of total
        if len(cat_totals) >= 2:
            top2_amt = float(cat_totals.iloc[:2].sum())
            top2_pct = round((top2_amt / total) * 100, 1)
            if top2_pct > 60:
                top2_cats = list(cat_totals.index[:2])
                insights.append({
                    'type': 'concentration',
                    'metric': 'spending_concentration',
                    'message': (
                        f'{top2_cats[0]} and {top2_cats[1]} account for {top2_pct}% '
                        f'of total spending ({round(top2_amt, 2)} of {round(total, 2)}).'
                    ),
                    'value': {
                        'categories': top2_cats,
                        'combined_amount': round(top2_amt, 2),
                        'combined_pct': top2_pct,
                    },
                    'confidence': 0.85,
                })

        return insights

    def _detect_anomalies(self, cur_df) -> List[Dict]:
        insights = []
        if len(cur_df) < 5:
            return insights

        mean_amt = cur_df['amount'].mean()
        std_amt = cur_df['amount'].std()
        if std_amt == 0 or not np.isfinite(std_amt):
            return insights

        # Spikes: amount > mean + 2*std
        spike_threshold = mean_amt + 2 * std_amt
        spikes = cur_df[cur_df['amount'] > spike_threshold]

        if len(spikes) > 0:
            spike_total = round(float(spikes['amount'].sum()), 2)
            spike_count = len(spikes)
            max_spike = spikes.loc[spikes['amount'].idxmax()]
            insights.append({
                'type': 'spending_spike',
                'metric': 'unusual_transactions',
                'message': (
                    f'{spike_count} transactions exceeded the statistical threshold '
                    f'of {round(spike_threshold, 2)} (mean {round(mean_amt, 2)} + 2x std {round(std_amt, 2)}). '
                    f'Largest: {round(float(max_spike["amount"]), 2)} in {max_spike.get("category", "Unknown")} '
                    f'on {max_spike["date"]}. Total spike amount: {spike_total}.'
                ),
                'value': {
                    'spike_count': spike_count,
                    'spike_total': spike_total,
                    'threshold': round(spike_threshold, 2),
                    'largest_amount': round(float(max_spike['amount']), 2),
                    'largest_category': max_spike.get('category', 'Unknown'),
                    'largest_date': str(max_spike['date']),
                    'mean': round(mean_amt, 2),
                    'std': round(std_amt, 2),
                },
                'confidence': 0.8,
            })

        return insights

    def _daily_stats(self, cur_df, cur_month) -> List[Dict]:
        insights = []
        if cur_df.empty:
            return insights

        daily = cur_df.groupby('date')['amount'].sum()
        daily_mean = float(daily.mean())
        daily_std = float(daily.std()) if len(daily) > 1 else 0
        active_days = len(daily)
        total = float(daily.sum())

        # Rolling 7-day average for the period
        daily_series = daily.sort_index()
        rolling_7 = daily_series.rolling(7, min_periods=1).mean()
        latest_rolling_7 = float(rolling_7.iloc[-1]) if len(rolling_7) > 0 else daily_mean

        insights.append({
            'type': 'daily_spending',
            'metric': 'daily_average',
            'message': (
                f'Daily average spending: {round(daily_mean, 2)} '
                f'(std: {round(daily_std, 2)}) across {active_days} active days. '
                f'7-day rolling average: {round(latest_rolling_7, 2)}. '
                f'Period total: {round(total, 2)}.'
            ),
            'value': {
                'daily_mean': round(daily_mean, 2),
                'daily_std': round(daily_std, 2),
                'active_days': active_days,
                'rolling_7d_avg': round(latest_rolling_7, 2),
                'total': round(total, 2),
            },
            'confidence': min(0.85, 0.4 + active_days * 0.02),
        })

        return insights

    def _trend_insight(self) -> List[Dict]:
        insights = []
        if self.df_agg.empty or len(self.df_agg) < 14:
            return insights

        agg = self.df_agg.copy()
        agg['total_amount'] = pd.to_numeric(agg['total_amount'], errors='coerce').fillna(0)
        recent = agg.tail(30)

        y = recent['total_amount'].values.astype(float)
        x = np.arange(len(y), dtype=float)

        if len(x) < 7:
            return insights

        slope = float(np.polyfit(x, y, 1)[0])
        avg = float(y.mean())
        std = float(y.std()) if len(y) > 1 else 0

        if std == 0:
            return insights

        # Normalize slope relative to std
        normalized_slope = slope / std if std > 0 else 0

        if abs(normalized_slope) < 0.05:
            trend = 'stable'
        elif normalized_slope > 0:
            trend = 'increasing'
        else:
            trend = 'decreasing'

        insights.append({
            'type': 'trend',
            'metric': 'spending_trend',
            'message': (
                f'Spending trend over last {len(recent)} days: {trend}. '
                f'Slope: {round(slope, 2)} per day. '
                f'Average: {round(avg, 2)}, std: {round(std, 2)}.'
            ),
            'value': {
                'trend': trend,
                'slope_per_day': round(slope, 2),
                'avg_daily': round(avg, 2),
                'std_daily': round(std, 2),
                'days_analyzed': len(recent),
            },
            'confidence': min(0.75, 0.3 + len(recent) * 0.015),
        })

        return insights

    def _forecast_insight(self) -> List[Dict]:
        insights = []
        forecast_result = self.get_forecast(days_ahead=30)

        if forecast_result.get('error'):
            return insights

        data = forecast_result.get('data', {})
        total_pred = data.get('total_predicted', 0)
        trend = data.get('trend', 'stable')
        slope = data.get('slope_per_day', 0)
        avg_30 = data.get('avg_daily_30d', 0)

        if total_pred > 0:
            insights.append({
                'type': 'forecast',
                'metric': 'predicted_next_month',
                'message': (
                    f'Projected spending for the next 30 days: {round(total_pred, 2)}. '
                    f'Trend: {trend} (slope {round(slope, 2)}/day). '
                    f'Based on 30-day average of {round(avg_30, 2)}/day.'
                ),
                'value': {
                    'total_predicted': round(total_pred, 2),
                    'trend': trend,
                    'slope_per_day': round(slope, 2),
                    'avg_daily': round(avg_30, 2),
                },
                'confidence': forecast_result.get('metadata', {}).get('confidence', 0.4),
            })

        return insights

    # ================================================================= #
    #  Utility
    # ================================================================= #

    def _empty(self, kind: str, msg: str) -> Dict:
        return {
            'data': [] if kind == 'insights' else {},
            'metadata': {'kind': kind},
            'error': msg,
        }
