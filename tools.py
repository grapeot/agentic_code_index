"""Simple file system tools for the agent."""
import os
import subprocess
from pathlib import Path
from typing import Dict, Any


def cat_file(file_path: str) -> Dict[str, Any]:
    """Read and return the contents of a file.
    
    Args:
        file_path: Path to the file to read
        
    Returns:
        Dict with 'success', 'content', and 'error' fields
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return {
                "success": False,
                "content": None,
                "error": f"File not found: {file_path}"
            }
        if not path.is_file():
            return {
                "success": False,
                "content": None,
                "error": f"Path is not a file: {file_path}"
            }
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        return {
            "success": True,
            "content": content,
            "error": None
        }
    except Exception as e:
        return {
            "success": False,
            "content": None,
            "error": f"Error reading file: {str(e)}"
        }


def ls_directory(dir_path: str = ".") -> Dict[str, Any]:
    """List files and directories in a given path.
    
    Args:
        dir_path: Path to the directory to list (default: current directory)
        
    Returns:
        Dict with 'success', 'items', and 'error' fields
    """
    try:
        path = Path(dir_path)
        if not path.exists():
            return {
                "success": False,
                "items": None,
                "error": f"Directory not found: {dir_path}"
            }
        if not path.is_dir():
            return {
                "success": False,
                "items": None,
                "error": f"Path is not a directory: {dir_path}"
            }
        items = []
        for item in sorted(path.iterdir()):
            item_type = "directory" if item.is_dir() else "file"
            items.append({
                "name": item.name,
                "type": item_type,
                "path": str(item)
            })
        return {
            "success": True,
            "items": items,
            "error": None
        }
    except Exception as e:
        return {
            "success": False,
            "items": None,
            "error": f"Error listing directory: {str(e)}"
        }


def find_files(pattern: str, start_path: str = ".") -> Dict[str, Any]:
    """Find files matching a pattern using Unix find command.
    
    Args:
        pattern: Filename pattern to search for (e.g., "*.py", "test*")
        start_path: Starting directory for the search (default: current directory)
        
    Returns:
        Dict with 'success', 'files', and 'error' fields
    """
    try:
        path = Path(start_path)
        if not path.exists():
            return {
                "success": False,
                "files": None,
                "error": f"Start path not found: {start_path}"
            }
        
        # Use find command
        result = subprocess.run(
            ["find", str(path), "-name", pattern],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            return {
                "success": False,
                "files": None,
                "error": f"Find command failed: {result.stderr}"
            }
        
        files = [f.strip() for f in result.stdout.strip().split('\n') if f.strip()]
        return {
            "success": True,
            "files": files,
            "error": None
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "files": None,
            "error": "Find command timed out"
        }
    except Exception as e:
        return {
            "success": False,
            "files": None,
            "error": f"Error running find: {str(e)}"
        }


# Tool registry
TOOLS = {
    "cat": {
        "function": cat_file,
        "description": "Read the contents of a file. Use this when you need to see what's inside a file.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to read"
                }
            },
            "required": ["file_path"]
        }
    },
    "ls": {
        "function": ls_directory,
        "description": "List files and directories in a given path. Use this to explore the directory structure.",
        "parameters": {
            "type": "object",
            "properties": {
                "dir_path": {
                    "type": "string",
                    "description": "Path to the directory to list (default: current directory)",
                    "default": "."
                }
            },
            "required": []
        }
    },
    "find": {
        "function": find_files,
        "description": "Find files matching a pattern. Use this to search for files by name pattern.",
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Filename pattern (e.g., '*.py', 'test*')"
                },
                "start_path": {
                    "type": "string",
                    "description": "Starting directory for search (default: current directory)",
                    "default": "."
                }
            },
            "required": ["pattern"]
        }
    }
}

