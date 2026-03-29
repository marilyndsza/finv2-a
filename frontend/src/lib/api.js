// Frontend API client — all endpoints return { data, metadata, error }
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';
const API = `${BACKEND_URL}/api`;

// ==================== Expenses ====================

export async function getExpenses() {
  try {
    const r = await axios.get(`${API}/expenses`);
    return r.data?.data || [];
  } catch (e) {
    console.error('getExpenses error:', e);
    return [];
  }
}

export async function postExpense(payload) {
  const r = await axios.post(`${API}/expenses`, payload, {
    headers: { 'Content-Type': 'application/json' },
  });
  return r.data;
}

export async function deleteExpense(id) {
  await axios.delete(`${API}/expenses/${id}`);
  return { ok: true };
}

// ==================== Analytics ====================

export async function getAnalyticsSpending() {
  try {
    const r = await axios.get(`${API}/analytics/spending`);
    return r.data || { data: {}, metadata: {}, error: null };
  } catch (e) {
    console.error('getAnalyticsSpending error:', e);
    return { data: { total_monthly: 0, by_category: [], comparison: null }, metadata: {}, error: e.message };
  }
}

// ==================== Insights / Suggestions ====================

export async function getSuggestions() {
  try {
    const r = await axios.get(`${API}/suggestions`);
    return r.data || { data: [], metadata: {}, error: null };
  } catch (e) {
    console.error('getSuggestions error:', e);
    return { data: [], metadata: {}, error: e.message };
  }
}

// ==================== Forecast ====================

export async function getForecast() {
  try {
    const r = await axios.get(`${API}/forecast/lstm`);
    return r.data || { data: {}, metadata: {}, error: null };
  } catch (e) {
    console.error('getForecast error:', e);
    return { data: { forecast: [], trend: 'error' }, metadata: {}, error: e.message };
  }
}

// ==================== Budgets ====================

export async function getBudgets() {
  try {
    const r = await axios.get(`${API}/budget/smart`);
    return r.data || { data: { budget: [], total: 0 }, metadata: {}, error: null };
  } catch (e) {
    console.error('getBudgets error:', e);
    return { data: { budget: [], total: 0 }, metadata: {}, error: e.message };
  }
}

// ==================== Anomalies ====================

export async function getAnomalies() {
  try {
    const r = await axios.get(`${API}/expenses/anomalies`);
    return r.data || { data: { alerts: [] }, metadata: {}, error: null };
  } catch (e) {
    console.error('getAnomalies error:', e);
    return { data: { alerts: [] }, metadata: {}, error: e.message };
  }
}

// ==================== Expenses by Category ====================

export async function getExpensesByCategory(category) {
  try {
    const r = await axios.get(`${API}/expenses/category/${encodeURIComponent(category)}`);
    return r.data?.data || [];
  } catch (e) {
    console.error('getExpensesByCategory error:', e);
    return [];
  }
}
