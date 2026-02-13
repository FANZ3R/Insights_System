"""
Configuration settings for insights generation system
"""

import os
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / '.env'

if env_path.exists():
    load_dotenv(dotenv_path=env_path)
    print(f" Loaded .env from: {env_path}")
else:
    print(f" Warning: .env file not found at {env_path}")


# Database Configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'database': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'port': os.getenv('DB_PORT')
}

# OpenRouter API Configuration
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
OPENROUTER_BASE_URL = 'https://openrouter.ai/api/v1'
DEFAULT_MODEL = 'openai/gpt-oss-120b'  # ← CORRECTED

# Directory Paths 
QUERIES_DIR = os.path.join(BASE_DIR, 'queries')

# Query subdirectories
TOTAL_QUERIES_DIR = os.path.join(QUERIES_DIR, 'total_queries')
DASHBOARD_QUERIES_DIR = os.path.join(QUERIES_DIR, 'dashboard_specific')

# Data directories
DATA_DIR = os.path.join(BASE_DIR, 'data')
TOTAL_DATA_DIR = os.path.join(DATA_DIR, 'total_data')
DASHBOARD_DATA_DIR = os.path.join(DATA_DIR, 'dashboard_data')
DASHBOARD_RAW_DIR = os.path.join(DASHBOARD_DATA_DIR, 'raw')
DASHBOARD_PROCESSED_DIR = os.path.join(DASHBOARD_DATA_DIR, 'processed')

# Query Files
TOTAL_QUERY_FILES = {
    'buyer': 'buyer_total_queries.sql',
    'seller': 'seller_total_queries.sql'
}

DASHBOARD_QUERY_FILES = {
    'buyer': 'buyer_dashboard_queries.sql',
    'seller': 'seller_dashboard_queries.sql'
}

# Total Data Output Files
TOTAL_DATA_FILES = {
    'buyer': 'buyers_total.json',
    'seller': 'sellers_total.json'
}

# Query Parameters - Default Values
DEFAULT_PARAMS = {
    'buyer': {
        'start_date': (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d'),
        'end_date': datetime.now().strftime('%Y-%m-%d'),
        'top_n': 10
    },
    'seller': {
        'start_date': (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d'),
        'end_date': datetime.now().strftime('%Y-%m-%d'),
        'top_n': 20
    }
}


# ============================================================================
# TOTAL DATA PARAMETERS (for baseline/historical data)
# ============================================================================

TOTAL_DATA_PARAMS = {
    'buyer': {
        'start_date': (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d'),
        'end_date': datetime.now().strftime('%Y-%m-%d'),
        'top_n': 20  # More items for comprehensive baseline
    },
    'seller': {
        'start_date': (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d'),
        'end_date': datetime.now().strftime('%Y-%m-%d'),
        'top_n': 30,  # More items for comprehensive baseline
        'time_resolution': 'month'
    }
}



# ============================================================================
# INSIGHTS GENERATION SETTINGS
# ============================================================================

# Insights quantity control
INSIGHTS_CONFIG = {
    'buyer': {
        'min_insights': 5,
        'max_insights': 7,
        'target_insights': 6  # What we ask LLM to aim for
    },
    'seller': {
        'min_insights': 5,
        'max_insights': 7,
        'target_insights': 6
    }
}

# Valid priority levels
INSIGHT_PRIORITY_LEVELS = ['high', 'medium', 'low']

# Valid comparison types (for new benchmarking system)
COMPARISON_TYPES = ['self', 'benchmark', 'both']

# Deviation thresholds for priority assignment (used in prompts)
PRIORITY_THRESHOLDS = {
    'high': {
        'self_deviation': 30,      # % change from own historical
        'benchmark_deviation': 50   # % difference from platform average
    },
    'medium': {
        'self_deviation': 15,
        'benchmark_deviation': 25
    }
    # Low priority: everything below medium
}

# LLM parameters
LLM_CONFIG = {
    'temperature': 0.3,
    'max_tokens': 2000,
    'response_format': 'json'  # Future: OpenAI structured outputs
}



AGGREGATE_PERCENTILES = [25, 50, 75, 90]

# Insight validation rules
INSIGHT_VALIDATION = {
    'require_title': True,
    'require_observation': True,
    'require_recommendation': True,
    'require_priority': True,
    'require_comparison_type': True,
    'min_title_length': 10,
    'min_observation_length': 20,
    'min_recommendation_length': 20,
    'max_title_length': 100,
    'max_metrics_per_insight': 5
}