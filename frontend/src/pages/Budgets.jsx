import React, { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertCircle } from 'lucide-react';
import * as api from '@/lib/api';

export default function Budgets() {
  const [budgets, setBudgets] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    try {
      const [budgetsData, analyticsData] = await Promise.all([
        api.getBudgets(),
        api.getAnalyticsSpending()
      ]);
      
      // getBudgets returns the budget array directly
      setBudgets(Array.isArray(budgetsData) ? budgetsData : []);
      setAnalytics(analyticsData);
    } catch (error) {
      console.error('Error loading budgets:', error);
    } finally {
      setLoading(false);
    }
  }

  const getStatusColor = (percentage) => {
    if (percentage > 100) return { bg: 'bg-red-50', bar: 'bg-red-500', text: 'text-red-600' };
    if (percentage >= 70) return { bg: 'bg-amber-50', bar: 'bg-amber-500', text: 'text-amber-600' };
    return { bg: 'bg-emerald-50', bar: 'bg-emerald-500', text: 'text-emerald-600' };
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#f5f7fb] flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading budgets...</p>
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
            <a href="/" className="hover:text-slate-800 transition-colors">
              Dashboard
            </a>
            <a href="/groups" className="hover:text-slate-800 transition-colors">
              Groups
            </a>
            <a href="/budgets" className="text-indigo-600 border-b-2 border-indigo-500 pb-1">
              Budgets
            </a>
            <a href="/forecast" className="hover:text-slate-800 transition-colors">
              Forecast
            </a>
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
            Budget Management
          </h1>
          <p className="text-slate-500 mt-2">
            Track your spending against budget limits - {analytics?.metadata?.period_label || 'Current period'}
          </p>
        </div>

        {/* Summary Card */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <Card className="rounded-[24px] border-0 shadow-sm bg-gradient-to-br from-indigo-50 to-purple-50 p-6">
            <p className="text-sm text-slate-600 mb-2">Total Budget</p>
            <p className="text-4xl font-bold text-indigo-600">
              ₹{budgets.reduce((sum, b) => sum + (b.limit || 0), 0).toFixed(2)}
            </p>
          </Card>
          
          <Card className="rounded-[24px] border-0 shadow-sm bg-gradient-to-br from-pink-50 to-rose-50 p-6">
            <p className="text-sm text-slate-600 mb-2">Total Spent</p>
            <p className="text-4xl font-bold text-rose-600">
              ₹{budgets.reduce((sum, b) => sum + (b.current || 0), 0).toFixed(2)}
            </p>
          </Card>
        </div>

        {/* Info Alert */}
        <Alert className="mb-6 border-blue-200 bg-blue-50">
          <AlertCircle className="h-4 w-4 text-blue-600" />
          <AlertDescription className="text-blue-800">
            <strong>Auto-generated budgets:</strong> Budgets are automatically calculated based on your spending patterns (average × 1.1 buffer)
          </AlertDescription>
        </Alert>

        {/* Budget Categories */}
        <div className="space-y-4">
          {budgets && budgets.length > 0 ? (
            budgets.map((budget, index) => {
              const percentage = budget.percentage || 0;
              const colors = getStatusColor(percentage);
              
              return (
                <Card
                  key={index}
                  className="rounded-[24px] border-0 shadow-sm bg-white p-6"
                >
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <h3 className="text-lg font-semibold text-slate-900">
                        {budget.category}
                      </h3>
                      <p className="text-sm text-slate-500 mt-1">
                        ₹{budget.current?.toFixed(2) || '0.00'} of ₹{budget.limit?.toFixed(2) || '0.00'}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className={`text-2xl font-bold ${colors.text}`}>
                        {percentage.toFixed(0)}%
                      </p>
                      <p className="text-xs text-slate-500 mt-1">
                        {percentage > 100 ? 'Over budget' : percentage >= 70 ? 'Warning' : 'On track'}
                      </p>
                    </div>
                  </div>

                  {/* Progress Bar */}
                  <div className="w-full bg-slate-200 rounded-full h-3 overflow-hidden">
                    <div
                      className={`h-full ${colors.bar} transition-all duration-500 rounded-full`}
                      style={{ width: `${Math.min(percentage, 100)}%` }}
                    />
                  </div>

                  {/* Details */}
                  <div className={`mt-4 p-3 rounded-lg ${colors.bg}`}>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <p className="text-slate-600">Remaining</p>
                        <p className={`font-semibold ${colors.text}`}>
                          ₹{Math.max(0, (budget.limit || 0) - (budget.current || 0)).toFixed(2)}
                        </p>
                      </div>
                      <div>
                        <p className="text-slate-600">Over/Under</p>
                        <p className={`font-semibold ${colors.text}`}>
                          {percentage > 100 ? '+' : ''}
                          ₹{((budget.current || 0) - (budget.limit || 0)).toFixed(2)}
                        </p>
                      </div>
                    </div>
                  </div>
                </Card>
              );
            })
          ) : (
            <Card className="rounded-[24px] border-0 shadow-sm bg-white p-12 text-center">
              <p className="text-slate-400 mb-4">No budget data available</p>
              <p className="text-sm text-slate-500">
                Add expenses from the Dashboard to auto-generate budgets
              </p>
            </Card>
          )}
        </div>

        {/* Footer Info */}
        {budgets.length > 0 && (
          <div className="mt-8 p-4 bg-slate-50 rounded-lg">
            <p className="text-sm text-slate-600">
              💡 <strong>Tip:</strong> These budgets are auto-generated based on your spending patterns. 
              Add more expenses from the Dashboard to improve accuracy.
            </p>
          </div>
        )}
      </main>
    </div>
  );
}
