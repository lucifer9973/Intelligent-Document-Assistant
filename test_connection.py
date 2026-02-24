#!/usr/bin/env python
"""
Test script to verify frontend-backend connection
Run this to diagnose connection issues
"""
import requests
import sys
import json

API_BASE = "http://localhost:8000"
__test__ = False  # Utility script, not part of automated pytest collection.

def test_backend_health():
    """Test if backend is running"""
    print("=" * 60)
    print("Testing Backend Connection")
    print("=" * 60)
    try:
        response = requests.get(f"{API_BASE}/health", timeout=5)
        print(f"✓ Backend is running!")
        print(f"  Status Code: {response.status_code}")
        print(f"  Response: {json.dumps(response.json(), indent=2)}")
        return True
    except requests.exceptions.ConnectionError:
        print(f"✗ Cannot connect to backend at {API_BASE}")
        print(f"  Make sure to run: python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000")
        return False
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False

def test_cors():
    """Test if CORS is properly configured"""
    print("\n" + "=" * 60)
    print("Testing CORS Configuration")
    print("=" * 60)
    try:
        response = requests.options(
            f"{API_BASE}/upload",
            headers={"Origin": "file://"},
            timeout=5
        )
        print(f"✓ CORS headers present: {response.headers.get('access-control-allow-origin', 'Not found')}")
        return True
    except Exception as e:
        print(f"✗ CORS test failed: {str(e)}")
        return False

def test_endpoints():
    """Test all API endpoints"""
    print("\n" + "=" * 60)
    print("Testing API Endpoints")
    print("=" * 60)
    
    endpoints = [
        ("GET", "/health"),
        ("GET", "/"),
        ("GET", "/memory"),
    ]
    
    for method, endpoint in endpoints:
        try:
            if method == "GET":
                response = requests.get(f"{API_BASE}{endpoint}", timeout=5)
            print(f"✓ {method:4} {endpoint:20} → {response.status_code}")
        except Exception as e:
            print(f"✗ {method:4} {endpoint:20} → Error: {str(e)}")

def test_frontend_file():
    """Check if frontend file exists"""
    print("\n" + "=" * 60)
    print("Testing Frontend File")
    print("=" * 60)
    import os
    
    if os.path.exists("index.html"):
        print("✓ index.html found")
        print(f"  Size: {os.path.getsize('index.html')} bytes")
        return True
    else:
        print("✗ index.html NOT found in current directory")
        print(f"  Current directory: {os.getcwd()}")
        return False

def main():
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║  Intelligent Document Assistant - Connection Test      ║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    # Run tests
    backend_ok = test_backend_health()
    if backend_ok:
        test_cors()
        test_endpoints()
    
    test_frontend_file()
    
    print("\n" + "=" * 60)
    print("Summary & Next Steps")
    print("=" * 60)
    
    if backend_ok:
        print("✓ Backend is running")
        print("\nNext steps:")
        print("1. Open index.html in your browser")
        print("2. Check browser console (F12) for any errors")
        print("3. Try uploading a document")
    else:
        print("✗ Backend is NOT running")
        print("\nTo start backend:")
        print("  1. Activate venv: .\\venv\\Scripts\\Activate.ps1")
        print("  2. Run: python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000")
        print("  3. Wait for 'Application startup complete' message")
    
    print("\nFor more help, check CONNECTION_GUIDE.md")
    print()

if __name__ == "__main__":
    main()
