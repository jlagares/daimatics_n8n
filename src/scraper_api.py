#!/usr/bin/env python3
"""
Email Scraper API

FastAPI application that exposes a /scrape endpoint to scrape emails from URLs
using the Scrapy email spider.
"""

import json
import os
import sys
import shutil
import re
import threading
import time
import logging
from pathlib import Path
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Email Scraper API",
    description="API to scrape emails from websites using Scrapy",
    version="1.0.0"
)

class ScrapeRequest(BaseModel):
    url: HttpUrl
    max_depth: Optional[int] = 2
    max_pages_per_domain: Optional[int] = 50
    contact_bias: Optional[bool] = True
    allowed_domains: Optional[str] = None
    allow_patterns: Optional[str] = None

class ScrapeResponse(BaseModel):
    success: bool
    url: str
    emails_found: List[Dict[str, Any]]
    total_unique_emails: int
    unique_emails: List[str]
    pages_scraped: int
    error: Optional[str] = None

def get_project_root():
    """Get the project root directory"""
    return Path(__file__).parent.parent

def get_venv_python():
    """Get the path to the Python executable in the virtual environment"""
    project_root = get_project_root()
    
    # Try multiple possible virtual environment locations
    possible_venv_paths = [
        project_root / "venv",
        project_root / ".venv", 
        project_root / "env",
        Path.cwd() / "venv",
        Path.cwd() / ".venv",
        Path.cwd() / "env"
    ]
    
    for venv_path in possible_venv_paths:
        if os.name == 'nt':  # Windows
            python_exe = venv_path / "Scripts" / "python.exe"
            if not python_exe.exists():
                python_exe = venv_path / "Scripts" / "python"
        else:  # Unix/Linux/Mac
            python_exe = venv_path / "bin" / "python"
            if not python_exe.exists():
                python_exe = venv_path / "bin" / "python3"
        
        if python_exe.exists():
            return str(python_exe)
    
    # If no virtual environment found, try to use the current Python executable
    # but check if it's in a virtual environment
    current_python = sys.executable
    
    # Check if we're already in a virtual environment
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        return current_python
    
    # As a last resort, try to find python/python3 in PATH
    python_cmd = shutil.which('python3') or shutil.which('python')
    if python_cmd:
        return python_cmd
    
    raise FileNotFoundError(
        f"Virtual environment Python not found. Searched paths: {[str(p) for p in possible_venv_paths]}. "
        f"Current Python: {current_python}. Please ensure you have a virtual environment set up."
    )

def get_scrapy_dir():
    """Get the scrapy project directory"""
    project_root = get_project_root()
    
    # Try multiple possible scrapy project locations
    possible_scrapy_paths = [
        project_root / "email_scraper",
        project_root / "scrapy",
        project_root / "scraper",
        Path.cwd() / "email_scraper",
        Path.cwd() / "scrapy",
        Path.cwd() / "scraper"
    ]
    
    for scrapy_path in possible_scrapy_paths:
        if scrapy_path.exists() and (scrapy_path / "scrapy.cfg").exists():
            return scrapy_path
    
    # If no scrapy project found, return the first option (will be created if needed)
    return project_root / "email_scraper"

