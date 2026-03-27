import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { TrendingUp, TrendingDown, Minus, AlertCircle } from 'lucide-react';
import * as api from '@/lib/api';

export default function Forecasting() {
  const [forecast, setForecast] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadForecast();
  }, []);

  async function loadForecast() {
    setLoading(true);
    try {
      const data = await api.getForecast();
      setForecast(data);
    } catch (error) {
      console.error('Forecast loading error:', error);
    } finally {
      setLoading(false);
    }
  }

  const getTrendIcon = (trend) => {
    switch (trend) {
      case 'increasing':
        return <TrendingUp className="w-5 h-5 text-red-500" />;
      case 'decreasing':
        return <TrendingDown className="w-5 h-5 text-green-500" />;
      case 'stable':
        return <Minus className="w-5 h-5 text-blue-500" />;
      default:
        return <AlertCircle className="w-5 h-5 text-gray-400" />;
    }
  };

  const getTrendColor = (trend) => {
    switch (trend) {
      case 'increasing':
        return 'text-red-600';
      case 'decreasing':
        return 'text-green-600';
      case 'stable':
        return 'text-blue-600';
      default:
        return 'text-gray-600';
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#f5f7fb] flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading forecast...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#f5f7fb]">
      {/* TOP NAVBAR */}
      <header className="sticky top-0 z-30 bg-white/80 backdrop-blur border-b border-slate-200">
        <div className="container mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-xl bg-indigo-500 flex items-center justify-center text-white text-lg font-bold">
              F
            </div>
            <span className="font-semibold text-slate-800 text-lg">FinFusion</span>
          </div>

          <nav className="hidden md:flex gap-6 text-sm font-medium text-slate-500">
            <Link to="/" className="hover:text-slate-800 transition-colors">
              Dashboard
            </Link>
            <Link to="/groups" className="hover:text-slate-800 transition-colors">
              Groups
            </Link>
            <Link to="/budgets" className="hover:text-slate-800 transition-colors">
              Budgets
            </Link>
            <Link to="/forecast" className="text-indigo-600 border-b-2 border-indigo-500 pb-1">
              Forecast
            </Link>
          </nav>

          <div className="h-9 w-9 rounded-full bg-gradient-to-tr from-indigo-400 to-purple-400 flex items-center justify-center text-white text-sm font-semibold">
            Y
          </div>
        </div>
      </header>

      {/* MAIN CONTENT */}
      <main className="container mx-auto px-6 py-8">
        <div className="mb-6">
          <h1 className="text-3xl md:text-4xl font-bold text-slate-900">
            Spending Forecast
          </h1>
          <p className="text-slate-500 mt-2">
            AI-powered predictions for your future spending
          </p>
        </div>

        {/* Fallback Warning */}
        {forecast?.fallback && (
          <Alert className="mb-6 border-amber-200 bg-amber-50">
            <AlertCircle className="h-4 w-4 text-amber-600" />
            <AlertDescription className="text-amber-800">
              <strong>Note:</strong> {forecast.error || 'Using simplified forecasting method'}
            </AlertDescription>
          </Alert>
        )}

        {/* Forecast Overview Card */}
        <Card className="rounded-[24px] border-0 shadow-sm bg-white p-6 mb-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">Spending Trend</h2>
              <p className="text-sm text-slate-500">Based on your recent transactions</p>
            </div>
            <div className="flex items-center gap-2">
              {getTrendIcon(forecast?.trend)}
              <span className={`text-lg font-semibold capitalize ${getTrendColor(forecast?.trend)}`}>
                {forecast?.trend || 'Unknown'}
              </span>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-slate-50 rounded-xl p-4">
              <p className="text-xs text-slate-500 uppercase mb-1">Confidence</p>
              <p className="text-2xl font-bold text-slate-900">
                {((forecast?.confidence || 0) * 100).toFixed(0)}%
              </p>
            </div>
            <div className="bg-slate-50 rounded-xl p-4">
              <p className="text-xs text-slate-500 uppercase mb-1">Method</p>
              <p className="text-lg font-semibold text-slate-900 capitalize">
                {forecast?.metadata?.method?.replace('_', ' ') || 'N/A'}
              </p>
            </div>
            <div className="bg-slate-50 rounded-xl p-4">
              <p className="text-xs text-slate-500 uppercase mb-1">Forecast Days</p>
              <p className="text-2xl font-bold text-slate-900">
                {forecast?.metadata?.forecast_days || 30}
              </p>
            </div>
          </div>
        </Card>

        {/* Forecast Data */}
        <Card className="rounded-[24px] border-0 shadow-sm bg-white p-6">
          <h2 className="text-lg font-semibold text-slate-900 mb-4">Daily Predictions</h2>
          
          {forecast?.forecast && forecast.forecast.length > 0 ? (
            <div className="space-y-2 max-h-[500px] overflow-y-auto">
              {forecast.forecast.slice(0, 30).map((item, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-3 rounded-lg hover:bg-slate-50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div className="h-8 w-8 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-600 text-xs font-semibold">
                      {index + 1}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-slate-900">{item.date}</p>
                      <p className="text-xs text-slate-500">Day {index + 1}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-semibold text-slate-900">
                      ₹{item.predicted_amount?.toFixed(2) || '0.00'}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-12 text-slate-400">
              <p>No forecast data available</p>
              <p className="text-sm mt-2">Add more transactions to generate predictions</p>
            </div>
          )}
        </Card>

        {/* Summary Stats */}
        {forecast?.forecast && forecast.forecast.length > 0 && (
          <Card className="rounded-[24px] border-0 shadow-sm bg-gradient-to-br from-indigo-50 to-purple-50 p-6 mt-6">
            <h2 className="text-lg font-semibold text-slate-900 mb-4">Forecast Summary</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-slate-600 mb-1">Total Predicted (30 days)</p>
                <p className="text-3xl font-bold text-indigo-600">
                  ₹{forecast.forecast.slice(0, 30).reduce((sum, item) => sum + (item.predicted_amount || 0), 0).toFixed(2)}
                </p>
              </div>
              <div>
                <p className="text-sm text-slate-600 mb-1">Daily Average</p>
                <p className="text-3xl font-bold text-purple-600">
                  ₹{(forecast.forecast.slice(0, 30).reduce((sum, item) => sum + (item.predicted_amount || 0), 0) / Math.min(30, forecast.forecast.length)).toFixed(2)}
                </p>
              </div>
            </div>
          </Card>
        )}
      </main>
    </div>
  );
}
