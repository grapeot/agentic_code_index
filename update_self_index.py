#!/usr/bin/env python3
"""Update self_index for the current codebase."""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.indexing import CodeIndexer

def main():
    """Update self_index."""
    print("🔄 Updating self_index...")
    print("=" * 60)
    
    indexer = CodeIndexer()
    result = indexer.index(
        codebase_path=".",
        output_dir="self_index",
        max_workers=32
    )
    
    print("=" * 60)
    print("✅ Self index updated successfully!")
    print(f"   - Total files: {result['total_files']}")
    print(f"   - File chunks: {result['file_chunks']}")
    print(f"   - Function chunks: {result['function_chunks']}")
    print(f"   - Total chunks: {result['total_chunks']}")

if __name__ == "__main__":
    main()

