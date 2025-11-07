"""Test script for indexing with detailed logging."""
import os
import shutil
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from indexing import CodeIndexer

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,  # Use DEBUG to see all detailed logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    """Test indexing with cleanup and detailed output."""
    print("=" * 80)
    print("Testing Code Indexing with Parallel Processing")
    print("=" * 80)
    
    # Clean up test index
    test_index_dir = 'test_index_fix'
    if os.path.exists(test_index_dir):
        print(f"\n🧹 Cleaning up existing test index: {test_index_dir}")
        shutil.rmtree(test_index_dir)
        print("   ✓ Cleanup completed")
    
    # Initialize indexer
    print("\n🔧 Initializing CodeIndexer...")
    indexer = CodeIndexer()
    print("   ✓ Indexer initialized")
    print(f"   - Embedding model: {indexer.embedding_model}")
    print(f"   - Parse model: {indexer.parse_model}")
    
    # Get files to index
    print("\n🔍 Scanning for files to index...")
    files = [f for f in indexer._get_supported_files('.') 
             if '.venv' not in f and '__pycache__' not in f]
    print(f"   ✓ Found {len(files)} files to index")
    if len(files) > 0:
        print(f"   First 5 files:")
        for f in files[:5]:
            print(f"     - {f}")
    
    # Test indexing
    print("\n🚀 Starting indexing process...")
    print("   (This may take a while with parallel processing)")
    print("-" * 80)
    
    try:
        result = indexer.index('.', 'test_index_fix', max_workers=32)
        
        print("-" * 80)
        print("\n✅ Indexing completed successfully!")
        print("\n📊 Results:")
        print(f"   Status: {result.get('status', 'unknown')}")
        print(f"   Total files: {result.get('total_files', 0)}")
        print(f"   Total chunks: {result.get('total_chunks', 0)}")
        print(f"   File chunks: {result.get('file_chunks', 0)}")
        print(f"   Function chunks: {result.get('function_chunks', 0)}")
        print(f"   Output directory: {result.get('output_dir', 'unknown')}")
        
        # Verify output files
        print("\n🔍 Verifying output files...")
        output_dir = result.get('output_dir', 'test_index_fix')
        expected_files = ['file_index.faiss', 'function_index.faiss', 'metadata.json']
        for filename in expected_files:
            filepath = os.path.join(output_dir, filename)
            if os.path.exists(filepath):
                size = os.path.getsize(filepath)
                print(f"   ✓ {filename} exists ({size:,} bytes)")
            else:
                print(f"   ✗ {filename} missing")
        
        print("\n" + "=" * 80)
        print("Test completed successfully!")
        print("=" * 80)
        
    except Exception as e:
        print("\n" + "=" * 80)
        print("❌ Indexing failed with error:")
        print(f"   {type(e).__name__}: {e}")
        print("=" * 80)
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    main()

