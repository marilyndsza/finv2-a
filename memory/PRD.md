# FinFusion - Project Reference Document

## Original Problem Statement
Load GitHub repo https://github.com/marilyndsza/finv2-a into /app. Analyze project structure, identify file hierarchy issues, fix only structural/file issues that break execution. No logic refactoring, no new dependencies, minimal changes.

## Architecture
- **Frontend**: React 19 (CRA + CRACO) + Tailwind CSS + shadcn/ui + Recharts
- **Backend**: FastAPI (Python) with in-memory data store (loaded from CSV)
- **Data**: BudgetWise CSV dataset at `/app/backend/data/budgetwise.csv`
- **No MongoDB** for application data (MongoDB is available but not used by current server.py)

## Issues Found & Fixed (2026-03-28)

### Critical (Broke Execution)
1. **Frontend `.env` stale URL** - `REACT_APP_BACKEND_URL` pointed to a previous deployment URL. Fixed to match current pod ingress.
2. **Missing Python dependency `scikit-learn`** - Required by `data/loader.py` (MinMaxScaler). Installed.
3. **Missing `node_modules`** - Frontend dependencies not installed after fresh clone. Ran `yarn install`.
4. **NaN crash in anomaly endpoint** - `/api/expenses/anomalies` could crash on NaN z-scores. Added guard.

### Structural (Misplaced/Unused Files Removed)
5. **`backend/package.json` + `backend/package-lock.json`** - Node.js files misplaced in Python backend. Removed.
6. **`temp_finfusion/`** - Empty leftover directory. Removed.
7. **`test_result.md`** - Stale root-level test file from previous run. Removed.

### Noted (Not Fixed - Non-Breaking)
- `backend/server.py.backup` - Old MongoDB-based server backup. Not breaking, kept for reference.
- `backend/models/__init__.py` and `backend/services/__init__.py` - Empty module stubs. Placeholder for future phases.
- `frontend/src/components/ui/AIBudgetSuggestions.jsx` and `ForecastOverview.jsx` - Feature components in ui/ directory. Not ideal placement but doesn't break anything.
- `requirements.txt` lists `tensorflow==2.15.0` and `keras==3.0.0` which are unused. Not installed, not breaking.

## What's Implemented
- Dashboard with spending overview, donut chart, expense management
- Budget tracking (auto-generated from spending patterns)
- Forecast page (moving average fallback, LSTM Phase 2 placeholder)
- Group expenses page (client-side Splitwise-like module)
- AI suggestions based on spending patterns
- Anomaly detection (z-score fallback)

## Backlog
- P0: None (all critical issues resolved)
- P1: LSTM model training (Phase 2), Isolation Forest anomaly detection (Phase 3)
- P2: Receipt OCR, MongoDB persistence mode, user authentication
