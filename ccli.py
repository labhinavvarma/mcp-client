from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass
import json
import logging
import statistics
import mcp.types as types
import requests  
import os
from typing import Optional
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from mcp.server.fastmcp import Context, FastMCP

logger = logging.getLogger(__name__)

# Create a named server
NWS_API_BASE = "https://api.weather.gov"
app = FastAPI(title="DataFlyWheel App")
mcp = FastMCP("DataFlyWheel App", app=app)

# --- MCP JSON Analyzer Tool ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "MCP Server is running"}

@app.post("/api/mcp")
async def mcp_api(request: Request):
    try:
        body_bytes = await request.body()
        logger.info(f"Received request: {body_bytes[:200]}")
        try:
            data = json.loads(body_bytes)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            return JSONResponse(status_code=400, content={"status": "error", "error": f"Invalid JSON: {str(e)}"})

        if "data" not in data or "operation" not in data:
            return JSONResponse(status_code=400, content={"status": "error", "error": "Missing 'data' or 'operation' field"})

        input_data = data["data"]
        operation = data["operation"].lower()
        valid_operations = ["sum", "mean", "median", "min", "max"]
        if operation not in valid_operations:
            return JSONResponse(status_code=400, content={"status": "error", "error": f"Invalid operation. Use one of: {', '.join(valid_operations)}"})

        result = None
        try:
            if isinstance(input_data, list):
                numbers = [float(n) for n in input_data]
                if not numbers:
                    return JSONResponse(status_code=400, content={"status": "error", "error": "Empty data list"})
                result = {
                    "sum": sum(numbers),
                    "mean": statistics.mean(numbers),
                    "median": statistics.median(numbers),
                    "min": min(numbers),
                    "max": max(numbers)
                }[operation]
            elif isinstance(input_data, dict):
                results_dict = {}
                for key, values in input_data.items():
                    if not isinstance(values, list):
                        return JSONResponse(status_code=400, content={"status": "error", "error": f"Value for key '{key}' must be a list"})
                    numbers = [float(n) for n in values]
                    if not numbers:
                        return JSONResponse(status_code=400, content={"status": "error", "error": f"Empty data list for key '{key}'"})
                    results_dict[key] = {
                        "sum": sum(numbers),
                        "mean": statistics.mean(numbers),
                        "median": statistics.median(numbers),
                        "min": min(numbers),
                        "max": max(numbers)
                    }[operation]
                result = results_dict
            else:
                return JSONResponse(status_code=400, content={"status": "error", "error": f"Data must be a list or dictionary, got {type(input_data).__name__}"})
        except (ValueError, TypeError) as e:
            logger.error(f"Data processing error: {e}")
            return JSONResponse(status_code=400, content={"status": "error", "error": f"Data processing error: {str(e)}"})

        return {"status": "success", "result": result}

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return JSONResponse(status_code=500, content={"status": "error", "error": "Internal server error"})

# --- Categorized Prompt Library ---
PROMPT_LIBRARY = {
    "hedis": [
        {"name": "Explain BCS Measure", "prompt": "Explain the purpose of the BCS HEDIS measure."},
        {"name": "List 2024 HEDIS Measures", "prompt": "List all HEDIS measures for the year 2024."},
        {"name": "Age Criteria for CBP", "prompt": "What is the age criteria for the CBP measure?"}
    ],
    "contract": [
        {"name": "Summarize Contract H123", "prompt": "Summarize contract ID H123 for 2023."},
        {"name": "Compare Contracts H456 & H789", "prompt": "Compare contracts H456 and H789 on key metrics."}
    ]
}

@mcp.tool(name="ready-prompts", description="Return ready-made prompts by application category")
def get_ready_prompts(category: Optional[str] = None) -> dict:
    if category:
        category = category.lower()
        if category not in PROMPT_LIBRARY:
            return {"error": f"No prompts found for category '{category}'"}
        return {"category": category, "prompts": PROMPT_LIBRARY[category]}
    else:
        return {"prompts": PROMPT_LIBRARY}

@mcp.tool(name="calculator", description="""
    Evaluates a basic arithmetic expression.
    Supports: +, -, *, /, parentheses, decimals.
""")
def calculate(expression: str) -> str:
    try:
        allowed_chars = "0123456789+-*/(). "
        if any(char not in allowed_chars for char in expression):
            return " Invalid characters in expression."
        result = eval(expression)
        return f" Result: {result}"
    except Exception as e:
        return f" Error: {str(e)}"

@mcp.tool(name="json-analyzer", description="Analyze JSON numeric data by performing operations like sum, mean, median, min, max.")
def analyze_json(data: dict, operation: str) -> dict:
    try:
        valid_operations = ["sum", "mean", "median", "min", "max"]
        if operation not in valid_operations:
            return {"error": f"Invalid operation. Must be one of: {', '.join(valid_operations)}"}

        result = {}
        for key, values in data.items():
            if not isinstance(values, list):
                return {"error": f"'{key}' must be a list of numbers"}
            numbers = [float(n) for n in values]
            if not numbers:
                return {"error": f"No numbers provided for '{key}'"}
            result[key] = {
                "sum": sum(numbers),
                "mean": statistics.mean(numbers),
                "median": statistics.median(numbers),
                "min": min(numbers),
                "max": max(numbers)
            }[operation]
        return {"status": "success", "result": result}
    except Exception as e:
        return {"error": f"Error analyzing data: {str(e)}"}

@mcp.tool()
def get_weather(latitude: float, longitude: float) -> str:
    try:
        headers = {
            "User-Agent": "MCP Weather Client (your-email@example.com)",
            "Accept": "application/geo+json"
        }
        points_url = f"{NWS_API_BASE}/points/{latitude},{longitude}"
        points_response = requests.get(points_url, headers=headers)
        points_response.raise_for_status()
        points_data = points_response.json()
        forecast_url = points_data['properties']['forecast']
        location_name = f"{points_data['properties']['relativeLocation']['properties']['city']}, {points_data['properties']['relativeLocation']['properties']['state']}"
        forecast_response = requests.get(forecast_url, headers=headers)
        forecast_response.raise_for_status()
        forecast_data = forecast_response.json()
        current_period = forecast_data['properties']['periods'][0]
        return f" Weather for {location_name}: {current_period['detailedForecast']}"
    except Exception as e:
        return f" Error fetching weather data: {str(e)}"

@mcp.prompt(name="hedis-prompt", description="Prompt to interact with hedis")
async def hedis_template_prompt() -> str:
    return """You are expert in HEDIS system... {query}"""

@mcp.prompt(name="calculator-prompt", description="Prompt to perform calculations")
async def calculator_template_prompt() -> str:
    return """You are expert in performing arithmetic operations. Given an expression, compute the result and verify using calculator tool."""

@mcp.prompt(name="weather-prompt", description="Prompt to report weather")
async def weather_template_prompt() -> str:
    return """You are expert in reporting weather. Use coordinates and fetch current forecast using weather tool."""

@mcp.prompt(name="json-analyzer-prompt", description="Prompt to analyze JSON numeric data")
async def json_analyzer_prompt() -> str:
    return """You are a data analyst. Perform numeric analysis over JSON data structures using the json-analyzer tool. Supported operations: sum, mean, median, min, max."""

if __name__ == "__main__":
    import uvicorn
    print("Starting MCP Server on http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
