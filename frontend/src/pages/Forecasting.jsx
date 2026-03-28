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
      <div className="min-h-screen bg-[#f7faf8] flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#386381] mx-auto"></div>
          <p className="mt-4 text-[#2c3432]">Loading forecast...</p>
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
    <div className="min-h-screen bg-[#f7faf8]">
      {/* TOP NAVBAR */}
      <header className="sticky top-0 z-30 bg-white/80 backdrop-blur-xl border-b border-[#abb4b1]/15">
        <div className="container mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-xl bg-[#386381] flex items-center justify-center text-white text-lg font-bold">
              F
            </div>
            <span className="font-semibold text-[#2c3432] text-lg">FinFusion</span>
          </div>

          <nav className="hidden md:flex gap-6 text-sm font-medium text-[#5f6664]">
            <a href="/" className="hover:text-[#2c3432] transition-colors">
              Dashboard
            </a>
            <a href="/groups" className="hover:text-[#2c3432] transition-colors">
              Groups
            </a>
            <a href="/budgets" className="hover:text-[#2c3432] transition-colors">
              Budgets
            </a>
            <a href="/forecast" className="text-[#386381] border-b-2 border-[#386381] pb-1">
              Forecast
            </a>
          </nav>

          <div className="h-9 w-9 rounded-full bg-gradient-to-tr from-[#386381] to-[#2b5775] flex items-center justify-center text-white text-sm font-semibold">
            Y
          </div>
        </div>
      </header>

      {/* MAIN CONTENT */}
      <main className="container mx-auto px-6 py-12 max-w-5xl">
        {/* Hero Section */}
        <div className="mb-8">
          <h1 className="text-4xl md:text-5xl font-bold text-[#2c3432] mb-4" style={{ fontFamily: 'Plus Jakarta Sans, sans-serif', lineHeight: '1.2' }}>
            You are likely to spend{' '}
            <span className="text-[#386381]">₹{totalPredicted.toFixed(0)}</span>{' '}
            next month
          </h1>
          
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[#f0f5f2]">
            {isIncreasing ? (
              <TrendingUp className="w-4 h-4 text-[#fa746f]" />
            ) : isDecreasing ? (
              <TrendingDown className="w-4 h-4 text-[#6a9b7f]" />
            ) : (
              <div className="w-4 h-4 bg-[#abb4b1] rounded-full" />
            )}
            <span className="text-sm font-medium text-[#2c3432] uppercase tracking-wide">
              {trend}
            </span>
            <span className="text-sm text-[#5f6664]">
              {isIncreasing && '(Your spending is increasing compared to last month)'}
              {isDecreasing && '(Your spending is decreasing compared to last month)'}
              {!isIncreasing && !isDecreasing && '(Your spending is stable)'}
            </span>
          </div>
        </div>

        {/* Predicted Spending Chart */}
        <Card className="rounded-3xl border-0 bg-[#f0f5f2] p-8 mb-8 shadow-sm">
          <div className="flex items-start justify-between mb-6">
            <div>
              <h2 className="text-xl font-semibold text-[#2c3432] mb-1" style={{ fontFamily: 'Plus Jakarta Sans, sans-serif' }}>
                Predicted Spending
              </h2>
              <p className="text-sm text-[#5f6664]">
                {analytics?.metadata?.period_label || 'Current month'} Forecast
              </p>
            </div>
            <div className="text-right">
              <p className="text-xs text-[#5f6664] uppercase tracking-wide mb-1">Avg Daily</p>
              <p className="text-2xl font-bold text-[#386381]">₹{avgDaily.toFixed(0)}</p>
            </div>
          </div>

          {/* Simple Chart Visualization */}
          <div className="relative h-64 bg-white/50 rounded-2xl p-6">
            <div className="absolute top-4 right-4 text-xs">
              <p className="text-[#5f6664] uppercase tracking-wide mb-1">Highest Spend</p>
              <p className="text-lg font-bold text-[#386381]">₹{highestDay?.predicted_amount?.toFixed(0) || '0'}</p>
            </div>
            
            {/* Chart Line */}
            <svg className="w-full h-full" viewBox="0 0 800 200" preserveAspectRatio="none">
              <defs>
                <linearGradient id="lineGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="#386381" stopOpacity="0.3" />
                  <stop offset="50%" stopColor="#386381" stopOpacity="0.6" />
                  <stop offset="100%" stopColor="#386381" stopOpacity="0.3" />
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
                    stroke="#386381"
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
            <div className="flex justify-between text-xs text-[#5f6664] mt-2">
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
          <Card className="rounded-3xl border-0 bg-[#dde8df] p-6 shadow-sm">
            <div className="flex items-center gap-2 mb-4">
              <Lightbulb className="w-5 h-5 text-[#6a9b7f]" />
              <h3 className="text-lg font-semibold text-[#2c3432]" style={{ fontFamily: 'Plus Jakarta Sans, sans-serif' }}>
                Assistant Insights
              </h3>
            </div>
            <ul className="space-y-3">
              {insights.map((insight, idx) => (
                <li key={idx} className="flex items-start gap-3">
                  <div className="w-1.5 h-1.5 rounded-full bg-[#6a9b7f] mt-2 flex-shrink-0" />
                  <p className="text-sm text-[#2c3432] leading-relaxed">{insight}</p>
                </li>
              ))}
            </ul>
          </Card>

          {/* Spend by Category */}
          <Card className="rounded-3xl border-0 bg-white p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-[#2c3432] mb-6" style={{ fontFamily: 'Plus Jakarta Sans, sans-serif' }}>
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
                        <span className="text-sm font-medium text-[#2c3432]">{category.category}</span>
                      </div>
                      <span className="text-sm font-bold text-[#386381]">₹{category.amount.toFixed(0)}</span>
                    </div>
                    <div className="w-full h-2 bg-[#f0f5f2] rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-gradient-to-r from-[#386381] to-[#2b5775] rounded-full transition-all duration-500"
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
          <Alert className="mt-6 border-0 bg-[#f0f5f2] rounded-2xl">
            <AlertCircle className="h-4 w-4 text-[#386381]" />
            <AlertDescription className="text-[#2c3432] text-sm">
              <strong>Note:</strong> This forecast uses a simplified prediction model. Add more transaction data for improved accuracy.
            </AlertDescription>
          </Alert>
        )}

        {/* Footer */}
        <div className="mt-12 text-center">
          <p className="text-xs text-[#abb4b1] uppercase tracking-wide">
            AI-Powered Forecast Based on Your Spending Patterns
          </p>
        </div>
      </main>
    </div>
  );
}
