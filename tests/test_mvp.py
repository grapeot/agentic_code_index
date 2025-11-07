"""Simple test script to verify the MVP works."""
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Test if we can import (will fail if dependencies not installed)
try:
    from src.agent import Agent
    from src.models import FinalAnswer
    from src.tools import cat_file, ls_directory, find_files
    print("✓ All imports successful")
except ImportError as e:
    print(f"✗ Import failed: {e}")
    print("Please install dependencies first:")
    print("  uv pip install -r requirements.txt")
    sys.exit(1)

# Test tools
print("\n--- Testing Tools ---")
print("\n1. Testing ls_directory:")
result = ls_directory(".")
if result["success"]:
    print(f"   ✓ Found {len(result['items'])} items")
    for item in result["items"][:5]:
        print(f"      - {item['name']} ({item['type']})")
else:
    print(f"   ✗ Error: {result['error']}")

print("\n2. Testing cat_file (reading this file):")
result = cat_file(__file__)
if result["success"]:
    print(f"   ✓ File read successfully ({len(result['content'])} chars)")
else:
    print(f"   ✗ Error: {result['error']}")

print("\n3. Testing find_files:")
result = find_files("*.py", ".")
if result["success"]:
    print(f"   ✓ Found {len(result['files'])} Python files")
    for f in result["files"][:3]:
        print(f"      - {f}")
else:
    print(f"   ✗ Error: {result['error']}")

# Test Agent initialization
print("\n--- Testing Agent Initialization ---")
try:
    agent = Agent(model="gpt-5-mini", max_iterations=3)
    print("✓ Agent initialized successfully")
    print(f"   Model: {agent.model}")
    print(f"   Max iterations: {agent.max_iterations}")
except Exception as e:
    print(f"✗ Agent initialization failed: {e}")
    sys.exit(1)

# Test Pydantic model
print("\n--- Testing Pydantic Model ---")
try:
    answer = FinalAnswer(
        answer="This is a test answer",
        confidence="high",
        sources=["test.py"],
        reasoning="Testing the model"
    )
    print("✓ FinalAnswer model created successfully")
    print(f"   Answer: {answer.answer[:50]}...")
    print(f"   Confidence: {answer.confidence}")
    print(f"   Sources: {answer.sources}")
    
    # Test JSON serialization
    json_str = answer.model_dump_json()
    print(f"   JSON serialization: ✓ ({len(json_str)} chars)")
except Exception as e:
    print(f"✗ Pydantic model test failed: {e}")
    sys.exit(1)

# Test OpenAI Embedding API
print("\n--- Testing OpenAI Embedding API ---")
if not os.getenv("OPENAI_API_KEY"):
    print("⚠ OPENAI_API_KEY not set, skipping embedding test")
else:
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        test_texts = [
            "This is a test string for embedding",
            "这是中文测试文本",
            "def hello_world():\n    print('Hello, World!')"
        ]
        
        print(f"   Testing with {len(test_texts)} text samples...")
        print(f"   Model: text-embedding-3-small")
        
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=test_texts
        )
        
        print(f"   ✓ Embedding API call successful")
        print(f"   ✓ Generated {len(response.data)} embeddings")
        
        for i, embedding_data in enumerate(response.data):
            dim = len(embedding_data.embedding)
            print(f"      Embedding {i+1}: dimension={dim}, text='{test_texts[i][:30]}...'")
        
        # Test single embedding
        single_response = client.embeddings.create(
            model="text-embedding-3-small",
            input="Single text embedding test"
        )
        print(f"   ✓ Single embedding test successful (dim={len(single_response.data[0].embedding)})")
        
    except Exception as e:
        print(f"✗ Embedding API test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

# Test actual Agent query with tools
print("\n--- Testing Agent Query with Tools ---")
if not os.getenv("OPENAI_API_KEY"):
    print("⚠ OPENAI_API_KEY not set, skipping Agent query test")
    print("\n--- All basic tests passed! ---")
    sys.exit(0)

try:
    print("Testing: '列出当前目录下的所有 Python 文件'")
    result = agent.query("列出当前目录下的所有 Python 文件")
    print("✓ Agent query completed successfully")
    print(f"\n   Answer: {result.answer[:200]}...")
    print(f"   Confidence: {result.confidence}")
    print(f"   Sources: {result.sources}")
    if result.reasoning:
        print(f"   Reasoning: {result.reasoning}")
except Exception as e:
    print(f"✗ Agent query failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n--- All tests passed! ---")
