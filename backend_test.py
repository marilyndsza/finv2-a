#!/usr/bin/env python3
"""
Backend API Testing for FinFusion Personal Finance App
Tests all API endpoints to ensure they're working correctly.
"""

import requests
import sys
import json
from datetime import datetime

class FinFusionAPITester:
    def __init__(self, base_url="https://1f4c8a69-bcfb-443f-9b04-659d348f5e39.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}")
        else:
            print(f"❌ {name} - {details}")
        
        self.test_results.append({
            "test": name,
            "success": success,
            "details": details
        })

    def run_test(self, name, method, endpoint, expected_status=200, data=None, validate_response=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}

        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=10)

            # Check status code
            if response.status_code != expected_status:
                self.log_test(name, False, f"Expected {expected_status}, got {response.status_code}")
                return False, {}

            # Parse JSON response
            try:
                response_data = response.json()
            except json.JSONDecodeError:
                self.log_test(name, False, "Invalid JSON response")
                return False, {}

            # Custom validation if provided
            if validate_response:
                validation_result = validate_response(response_data)
                if not validation_result[0]:
                    self.log_test(name, False, validation_result[1])
                    return False, response_data

            self.log_test(name, True)
            return True, response_data

        except requests.exceptions.RequestException as e:
            self.log_test(name, False, f"Request error: {str(e)}")
            return False, {}
        except Exception as e:
            self.log_test(name, False, f"Unexpected error: {str(e)}")
            return False, {}

    def validate_health_response(self, data):
        """Validate health endpoint response"""
        if not isinstance(data, dict):
            return False, "Response is not a dictionary"
        
        if not data.get('ok'):
            return False, "Health check failed - ok is not True"
        
        if not data.get('data_loaded'):
            return False, "Data not loaded - data_loaded is not True"
        
        return True, "Health check passed"

    def validate_expenses_response(self, data):
        """Validate expenses endpoint response"""
        if not isinstance(data, list):
            return False, "Response is not a list"
        
        if len(data) == 0:
            return False, "No expenses found in response"
        
        # Check first expense structure
        expense = data[0]
        required_fields = ['id', 'amount', 'category', 'description', 'date']
        for field in required_fields:
            if field not in expense:
                return False, f"Missing required field: {field}"
        
        return True, f"Found {len(data)} expenses"

    def validate_analytics_response(self, data):
        """Validate analytics spending endpoint response"""
        if not isinstance(data, dict):
            return False, "Response is not a dictionary"
        
        if 'total_monthly' not in data:
            return False, "Missing total_monthly field"
        
        if 'by_category' not in data:
            return False, "Missing by_category field"
        
        if not isinstance(data['by_category'], list):
            return False, "by_category is not a list"
        
        return True, f"Analytics data with total: {data['total_monthly']}"

    def validate_suggestions_response(self, data):
        """Validate suggestions endpoint response"""
        if not isinstance(data, dict):
            return False, "Response is not a dictionary"
        
        if 'suggestions' not in data:
            return False, "Missing suggestions field"
        
        if not isinstance(data['suggestions'], list):
            return False, "suggestions is not a list"
        
        return True, f"Found {len(data['suggestions'])} suggestions"

    def validate_forecast_response(self, data):
        """Validate forecast LSTM endpoint response"""
        if not isinstance(data, dict):
            return False, "Response is not a dictionary"
        
        required_fields = ['forecast', 'trend', 'confidence', 'fallback']
        for field in required_fields:
            if field not in data:
                return False, f"Missing required field: {field}"
        
        if not isinstance(data['forecast'], list):
            return False, "forecast is not a list"
        
        return True, f"Forecast with {len(data['forecast'])} data points, trend: {data['trend']}"

    def validate_budget_response(self, data):
        """Validate smart budget endpoint response"""
        if not isinstance(data, dict):
            return False, "Response is not a dictionary"
        
        required_fields = ['budget', 'total', 'current_spending', 'fallback']
        for field in required_fields:
            if field not in data:
                return False, f"Missing required field: {field}"
        
        if not isinstance(data['budget'], list):
            return False, "budget is not a list"
        
        return True, f"Budget with {len(data['budget'])} categories, total: {data['total']}"

    def validate_anomalies_response(self, data):
        """Validate anomalies endpoint response"""
        if not isinstance(data, dict):
            return False, "Response is not a dictionary"
        
        required_fields = ['alerts', 'count', 'fallback']
        for field in required_fields:
            if field not in data:
                return False, f"Missing required field: {field}"
        
        if not isinstance(data['alerts'], list):
            return False, "alerts is not a list"
        
        return True, f"Anomaly detection with {data['count']} alerts"

    def test_create_expense(self):
        """Test creating a new expense"""
        test_expense = {
            "amount": 150.50,
            "category": "Food",
            "description": "Test expense from API test",
            "date": datetime.now().strftime("%Y-%m-%d")
        }
        
        def validate_create_response(data):
            if not isinstance(data, dict):
                return False, "Response is not a dictionary"
            
            required_fields = ['id', 'amount', 'category', 'description', 'date']
            for field in required_fields:
                if field not in data:
                    return False, f"Missing required field: {field}"
            
            if data['amount'] != test_expense['amount']:
                return False, f"Amount mismatch: expected {test_expense['amount']}, got {data['amount']}"
            
            return True, "Expense created successfully"
        
        return self.run_test(
            "Create Expense",
            "POST",
            "expenses",
            200,  # Backend returns 200 instead of 201
            test_expense,
            validate_create_response
        )

    def run_all_tests(self):
        """Run all API tests"""
        print("=" * 60)
        print("🧪 FinFusion API Testing Started")
        print("=" * 60)
        print(f"Testing backend at: {self.base_url}")
        print()

        # Test 1: Health Check
        self.run_test(
            "Health Check",
            "GET",
            "health",
            200,
            validate_response=self.validate_health_response
        )

        # Test 2: Get Expenses
        self.run_test(
            "Get Expenses",
            "GET",
            "expenses",
            200,
            validate_response=self.validate_expenses_response
        )

        # Test 3: Analytics Spending
        self.run_test(
            "Analytics Spending",
            "GET",
            "analytics/spending",
            200,
            validate_response=self.validate_analytics_response
        )

        # Test 4: AI Suggestions
        self.run_test(
            "AI Suggestions",
            "GET",
            "suggestions",
            200,
            validate_response=self.validate_suggestions_response
        )

        # Test 5: Forecast LSTM
        self.run_test(
            "Forecast LSTM",
            "GET",
            "forecast/lstm",
            200,
            validate_response=self.validate_forecast_response
        )

        # Test 6: Smart Budget
        self.run_test(
            "Smart Budget",
            "GET",
            "budget/smart",
            200,
            validate_response=self.validate_budget_response
        )

        # Test 7: Anomaly Detection
        self.run_test(
            "Anomaly Detection",
            "GET",
            "expenses/anomalies",
            200,
            validate_response=self.validate_anomalies_response
        )

        # Test 8: Create Expense (POST)
        success, created_expense = self.test_create_expense()
        
        # Test 9: Delete Expense (if creation was successful)
        if success and created_expense.get('id'):
            self.run_test(
                "Delete Expense",
                "DELETE",
                f"expenses/{created_expense['id']}",
                200
            )

        # Print Results
        print()
        print("=" * 60)
        print("📊 Test Results Summary")
        print("=" * 60)
        print(f"Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed / self.tests_run * 100):.1f}%")
        print()

        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed! Backend API is working correctly.")
            return 0
        else:
            print("⚠️  Some tests failed. Check the details above.")
            print()
            print("Failed Tests:")
            for result in self.test_results:
                if not result['success']:
                    print(f"  - {result['test']}: {result['details']}")
            return 1

def main():
    """Main test runner"""
    tester = FinFusionAPITester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())