@app.post("/scrape", response_model=ScrapeResponse)
async def scrape_emails(request: ScrapeRequest):
    """
    Scrape emails from the provided URL using Scrapy spider
    
    Args:
        request: ScrapeRequest containing URL and scraping parameters
        
    Returns:
        ScrapeResponse with scraped emails and metadata
    """
    try:
        # Generate a unique filename for this request
        output_file = f"emails_{uuid.uuid4().hex}.json"
        scrapy_dir = get_scrapy_dir()
        output_path = scrapy_dir / output_file
        
        # Get the virtual environment Python path
        python_exe = get_venv_python()
        
        # Build the scrapy command arguments
        scrapy_args = [
            python_exe, "-m", "scrapy", "crawl", "email_spider",
            "-a", f"start_urls={request.url}",
            "-a", f"max_depth={request.max_depth}",
            "-a", f"max_pages_per_domain={request.max_pages_per_domain}",
            "-a", f"contact_bias={str(request.contact_bias).lower()}",
            "-o", str(output_path)
        ]
        
        # Add optional parameters if provided
        if request.allowed_domains:
            scrapy_args.extend(["-a", f"allowed_domains={request.allowed_domains}"])
        
        if request.allow_patterns:
            scrapy_args.extend(["-a", f"allow={request.allow_patterns}"])
        
        # Add logging settings to reduce noise
        scrapy_args.extend(["-s", "LOG_LEVEL=ERROR"])
        
        # Run the scrapy command
        result = subprocess.run(
            scrapy_args,
            cwd=scrapy_dir,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode != 0:
            error_message = f"Scrapy failed with return code {result.returncode}"
            if result.stderr:
                error_message += f": {result.stderr}"
            
            return ScrapeResponse(
                success=False,
                url=str(request.url),
                emails_found=[],
                total_unique_emails=0,
                unique_emails=[],
                pages_scraped=0,
                error=error_message
            )
        
        # Read the output file
        if not output_path.exists():
            return ScrapeResponse(
                success=False,
                url=str(request.url),
                emails_found=[],
                total_unique_emails=0,
                unique_emails=[],
                pages_scraped=0,
                error="Output file was not created by Scrapy"
            )
        
        # Load and process the scraped data
        with open(output_path, 'r', encoding='utf-8') as f:
            scraped_data = json.load(f)
        
        # Clean up the temporary file
        try:
            output_path.unlink()
        except Exception:
            pass  # Don't fail if cleanup fails
        
        # Extract unique emails from all pages
        all_emails = set()
        pages_scraped = len(scraped_data)
        
        for item in scraped_data:
            if 'emails' in item and isinstance(item['emails'], list):
                all_emails.update(item['emails'])
        
        unique_emails_list = sorted(list(all_emails))
        
        return ScrapeResponse(
            success=True,
            url=str(request.url),
            emails_found=scraped_data,
            total_unique_emails=len(unique_emails_list),
            unique_emails=unique_emails_list,
            pages_scraped=pages_scraped
        )
        
    except subprocess.TimeoutExpired:
        return ScrapeResponse(
            success=False,
            url=str(request.url),
            emails_found=[],
            total_unique_emails=0,
            unique_emails=[],
            pages_scraped=0,
            error="Scraping timeout after 5 minutes"
        )
    except FileNotFoundError as e:
        return ScrapeResponse(
            success=False,
            url=str(request.url),
            emails_found=[],
            total_unique_emails=0,
            unique_emails=[],
            pages_scraped=0,
            error=f"File not found: {str(e)}"
        )
    except Exception as e:
        return ScrapeResponse(
            success=False,
            url=str(request.url),
            emails_found=[],
            total_unique_emails=0,
            unique_emails=[],
            pages_scraped=0,
            error=f"Unexpected error: {str(e)}"
        )

@app.get("/health")
async def health_check():
    """Health check endpoint with detailed system information"""
    try:
        # Check if virtual environment exists
        python_exe = get_venv_python()
        scrapy_dir = get_scrapy_dir()
        
        # Check if we're in a virtual environment
        in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
        
        # Get system information
        system_info = {
            "platform": os.name,
            "system": os.uname() if hasattr(os, 'uname') else "Windows",
            "python_version": sys.version,
            "current_python": sys.executable,
            "working_directory": str(Path.cwd()),
            "project_root": str(get_project_root()),
            "in_virtual_env": in_venv
        }
        
        # Check scrapy availability
        scrapy_available = False
        scrapy_version = None
        try:
            result = subprocess.run([python_exe, "-c", "import scrapy; print(scrapy.__version__)"], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                scrapy_available = True
                scrapy_version = result.stdout.strip()
        except Exception as e:
            scrapy_version = f"Error checking: {str(e)}"
        
        return {
            "status": "healthy" if scrapy_available else "warning",
            "message": "Email Scraper API is running",
            "python_executable": python_exe,
            "scrapy_directory": str(scrapy_dir),
            "scrapy_exists": scrapy_dir.exists(),
            "scrapy_available": scrapy_available,
            "scrapy_version": scrapy_version,
            "system_info": system_info
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"Configuration error: {str(e)}",
            "system_info": {
                "platform": os.name,
                "current_python": sys.executable,
                "working_directory": str(Path.cwd())
            }
        }

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Email Scraper API",
        "version": "1.0.0",
        "description": "API to scrape emails from websites using Scrapy",
        "endpoints": {
            "POST /scrape": "Scrape emails from a URL",
            "GET /health": "Health check",
            "GET /docs": "Interactive API documentation",
            "GET /redoc": "Alternative API documentation"
        },
        "example_usage": {
            "curl": 'curl -X POST "http://localhost:8000/scrape" -H "Content-Type: application/json" -d \'{"url": "https://example.com"}\''
        }
    }

if __name__ == "__main__":
    print("Starting Email Scraper API...")
    print("API will be available at: http://localhost:8000")
    print("API documentation at: http://localhost:8000/docs")
    print("Alternative docs at: http://localhost:8000/redoc")
    
    uvicorn.run(
        "scraper_api:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )