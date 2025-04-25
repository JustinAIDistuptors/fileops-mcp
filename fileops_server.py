#!/usr/bin/env python3
"""
FileOps MCP Server
This file implements a simple MCP server for file operations.
"""

import os
import json
import logging
import tempfile
from pathlib import Path
import glob
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Configure logging
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("fileops-mcp")

# Create FastAPI app
app = FastAPI(title="FileOps MCP Server")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create a temp directory for file operations
TEMP_DIR = tempfile.mkdtemp(prefix="fileops_")
logger.info(f"Using temporary directory: {TEMP_DIR}")

# MCP endpoint
@app.post("/mcp/{function_name}")
async def handle_mcp_request(function_name: str, request: Request):
    """Handle MCP request"""
    try:
        # Parse request body
        body = await request.body()
        parameters = json.loads(body) if body else {}
        
        # Log the request
        logger.info(f"Received request for function: {function_name}")
        logger.info(f"Parameters: {parameters}")
        
        # Handle different functions
        if function_name == "write_file":
            filepath = parameters.get("filepath")
            content = parameters.get("content")
            
            if not filepath:
                return {"error": "filepath parameter is required"}
            if content is None:
                return {"error": "content parameter is required"}
            
            # Make the path safe by ensuring it's within our temp directory
            safe_path = os.path.normpath(os.path.join(TEMP_DIR, filepath.lstrip("/")))
            
            # Create parent directories if they don't exist
            os.makedirs(os.path.dirname(safe_path), exist_ok=True)
            
            # Write the file
            with open(safe_path, "w") as f:
                f.write(content)
            
            result = {"success": True, "filepath": filepath}
        
        elif function_name == "read_file":
            filepath = parameters.get("filepath")
            
            if not filepath:
                return {"error": "filepath parameter is required"}
            
            # Make the path safe by ensuring it's within our temp directory
            safe_path = os.path.normpath(os.path.join(TEMP_DIR, filepath.lstrip("/")))
            
            # Check if the file exists
            if not os.path.isfile(safe_path):
                return {"error": f"File {filepath} not found"}
            
            # Read the file
            with open(safe_path, "r") as f:
                content = f.read()
            
            result = {"content": content, "filepath": filepath}
        
        elif function_name == "list_directory":
            directory_path = parameters.get("directory_path")
            
            if not directory_path:
                return {"error": "directory_path parameter is required"}
            
            # Make the path safe by ensuring it's within our temp directory
            safe_path = os.path.normpath(os.path.join(TEMP_DIR, directory_path.lstrip("/")))
            
            # Check if the directory exists
            if not os.path.isdir(safe_path):
                # Create the directory if it doesn't exist
                os.makedirs(safe_path, exist_ok=True)
            
            # List the directory
            items = []
            for item in os.listdir(safe_path):
                item_path = os.path.join(safe_path, item)
                items.append({
                    "name": item,
                    "is_directory": os.path.isdir(item_path),
                    "size": os.path.getsize(item_path) if os.path.isfile(item_path) else None
                })
            
            result = {"items": items, "directory_path": directory_path}
        
        elif function_name == "search_files":
            directory_path = parameters.get("directory_path")
            pattern = parameters.get("pattern")
            
            if not directory_path:
                return {"error": "directory_path parameter is required"}
            if not pattern:
                return {"error": "pattern parameter is required"}
            
            # Make the path safe by ensuring it's within our temp directory
            safe_path = os.path.normpath(os.path.join(TEMP_DIR, directory_path.lstrip("/")))
            
            # Check if the directory exists
            if not os.path.isdir(safe_path):
                return {"error": f"Directory {directory_path} not found"}
            
            # Search for files
            search_pattern = os.path.join(safe_path, pattern)
            matches = glob.glob(search_pattern)
            
            # Convert to relative paths
            relative_matches = [os.path.relpath(match, TEMP_DIR) for match in matches]
            
            result = {"matches": relative_matches, "pattern": pattern, "directory_path": directory_path}
        
        elif function_name == "delete_file":
            filepath = parameters.get("filepath")
            
            if not filepath:
                return {"error": "filepath parameter is required"}
            
            # Make the path safe by ensuring it's within our temp directory
            safe_path = os.path.normpath(os.path.join(TEMP_DIR, filepath.lstrip("/")))
            
            # Check if the file exists
            if not os.path.exists(safe_path):
                return {"error": f"File or directory {filepath} not found"}
            
            # Delete the file or directory
            if os.path.isdir(safe_path):
                import shutil
                shutil.rmtree(safe_path)
            else:
                os.remove(safe_path)
            
            result = {"success": True, "filepath": filepath}
        
        else:
            return {"error": f"Function {function_name} not supported"}
        
        logger.info(f"Result: {result}")
        return result
    except json.JSONDecodeError:
        logger.error("Invalid JSON in request body")
        return {"error": "Invalid JSON in request body"}
    except Exception as e:
        logger.error(f"Error handling request: {str(e)}")
        return {"error": str(e)}

@app.get("/")
async def root():
    """Root endpoint that returns information about the server"""
    return {
        "name": "FileOps MCP Server",
        "version": "1.0.0",
        "description": "MCP server for file operations",
        "functions": ["write_file", "read_file", "list_directory", "search_files", "delete_file"]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    logger.info(f"Starting FileOps MCP Server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
