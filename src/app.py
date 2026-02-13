"""
FastAPI application for on-demand insights generation
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
from pathlib import Path
import json
import os

import config
from dashboard_executor import DashboardExecutor
from insights_generator import BenchmarkingInsightsGenerator

app = FastAPI(
    title="Vendor/Buyer Insights API",
    description="Generate AI-powered procurement insights for buyers and sellers",
    version="1.0.0"
)

# Initialize components
executor = DashboardExecutor()
generator = BenchmarkingInsightsGenerator()


@app.get("/")
def root():
    """API health check"""
    return {
        "status": "healthy",
        "service": "Vendor Insights API",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/insights/{entity_type}/{entity_id}")
def generate_insights(
    entity_type: str,
    entity_id: int,
    start_date: str = Query(None, description="Start date (YYYY-MM-DD), defaults to 90 days ago"),
    end_date: str = Query(None, description="End date (YYYY-MM-DD), defaults to today"),
    top_n: int = Query(None, description="Number of top items in rankings")
):
    """
    Generate insights for a specific buyer or seller
    
    Args:
        entity_type: 'buyer' or 'seller'
        entity_id: The entity ID (e.g., 5098)
        start_date: Dashboard period start (optional)
        end_date: Dashboard period end (optional)
        top_n: Number of top items (optional)
    
    Returns:
        JSON with insights
    
    Example:
        GET /insights/buyer/5098
        GET /insights/seller/7?start_date=2025-01-01&end_date=2026-02-13
    """
    
    # Validate entity_type
    if entity_type not in ['buyer', 'seller']:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid entity_type '{entity_type}'. Must be 'buyer' or 'seller'."
        )
    
    # Validate total data exists
    total_data_file = Path(config.TOTAL_DATA_DIR) / config.TOTAL_DATA_FILES[entity_type]
    if not total_data_file.exists():
        raise HTTPException(
            status_code=503,
            detail=f"Total data not found for {entity_type}s. Please run populate_total_data.py first."
        )
    
    # Build parameters
    params = config.DEFAULT_PARAMS[entity_type].copy()
    
    if start_date:
        params['start_date'] = start_date
    if end_date:
        params['end_date'] = end_date
    if top_n:
        params['top_n'] = top_n
    
    try:
        # Step 1: Execute dashboard queries for this entity
        print(f"\n{'='*60}")
        print(f"API Request: {entity_type.upper()} {entity_id}")
        print(f"Period: {params['start_date']} to {params['end_date']}")
        print(f"{'='*60}\n")
        
        dashboard_file = executor.process_entity(entity_type, entity_id, params)
        
        # Step 2: Generate insights
        insights_file = generator.generate_insights(dashboard_file)
        
        # Step 3: Load and return insights
        with open(insights_file, 'r') as f:
            insights_data = json.load(f)
        
        # Add API metadata
        response = {
            "status": "success",
            "generated_at": datetime.now().isoformat(),
            "request": {
                "entity_type": entity_type,
                "entity_id": entity_id,
                "dashboard_period": params
            },
            "insights": insights_data
        }
        
        return JSONResponse(content=response)
    
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=f"Entity {entity_type} {entity_id} not found or has no data in the specified period."
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating insights: {str(e)}"
        )


@app.get("/insights/batch/{entity_type}")
def generate_insights_batch(
    entity_type: str,
    entity_ids: str = Query(..., description="Comma-separated entity IDs (e.g., '5098,5100,5105')"),
    start_date: str = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(None, description="End date (YYYY-MM-DD)"),
    top_n: int = Query(None, description="Number of top items")
):
    """
    Generate insights for multiple entities
    
    Args:
        entity_type: 'buyer' or 'seller'
        entity_ids: Comma-separated IDs (e.g., "5098,5100,5105")
        start_date: Dashboard period start (optional)
        end_date: Dashboard period end (optional)
        top_n: Number of top items (optional)
    
    Returns:
        JSON with insights for all requested entities
    
    Example:
        GET /insights/batch/buyer?entity_ids=5098,5100,5105
    """
    
    # Validate entity_type
    if entity_type not in ['buyer', 'seller']:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid entity_type '{entity_type}'. Must be 'buyer' or 'seller'."
        )
    
    # Parse entity IDs
    try:
        ids = [int(id.strip()) for id in entity_ids.split(',')]
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid entity_ids format. Use comma-separated integers (e.g., '5098,5100')."
        )
    
    if len(ids) > 50:
        raise HTTPException(
            status_code=400,
            detail="Maximum 50 entities per batch request."
        )
    
    # Build parameters
    params = config.DEFAULT_PARAMS[entity_type].copy()
    
    if start_date:
        params['start_date'] = start_date
    if end_date:
        params['end_date'] = end_date
    if top_n:
        params['top_n'] = top_n
    
    results = []
    errors = []
    
    for entity_id in ids:
        try:
            dashboard_file = executor.process_entity(entity_type, entity_id, params)
            insights_file = generator.generate_insights(dashboard_file)
            
            with open(insights_file, 'r') as f:
                insights_data = json.load(f)
            
            results.append({
                "entity_id": entity_id,
                "status": "success",
                "insights": insights_data
            })
        
        except Exception as e:
            errors.append({
                "entity_id": entity_id,
                "status": "error",
                "error": str(e)
            })
    
    return JSONResponse(content={
        "status": "completed",
        "generated_at": datetime.now().isoformat(),
        "request": {
            "entity_type": entity_type,
            "entity_ids": ids,
            "dashboard_period": params
        },
        "results": results,
        "errors": errors,
        "summary": {
            "total": len(ids),
            "successful": len(results),
            "failed": len(errors)
        }
    })


@app.get("/status/total-data")
def check_total_data_status():
    """
    Check if total data files exist and show their metadata
    
    Returns:
        Status of buyer and seller total data files
    """
    
    status = {}
    
    for entity_type in ['buyer', 'seller']:
        filepath = Path(config.TOTAL_DATA_DIR) / config.TOTAL_DATA_FILES[entity_type]
        
        if filepath.exists():
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            status[entity_type] = {
                "exists": True,
                "filepath": str(filepath),
                "generated_at": data.get('generated_at'),
                "baseline_period": data.get('baseline_period'),
                "total_entities": data.get('total_entities'),
                "queries_executed": data.get('queries_executed'),
                "file_size_mb": round(filepath.stat().st_size / (1024 * 1024), 2)
            }
        else:
            status[entity_type] = {
                "exists": False,
                "filepath": str(filepath),
                "error": "File not found. Run populate_total_data.py first."
            }
    
    return status


@app.get("/entities/{entity_type}")
def list_entities(entity_type: str):
    """
    List all available entities of a given type from total_data
    
    Args:
        entity_type: 'buyer' or 'seller'
    
    Returns:
        List of entity IDs available for insights generation
    """
    
    if entity_type not in ['buyer', 'seller']:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid entity_type '{entity_type}'. Must be 'buyer' or 'seller'."
        )
    
    filepath = Path(config.TOTAL_DATA_DIR) / config.TOTAL_DATA_FILES[entity_type]
    
    if not filepath.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Total data not found for {entity_type}s."
        )
    
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    # Extract entity IDs
    entity_ids = [int(entity_id) for entity_id in data['entities'].keys()]
    entity_ids.sort()
    
    return {
        "entity_type": entity_type,
        "total_count": len(entity_ids),
        "entity_ids": entity_ids,
        "baseline_period": data.get('baseline_period')
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)