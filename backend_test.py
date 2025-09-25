#!/usr/bin/env python3
"""
Backend API Test Suite for Check Payment Logger
Tests all backend endpoints including authentication and payment management
"""

import requests
import json
import base64
import time
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/frontend/.env')

# Get backend URL from environment
BACKEND_URL = os.getenv('EXPO_PUBLIC_BACKEND_URL', 'https://payment-logger-2.preview.emergentagent.com')
API_BASE_URL = f"{BACKEND_URL}/api"

# Test users from backend code
TEST_USERS = {
    "Rob": "GeenaJolee55!",
    "Geena": "Elijah6810!",
    "Eric": "Tactical1"
}

# Test data
SAMPLE_CHECK_IMAGE_BASE64 = base64.b64encode(b"Sample check image data for testing").decode('utf-8')

class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.results = []
    
    def add_result(self, test_name, passed, message=""):
        self.results.append({
            'test': test_name,
            'passed': passed,
            'message': message,
            'timestamp': datetime.now().isoformat()
        })
        if passed:
            self.passed += 1
        else:
            self.failed += 1
        
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
        if message:
            print(f"   Details: {message}")
    
    def print_summary(self):
        print(f"\n{'='*60}")
        print(f"TEST SUMMARY")
        print(f"{'='*60}")
        print(f"Total Tests: {self.passed + self.failed}")
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        print(f"Success Rate: {(self.passed/(self.passed + self.failed)*100):.1f}%")
        
        if self.failed > 0:
            print(f"\nFAILED TESTS:")
            for result in self.results:
                if not result['passed']:
                    print(f"- {result['test']}: {result['message']}")

