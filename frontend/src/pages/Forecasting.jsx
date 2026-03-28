import React, { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { TrendingUp, TrendingDown, Lightbulb, AlertCircle } from 'lucide-react';
import * as api from '@/lib/api';

export default function Forecasting() {
  const [forecast, setForecast] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadForecast();
  }, []);

  async function loadForecast() {
    setLoading(true);
    try {
      const [forecastData, analyticsData] = await Promise.all([
        api.getForecast(),
        api.getAnalyticsSpending()
      ]);
      setForecast(forecastData);
      setAnalytics(analyticsData);
    } catch (error) {
      console.error('Forecast loading error:', error);
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-[#f5f7fb] flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
          <p className="mt-4 text-slate-600">Loading forecast...</p>
        </div>
      </div>
    );
  }

  // Calculate metrics
  const totalPredicted = forecast?.forecast?.reduce((sum, item) => sum + (item.predicted_amount || 0), 0) || 0;
  const forecastDays = forecast?.forecast?.length || 30;
  const avgDaily = forecastDays > 0 ? totalPredicted / forecastDays : 0;
  const highestDay = forecast?.forecast?.reduce((max, item) => 
    item.predicted_amount > (max?.predicted_amount || 0) ? item : max, 
    forecast?.forecast?.[0]
  );
  
  const trend = forecast?.trend || 'stable';
  const isIncreasing = trend === 'increasing';
  const isDecreasing = trend === 'decreasing';

  // Get category breakdown from analytics
  const categorySpending = analytics?.by_category || [];
  const topCategories = categorySpending.slice(0, 3);

  // Generate insights
  const insights = [];
  if (avgDaily > 0) {
    insights.push(`Average daily spend is expected to hover around ₹${avgDaily.toFixed(0)}.`);
  }
  if (highestDay) {
    insights.push(`Prepare for your highest spending day on ${new Date(highestDay.date).toLocaleDateString('en-IN', { month: 'short', day: 'numeric' })} with about ₹${highestDay.predicted_amount?.toFixed(0)}.`);
  }
  if (topCategories.length > 0) {
    insights.push(`Most of your money is likely going towards ${topCategories[0].category} this month.`);
  }
  if (forecast?.fallback) {
    insights.push(forecast.error || 'Using simplified forecasting method.');
  }

  return (
    <div className="min-h-screen bg-[#f5f7fb]">
      {/* TOP NAVBAR */}
      <header className="sticky top-0 z-30 bg-white/80 backdrop-blur-xl border-b border-slate-200">
        <div className="container mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-xl bg-indigo-500 flex items-center justify-center text-white text-lg font-bold">
              F
            </div>
            <span className="font-semibold text-slate-800 text-lg">FinFusion</span>
          </div>

          <nav className="hidden md:flex gap-6 text-sm font-medium text-slate-500">
            <a href="/" className="hover:text-slate-800 transition-colors">
              Dashboard
            </a>
            <a href="/groups" className="hover:text-slate-800 transition-colors">
              Groups
            </a>
            <a href="/budgets" className="hover:text-slate-800 transition-colors">
              Budgets
            </a>
            <a href="/forecast" className="text-indigo-600 border-b-2 border-indigo-500 pb-1">
              Forecast
            </a>
          </nav>

          <div className="h-9 w-9 rounded-full bg-gradient-to-tr from-indigo-400 to-purple-400 flex items-center justify-center text-white text-sm font-semibold">
            Y
          </div>
        </div>
      </header>

      {/* MAIN CONTENT */}
      <main className="container mx-auto px-6 py-12 max-w-5xl">
        {/* Hero Section */}
        <div className="mb-8">
          <h1 className="text-4xl md:text-5xl font-bold text-slate-900 mb-4" style={{ lineHeight: '1.2' }}>
            You are likely to spend{' '}
            <span className="text-indigo-600">₹{totalPredicted.toFixed(0)}</span>{' '}
            next month
          </h1>
          
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-slate-100">
            {isIncreasing ? (
              <TrendingUp className="w-4 h-4 text-rose-500" />
            ) : isDecreasing ? (
              <TrendingDown className="w-4 h-4 text-emerald-500" />
            ) : (
              <div className="w-4 h-4 bg-slate-400 rounded-full" />
            )}
            <span className="text-sm font-medium text-slate-900 uppercase tracking-wide">
              {trend}
            </span>
            <span className="text-sm text-slate-600">
              {isIncreasing && '(Your spending is increasing compared to last month)'}
              {isDecreasing && '(Your spending is decreasing compared to last month)'}
              {!isIncreasing && !isDecreasing && '(Your spending is stable)'}
            </span>
          </div>
        </div>

        {/* Predicted Spending Chart */}
        <Card className="rounded-3xl border-0 bg-gradient-to-br from-indigo-50 to-purple-50 p-8 mb-8 shadow-sm">
          <div className="flex items-start justify-between mb-6">
            <div>
              <h2 className="text-xl font-semibold text-slate-900 mb-1">
                Predicted Spending
              </h2>
              <p className="text-sm text-slate-600">
                {analytics?.metadata?.period_label || 'Current month'} Forecast
              </p>
            </div>
            <div className="text-right">
              <p className="text-xs text-slate-600 uppercase tracking-wide mb-1">Avg Daily</p>
              <p className="text-2xl font-bold text-indigo-600">₹{avgDaily.toFixed(0)}</p>
            </div>
          </div>

          {/* Simple Chart Visualization */}
          <div className="relative h-64 bg-white/60 rounded-2xl p-6">
            <div className="absolute top-4 right-4 text-xs">
              <p className="text-slate-600 uppercase tracking-wide mb-1">Highest Spend</p>
              <p className="text-lg font-bold text-indigo-600">₹{highestDay?.predicted_amount?.toFixed(0) || '0'}</p>
            </div>
            
            {/* Chart Line */}
            <svg className="w-full h-full" viewBox="0 0 800 200" preserveAspectRatio="none">
              <defs>
                <linearGradient id="lineGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="#6366f1" stopOpacity="0.2" />
                  <stop offset="50%" stopColor="#6366f1" stopOpacity="0.4" />
                  <stop offset="100%" stopColor="#6366f1" stopOpacity="0.2" />
                </linearGradient>
              </defs>
              {forecast?.forecast && forecast.forecast.length > 0 && (
                <>
                  <path
                    d={`M 0,100 ${forecast.forecast.map((item, i) => {
                      const x = (i / (forecast.forecast.length - 1)) * 800;
                      const y = 150 - ((item.predicted_amount / (highestDay?.predicted_amount || 1)) * 100);
                      return `L ${x},${y}`;
                    }).join(' ')}`}
                    fill="none"
                    stroke="#6366f1"
                    strokeWidth="3"
                    strokeLinecap="round"
                  />
                  <path
                    d={`M 0,100 ${forecast.forecast.map((item, i) => {
                      const x = (i / (forecast.forecast.length - 1)) * 800;
                      const y = 150 - ((item.predicted_amount / (highestDay?.predicted_amount || 1)) * 100);
                      return `L ${x},${y}`;
                    }).join(' ')} L 800,200 L 0,200 Z`}
                    fill="url(#lineGradient)"
                  />
                </>
              )}
            </svg>

            {/* X-axis labels */}
            <div className="flex justify-between text-xs text-slate-500 mt-2">
              <span>Day 1</span>
              <span>Day 8</span>
              <span>Day 15</span>
              <span>Day 22</span>
              <span>Day 30</span>
            </div>
          </div>
        </Card>

        {/* Insights and Category Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Assistant Insights */}
          <Card className="rounded-3xl border-0 bg-indigo-50 p-6 shadow-sm">
            <div className="flex items-center gap-2 mb-4">
              <Lightbulb className="w-5 h-5 text-indigo-600" />
              <h3 className="text-lg font-semibold text-slate-900">
                Assistant Insights
              </h3>
            </div>
            <ul className="space-y-3">
              {insights.map((insight, idx) => (
                <li key={idx} className="flex items-start gap-3">
                  <div className="w-1.5 h-1.5 rounded-full bg-indigo-500 mt-2 flex-shrink-0" />
                  <p className="text-sm text-slate-700 leading-relaxed">{insight}</p>
                </li>
              ))}
            </ul>
          </Card>

          {/* Spend by Category */}
          <Card className="rounded-3xl border-0 bg-white p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-slate-900 mb-6">
              Spend by Category
            </h3>
            <div className="space-y-5">
              {topCategories.map((category, idx) => {
                const icons = {
                  Food: '🍽️',
                  Transport: '🚗',
                  Entertainment: '🎭',
                  Shopping: '🛍️',
                  Utilities: '💡',
                  Healthcare: '🏥'
                };
                const maxAmount = Math.max(...topCategories.map(c => c.amount));
                const percentage = (category.amount / maxAmount) * 100;
                
                return (
                  <div key={idx}>
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="text-lg">{icons[category.category] || '📊'}</span>
                        <span className="text-sm font-medium text-slate-900">{category.category}</span>
                      </div>
                      <span className="text-sm font-bold text-indigo-600">₹{category.amount.toFixed(0)}</span>
                    </div>
                    <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full transition-all duration-500"
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>
        </div>

        {/* Fallback Warning */}
        {forecast?.fallback && (
          <Alert className="mt-6 border-0 bg-amber-50 rounded-2xl">
            <AlertCircle className="h-4 w-4 text-amber-600" />
            <AlertDescription className="text-amber-900 text-sm">
              <strong>Note:</strong> This forecast uses a simplified prediction model. Add more transaction data for improved accuracy.
            </AlertDescription>
          </Alert>
        )}

        {/* Footer */}
        <div className="mt-12 text-center">
          <p className="text-xs text-slate-400 uppercase tracking-wide">
            AI-Powered Forecast Based on Your Spending Patterns
          </p>
        </div>
      </main>
    </div>
  );
}
