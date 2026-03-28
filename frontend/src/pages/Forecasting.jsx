import React, { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { TrendingUp, TrendingDown, Lightbulb, AlertCircle } from 'lucide-react';
import * as api from '@/lib/api';
import { formatCurrency } from '@/utils/formatCurrency';

export default function Forecasting() {
  const [forecast, setForecast] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => { loadForecast(); }, []);

  async function loadForecast() {
    setLoading(true);
    try {
      const [fData, aData] = await Promise.all([
        api.getForecast(),
        api.getAnalyticsSpending()
      ]);
      setForecast(fData);
      setAnalytics(aData);
    } catch (e) {
      console.error('Forecast loading error:', e);
    } finally { setLoading(false); }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-[#f5f7fb] flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto" />
          <p className="mt-4 text-slate-600">Loading forecast...</p>
        </div>
      </div>
    );
  }

  // All values from backend
  const fData = forecast?.data || {};
  const fMeta = forecast?.metadata || {};
  const forecastPoints = fData.forecast || [];
  const totalPredicted = fData.total_predicted || 0;
  const trend = fData.trend || 'stable';
  const slopePerDay = fData.slope_per_day || 0;
  const avgDaily30 = fData.avg_daily_30d || 0;
  const avgDaily7 = fData.avg_daily_7d || 0;
  const methodLabel = fMeta.method_label || fMeta.method || 'unknown';
  const isMlModel = fMeta.is_ml_model || false;
  const confidence = fMeta.confidence || 0;

  const isIncreasing = trend === 'increasing';
  const isDecreasing = trend === 'decreasing';

  // Category spending from analytics
  const categorySpending = analytics?.data?.by_category || [];
  const topCategories = categorySpending.slice(0, 4);

  // Highest predicted day
  const highestDay = forecastPoints.reduce((max, item) =>
    item.predicted_amount > (max?.predicted_amount || 0) ? item : max,
    forecastPoints[0]
  );

  return (
    <div className="min-h-screen bg-[#f5f7fb]">
      {/* NAVBAR */}
      <header className="sticky top-0 z-30 bg-white/80 backdrop-blur-xl border-b border-slate-200">
        <div className="container mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-xl bg-indigo-500 flex items-center justify-center text-white text-lg font-bold">F</div>
            <span className="font-semibold text-slate-800 text-lg">FinFusion</span>
          </div>
          <nav className="hidden md:flex gap-6 text-sm font-medium text-slate-500">
            <a href="/" className="hover:text-slate-800 transition-colors">Dashboard</a>
            <a href="/budgets" className="hover:text-slate-800 transition-colors">Budgets</a>
            <a href="/forecast" className="text-indigo-600 border-b-2 border-indigo-500 pb-1">Forecast</a>
            <a href="/groups" className="hover:text-slate-800 transition-colors">Groups</a>
          </nav>
          <div className="h-9 w-9 rounded-full bg-gradient-to-tr from-indigo-400 to-purple-400 flex items-center justify-center text-white text-sm font-semibold">Y</div>
        </div>
      </header>

      <main className="container mx-auto px-6 py-12 max-w-5xl">
        {/* Hero */}
        <div className="mb-8">
          <h1 className="text-4xl md:text-5xl font-bold text-slate-900 mb-4" style={{ lineHeight: '1.2' }}>
            Projected spending:{' '}
            <span className="text-indigo-600">{formatCurrency(totalPredicted)}</span>{' '}
            over {forecastPoints.length} days
          </h1>

          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-slate-100">
            {isIncreasing ? <TrendingUp className="w-4 h-4 text-rose-500" />
              : isDecreasing ? <TrendingDown className="w-4 h-4 text-emerald-500" />
              : <div className="w-4 h-4 bg-slate-400 rounded-full" />}
            <span className="text-sm font-medium text-slate-900 uppercase tracking-wide">{trend}</span>
            <span className="text-sm text-slate-600">
              (slope: {slopePerDay}/day)
            </span>
          </div>
        </div>

        {/* Method label */}
        <Alert className={`mb-6 border-0 rounded-2xl ${isMlModel ? 'bg-emerald-50' : 'bg-amber-50'}`}>
          <AlertCircle className={`h-4 w-4 ${isMlModel ? 'text-emerald-600' : 'text-amber-600'}`} />
          <AlertDescription className={`text-sm ${isMlModel ? 'text-emerald-900' : 'text-amber-900'}`}>
            <strong>Method:</strong> {methodLabel}. Confidence: {(confidence * 100).toFixed(0)}%.
          </AlertDescription>
        </Alert>

        {/* Chart Card */}
        <Card className="rounded-3xl border-0 bg-gradient-to-br from-indigo-50 to-purple-50 p-8 mb-8 shadow-sm">
          <div className="flex items-start justify-between mb-6">
            <div>
              <h2 className="text-xl font-semibold text-slate-900 mb-1">Predicted Spending</h2>
              <p className="text-sm text-slate-600">{analytics?.metadata?.current_period || 'Next period'}</p>
            </div>
            <div className="text-right">
              <p className="text-xs text-slate-600 uppercase tracking-wide mb-1">Avg Daily (30d)</p>
              <p className="text-2xl font-bold text-indigo-600">{formatCurrency(avgDaily30)}</p>
              <p className="text-xs text-slate-500 mt-1">7-day: {formatCurrency(avgDaily7)}</p>
            </div>
          </div>

          <div className="relative h-64 bg-white/60 rounded-2xl p-6">
            <div className="absolute top-4 right-4 text-xs">
              <p className="text-slate-600 uppercase tracking-wide mb-1">Peak Day</p>
              <p className="text-lg font-bold text-indigo-600">{formatCurrency(highestDay?.predicted_amount || 0)}</p>
            </div>

            <svg className="w-full h-full" viewBox="0 0 800 200" preserveAspectRatio="none">
              <defs>
                <linearGradient id="lineGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="#6366f1" stopOpacity="0.2" />
                  <stop offset="50%" stopColor="#6366f1" stopOpacity="0.4" />
                  <stop offset="100%" stopColor="#6366f1" stopOpacity="0.2" />
                </linearGradient>
              </defs>
              {forecastPoints.length > 0 && (
                <>
                  <path
                    d={`M 0,100 ${forecastPoints.map((item, i) => {
                      const x = (i / (forecastPoints.length - 1)) * 800;
                      const y = 150 - ((item.predicted_amount / (highestDay?.predicted_amount || 1)) * 100);
                      return `L ${x},${y}`;
                    }).join(' ')}`}
                    fill="none" stroke="#6366f1" strokeWidth="3" strokeLinecap="round"
                  />
                  <path
                    d={`M 0,100 ${forecastPoints.map((item, i) => {
                      const x = (i / (forecastPoints.length - 1)) * 800;
                      const y = 150 - ((item.predicted_amount / (highestDay?.predicted_amount || 1)) * 100);
                      return `L ${x},${y}`;
                    }).join(' ')} L 800,200 L 0,200 Z`}
                    fill="url(#lineGrad)"
                  />
                </>
              )}
            </svg>
            <div className="flex justify-between text-xs text-slate-500 mt-2">
              <span>Day 1</span><span>Day 8</span><span>Day 15</span><span>Day 22</span><span>Day 30</span>
            </div>
          </div>
        </Card>

        {/* Insights + Categories */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card className="rounded-3xl border-0 bg-indigo-50 p-6 shadow-sm">
            <div className="flex items-center gap-2 mb-4">
              <Lightbulb className="w-5 h-5 text-indigo-600" />
              <h3 className="text-lg font-semibold text-slate-900">Forecast Details</h3>
            </div>
            <ul className="space-y-3">
              <li className="flex items-start gap-3">
                <div className="w-1.5 h-1.5 rounded-full bg-indigo-500 mt-2 flex-shrink-0" />
                <p className="text-sm text-slate-700 leading-relaxed">
                  30-day average daily spend: {formatCurrency(avgDaily30)}. 7-day average: {formatCurrency(avgDaily7)}.
                </p>
              </li>
              <li className="flex items-start gap-3">
                <div className="w-1.5 h-1.5 rounded-full bg-indigo-500 mt-2 flex-shrink-0" />
                <p className="text-sm text-slate-700 leading-relaxed">
                  Trend: {trend} (slope: {slopePerDay} per day).
                </p>
              </li>
              {highestDay && (
                <li className="flex items-start gap-3">
                  <div className="w-1.5 h-1.5 rounded-full bg-indigo-500 mt-2 flex-shrink-0" />
                  <p className="text-sm text-slate-700 leading-relaxed">
                    Peak predicted day: {highestDay.date} at {formatCurrency(highestDay.predicted_amount)}.
                  </p>
                </li>
              )}
            </ul>
          </Card>

          <Card className="rounded-3xl border-0 bg-white p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-slate-900 mb-6">Top Categories</h3>
            <div className="space-y-5">
              {topCategories.map((cat, idx) => {
                const maxAmt = Math.max(...topCategories.map(c => c.amount));
                const pct = maxAmt > 0 ? (cat.amount / maxAmt) * 100 : 0;
                return (
                  <div key={idx}>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-slate-900">{cat.category}</span>
                      <span className="text-sm font-bold text-indigo-600">{formatCurrency(cat.amount)}</span>
                    </div>
                    <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
                      <div className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full transition-all duration-500"
                        style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                );
              })}
              {topCategories.length === 0 && <p className="text-sm text-slate-400">No category data</p>}
            </div>
          </Card>
        </div>

        <div className="mt-12 text-center">
          <p className="text-xs text-slate-400 uppercase tracking-wide">
            {methodLabel}
          </p>
        </div>
      </main>
    </div>
  );
}