def test_health_check():
    """Test the health check endpoint"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if 'status' in data and data['status'] == 'healthy':
                return True, f"Health check successful: {data}"
            else:
                return False, f"Unexpected response format: {data}"
        else:
            return False, f"HTTP {response.status_code}: {response.text}"
    except Exception as e:
        return False, f"Request failed: {str(e)}"

def test_login_valid_credentials():
    """Test login with valid credentials for all users"""
    results = []
    tokens = {}
    
    for username, password in TEST_USERS.items():
        try:
            payload = {
                "username": username,
                "password": password
            }
            response = requests.post(f"{API_BASE_URL}/login", json=payload, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ['access_token', 'user_id', 'username']
                
                if all(field in data for field in required_fields):
                    if data['username'] == username and data['user_id'] == username:
                        tokens[username] = data['access_token']
                        results.append((True, f"Login successful for {username}"))
                    else:
                        results.append((False, f"User data mismatch for {username}: {data}"))
                else:
                    results.append((False, f"Missing fields in response for {username}: {data}"))
            else:
                results.append((False, f"HTTP {response.status_code} for {username}: {response.text}"))
                
        except Exception as e:
            results.append((False, f"Login request failed for {username}: {str(e)}"))
    
    # Check if all logins were successful
    all_passed = all(result[0] for result in results)
    message = "; ".join([result[1] for result in results])
    
    return all_passed, message, tokens

def test_login_invalid_credentials():
    """Test login with invalid credentials"""
    test_cases = [
        {"username": "Rob", "password": "wrongpassword"},
        {"username": "InvalidUser", "password": "GeenaJolee55!"},
        {"username": "", "password": ""},
    ]
    
    results = []
    
    for case in test_cases:
        try:
            response = requests.post(f"{API_BASE_URL}/login", json=case, timeout=10)
            
            if response.status_code == 401:
                results.append((True, f"Correctly rejected invalid credentials: {case['username']}"))
            else:
                results.append((False, f"Should have rejected {case['username']} but got HTTP {response.status_code}"))
                
        except Exception as e:
            results.append((False, f"Request failed for invalid login {case['username']}: {str(e)}"))
    
    all_passed = all(result[0] for result in results)
    message = "; ".join([result[1] for result in results])
    
    return all_passed, message

def test_create_payment(token, username):
    """Test creating a payment entry with valid token"""
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        payment_data = {
            "businessName": f"Acme Corp - {username}",
            "quantitySold": 150,
            "checkImageBase64": SAMPLE_CHECK_IMAGE_BASE64
        }
        
        response = requests.post(f"{API_BASE_URL}/payments", json=payment_data, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            required_fields = ['id', 'userId', 'businessName', 'quantitySold', 'timestamp']
            
            if all(field in data for field in required_fields):
                if (data['userId'] == username and 
                    data['businessName'] == payment_data['businessName'] and
                    data['quantitySold'] == payment_data['quantitySold']):
                    return True, f"Payment created successfully for {username}: ID {data['id']}"
                else:
                    return False, f"Payment data mismatch for {username}: {data}"
            else:
                return False, f"Missing fields in payment response for {username}: {data}"
        else:
            return False, f"HTTP {response.status_code} for {username}: {response.text}"
            
    except Exception as e:
        return False, f"Create payment request failed for {username}: {str(e)}"

def test_get_payments(token, username):
    """Test retrieving payment entries with valid token"""
    try:
        headers = {
            "Authorization": f"Bearer {token}"
        }
        
        response = requests.get(f"{API_BASE_URL}/payments", headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if isinstance(data, list):
                # Check if we have at least one payment (from the create test)
                if len(data) > 0:
                    payment = data[0]
                    required_fields = ['id', 'userId', 'businessName', 'quantitySold', 'timestamp']
                    
                    if all(field in payment for field in required_fields):
                        if payment['userId'] == username:
                            return True, f"Retrieved {len(data)} payments for {username}"
                        else:
                            return False, f"Payment userId mismatch for {username}: {payment}"
                    else:
                        return False, f"Missing fields in payment data for {username}: {payment}"
                else:
                    return True, f"No payments found for {username} (valid empty response)"
            else:
                return False, f"Expected list response for {username}, got: {type(data)}"
        else:
            return False, f"HTTP {response.status_code} for {username}: {response.text}"
            
    except Exception as e:
        return False, f"Get payments request failed for {username}: {str(e)}"

def test_protected_endpoints_without_token():
    """Test accessing protected endpoints without authentication token"""
    endpoints = [
        ("POST", "/payments", {"businessName": "Test", "quantitySold": 1, "checkImageBase64": "test"}),
        ("GET", "/payments", None)
    ]
    
    results = []
    
    for method, endpoint, data in endpoints:
        try:
            url = f"{API_BASE_URL}{endpoint}"
            
            if method == "POST":
                response = requests.post(url, json=data, timeout=10)
            else:
                response = requests.get(url, timeout=10)
            
            if response.status_code == 401 or response.status_code == 403:
                results.append((True, f"Correctly rejected {method} {endpoint} without token"))
            else:
                results.append((False, f"Should have rejected {method} {endpoint} but got HTTP {response.status_code}"))
                
        except Exception as e:
            results.append((False, f"Request failed for {method} {endpoint}: {str(e)}"))
    
    all_passed = all(result[0] for result in results)
    message = "; ".join([result[1] for result in results])
    
    return all_passed, message

def main():
    """Run all backend API tests"""
    print(f"Starting Backend API Tests for Check Payment Logger")
    print(f"Backend URL: {API_BASE_URL}")
    print(f"{'='*60}")
    
    results = TestResults()
    
    # Test 1: Health Check
    print("\n1. Testing Health Check Endpoint...")
    passed, message = test_health_check()
    results.add_result("Health Check", passed, message)
    
    # Test 2: Valid Login
    print("\n2. Testing Login with Valid Credentials...")
    passed, message, tokens = test_login_valid_credentials()
    results.add_result("Login Valid Credentials", passed, message)
    
    # Test 3: Invalid Login
    print("\n3. Testing Login with Invalid Credentials...")
    passed, message = test_login_invalid_credentials()
    results.add_result("Login Invalid Credentials", passed, message)
    
    # Test 4: Protected endpoints without token
    print("\n4. Testing Protected Endpoints Without Token...")
    passed, message = test_protected_endpoints_without_token()
    results.add_result("Protected Endpoints Without Token", passed, message)
    
    # Test 5 & 6: Payment operations (only if we have valid tokens)
    if tokens:
        for username, token in tokens.items():
            print(f"\n5. Testing Create Payment for {username}...")
            passed, message = test_create_payment(token, username)
            results.add_result(f"Create Payment ({username})", passed, message)
            
            print(f"\n6. Testing Get Payments for {username}...")
            passed, message = test_get_payments(token, username)
            results.add_result(f"Get Payments ({username})", passed, message)
    else:
        results.add_result("Create Payment", False, "No valid tokens available")
        results.add_result("Get Payments", False, "No valid tokens available")
    
    # Print final summary
    results.print_summary()
    
    return results.failed == 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)