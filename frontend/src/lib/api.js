// Frontend API client - connects to backend
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8002';
const API = `${BACKEND_URL}/api`;

// ==================== Expenses ====================

export async function getExpenses() {
  try {
    const response = await axios.get(`${API}/expenses`);
    return response.data || [];
  } catch (error) {
    console.error('getExpenses error:', error);
    return [];
  }
}

export async function postExpense(payload) {
  try {
    const response = await axios.post(`${API}/expenses`, payload, {
      headers: { 'Content-Type': 'application/json' }
    });
    return response.data;
  } catch (error) {
    console.error('postExpense error:', error);
    throw error;
  }
}

export async function deleteExpense(id) {
  try {
    await axios.delete(`${API}/expenses/${id}`);
    return { ok: true };
  } catch (error) {
    console.error('deleteExpense error:', error);
    throw error;
  }
}

// ==================== Analytics & Suggestions ====================

export async function getSuggestions() {
  try {
    const response = await axios.get(`${API}/suggestions`);
    return response.data || { suggestions: [] };
  } catch (error) {
    console.error('getSuggestions error:', error);
    return { suggestions: [] };
  }
}

export async function getAnalyticsSpending() {
  try {
    const response = await axios.get(`${API}/analytics/spending`);
    return response.data || { total_monthly: 0, by_category: [] };
  } catch (error) {
    console.error('getAnalyticsSpending error:', error);
    return { total_monthly: 0, by_category: [] };
  }
}

// ==================== Forecast ====================

export async function getForecast() {
  try {
    const response = await axios.get(`${API}/forecast/lstm`);
    return response.data || { forecast: [], trend: 'insufficient_data', confidence: 0, fallback: true, error: null };
  } catch (error) {
    console.error('getForecast error:', error);
    return { forecast: [], trend: 'error', confidence: 0, fallback: true, error: error.message };
  }
}

// ==================== Budgets ====================

export async function getBudgets() {
  try {
    const response = await axios.get(`${API}/budget/smart`);
    const data = response.data || { budget: [], total: 0, fallback: true, error: null };
    // Convert budget array to expected format
    return data.budget || [];
  } catch (error) {
    console.error('getBudgets error:', error);
    return [];
  }
}

export async function generateBudgets(options = {}) {
  try {
    const response = await axios.get(`${API}/budget/smart`);
    const data = response.data || { budget: [], total: 0, fallback: true, error: null };
    return { 
      ok: true, 
      budgets: data.budget || [], 
      meta: { 
        fallback: data.fallback, 
        method: data.metadata?.method,
        error: data.error 
      } 
    };
  } catch (error) {
    console.error('generateBudgets error:', error);
    return { ok: false, budgets: [], meta: { error: error.message } };
  }
}

// ==================== Anomalies ====================

export async function getAnomalies() {
  try {
    const response = await axios.get(`${API}/expenses/anomalies`);
    return response.data || { alerts: [], count: 0, fallback: false, error: null };
  } catch (error) {
    console.error('getAnomalies error:', error);
    return { alerts: [], count: 0, fallback: true, error: error.message };
  }
}

// ==================== Groups (Stub - not implemented in backend yet) ====================

export async function getGroups() {
  return [];
}

export async function getGroupExpenses(groupId) {
  return [];
}

export async function getGroupBalances(groupId) {
  return { settlements: [] };
}

export async function postGroupExpense(payload) {
  return { id: 'stub', ...payload };
}
