"""Comprehensive test suite for the code indexing agent."""
import requests
import json
import time
import sys
from typing import List, Tuple

API_URL = "http://localhost:8001"
INDEX_URL = f"{API_URL}/index"
QUERY_URL = f"{API_URL}/query"

def wait_for_server(max_wait=30):
    """Wait for the server to be ready."""
    print("Waiting for server to be ready...")
    for i in range(max_wait):
        try:
            response = requests.get(f"{API_URL}/health", timeout=2)
            if response.status_code == 200:
                print("✓ Server is ready\n")
                return True
        except:
            pass
        time.sleep(1)
    print("✗ Server did not become ready in time\n")
    return False

def index_codebase(codebase_path: str = ".", output_dir: str = "test_index") -> bool:
    """Index the codebase."""
    print(f"📦 Indexing codebase: {codebase_path}")
    try:
        response = requests.post(
            INDEX_URL,
            json={"codebase_path": codebase_path, "output_dir": output_dir},
            timeout=300
        )
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Indexing successful")
            print(f"  Files: {result['total_files']}")
            print(f"  Total chunks: {result['total_chunks']}")
            print(f"  File chunks: {result['file_chunks']}")
            print(f"  Function chunks: {result['function_chunks']}\n")
            return True
        else:
            print(f"✗ Indexing failed: {response.status_code}")
            print(f"  {response.text}\n")
            return False
    except Exception as e:
        print(f"✗ Indexing error: {e}\n")
        return False

def test_query(question: str, category: str) -> Tuple[bool, dict]:
    """Test a query and return result."""
    print(f"🔍 [{category}] {question}")
    print("-" * 60)
    
    try:
        response = requests.post(
            QUERY_URL,
            json={"question": question, "max_iterations": 6},
            timeout=120
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Query successful")
            print(f"  Answer: {result['answer'][:200]}...")
            print(f"  Confidence: {result['confidence']}")
            print(f"  Sources: {len(result['sources'])} source(s)")
            if result.get('reasoning'):
                print(f"  Reasoning: {result['reasoning'][:100]}...")
            print()
            return True, result
        else:
            print(f"✗ Query failed: {response.status_code}")
            print(f"  {response.text}\n")
            return False, {}
    except Exception as e:
        print(f"✗ Query error: {e}\n")
        return False, {}

def main():
    """Run comprehensive tests."""
    print("=" * 60)
    print("Comprehensive Test Suite for Code Indexing Agent")
    print("=" * 60)
    print()
    
    # Wait for server
    if not wait_for_server():
        print("Please start the server first:")
        print("  ./launch_backend.sh")
        sys.exit(1)
    
    # Index codebase
    if not index_codebase():
        print("Failed to index codebase. Exiting.")
        sys.exit(1)
    
    # Wait a bit for index to be loaded
    time.sleep(2)
    
    # Test cases
    test_cases = [
        ("Model-related", "这个项目使用了哪些 Pydantic 模型？它们的作用是什么？"),
        ("Data format", "FinalAnswer 模型的数据格式是什么？包含哪些字段？"),
        ("OpenAI API", "代码中是如何调用 OpenAI API 的？使用了哪些模型？"),
        ("Architecture", "这个项目的整体架构是什么？有哪些主要模块？"),
        ("Tools", "Agent 可以使用哪些工具？这些工具是如何实现的？"),
    ]
    
    print("=" * 60)
    print("Running Query Tests")
    print("=" * 60)
    print()
    
    results = []
    for category, question in test_cases:
        success, result = test_query(question, category)
        results.append((category, question, success, result))
        time.sleep(1)  # Small delay between tests
    
    # Summary
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    passed = sum(1 for _, _, success, _ in results if success)
    total = len(results)
    print(f"Passed: {passed}/{total}\n")
    
    for category, question, success, result in results:
        status = "✓" if success else "✗"
        print(f"{status} [{category}]")
        print(f"   Q: {question}")
        if success:
            print(f"   A: {result.get('answer', '')[:100]}...")
        print()
    
    # Save results to file
    with open("test_results.json", "w", encoding="utf-8") as f:
        json.dump({
            "summary": {
                "total": total,
                "passed": passed,
                "failed": total - passed
            },
            "results": [
                {
                    "category": cat,
                    "question": q,
                    "success": s,
                    "answer": r.get("answer", ""),
                    "confidence": r.get("confidence", ""),
                    "sources": r.get("sources", []),
                    "reasoning": r.get("reasoning", "")
                }
                for cat, q, s, r in results
            ]
        }, f, ensure_ascii=False, indent=2)
    
    print(f"📄 Detailed results saved to test_results.json")
    
    if passed == total:
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print(f"\n❌ {total - passed} test(s) failed")
        sys.exit(1)

if __name__ == "__main__":
    main()

