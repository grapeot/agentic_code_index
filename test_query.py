"""Automated test for the query endpoint."""
import requests
import json
import time
import sys

API_URL = "http://localhost:8001/query"

def test_query(question: str, expected_success: bool = True):
    """Test a query and return the result."""
    print(f"\n{'='*60}")
    print(f"Testing query: {question}")
    print(f"{'='*60}")
    
    payload = {
        "question": question,
        "model": "gpt-5-mini",
        "max_iterations": 6
    }
    
    try:
        response = requests.post(API_URL, json=payload, timeout=120)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Query successful")
            print(f"  Answer: {result.get('answer', '')[:200]}...")
            print(f"  Confidence: {result.get('confidence', 'unknown')}")
            print(f"  Sources: {result.get('sources', [])}")
            if result.get('reasoning'):
                print(f"  Reasoning: {result.get('reasoning')}")
            return True
        else:
            print(f"✗ Query failed with status {response.status_code}")
            print(f"  Error: {response.text}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"✗ Cannot connect to server. Is it running?")
        print(f"  Start server with: ./launch_backend.sh")
        return False
    except requests.exceptions.Timeout:
        print(f"✗ Request timed out (took > 120 seconds)")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def wait_for_server(max_wait=30):
    """Wait for the server to be ready."""
    print("Waiting for server to be ready...")
    for i in range(max_wait):
        try:
            response = requests.get("http://localhost:8001/health", timeout=2)
            if response.status_code == 200:
                print("✓ Server is ready")
                return True
        except:
            pass
        time.sleep(1)
        print(f"  Waiting... ({i+1}/{max_wait})")
    print("✗ Server did not become ready in time")
    return False

if __name__ == "__main__":
    # Wait for server
    if not wait_for_server():
        print("\nPlease start the server first:")
        print("  ./launch_backend.sh")
        sys.exit(1)
    
    # Run tests
    tests = [
        ("列出当前目录下的所有文件", True),
        ("找到所有的 Python 文件", True),
        ("读取 design.md 文件的内容", True),
    ]
    
    results = []
    for question, expected in tests:
        success = test_query(question, expected)
        results.append((question, success))
        time.sleep(2)  # Small delay between tests
    
    # Summary
    print(f"\n{'='*60}")
    print("Test Summary")
    print(f"{'='*60}")
    passed = sum(1 for _, success in results if success)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    for question, success in results:
        status = "✓" if success else "✗"
        print(f"  {status} {question}")
    
    if passed == total:
        print("\n✓ All tests passed!")
        sys.exit(0)
    else:
        print(f"\n✗ {total - passed} test(s) failed")
        sys.exit(1)

