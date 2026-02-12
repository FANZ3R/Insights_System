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
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUERIES_DIR = os.path.join(BASE_DIR, 'queries')
RAW_DATA_DIR = os.path.join(BASE_DIR, 'data', 'raw')
PROCESSED_DATA_DIR = os.path.join(BASE_DIR, 'data', 'processed')

# Query Files - NEW: Single combined SQL files
QUERY_FILES = {
    'buyer': 'buyer_queries.sql',
    'seller': 'seller_queries.sql'
}



# Query Parameters - Default Values
DEFAULT_PARAMS = {
    'buyer': {
        'start_date': (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d'),
        'end_date': datetime.now().strftime('%Y-%m-%d'),
        'top_n': 10
    },
    'seller': {
        'start_date': (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d'),
        'end_date': datetime.now().strftime('%Y-%m-%d'),
        'top_n': 20,
        'time_resolution': 'day'
    }
}

# Query Definitions
QUERY_DEFINITIONS = {
    'buyer': {
        'overview_metrics': {
            'file': 'overview_metrics.sql',
            'params': ['start_date', 'end_date'],
            'description': 'Period-over-period comparison of buyer metrics'
        },
        'top_products': {
            'file': 'top_products.sql',
            'params': ['start_date', 'end_date', 'top_n'],
            'description': 'Top products by purchase amount'
        },
        'top_suppliers': {
            'file': 'top_suppliers.sql',
            'params': ['start_date', 'end_date', 'top_n'],
            'description': 'Top suppliers by purchase amount'
        },
        'top_categories': {
            'file': 'top_categories.sql',
            'params': ['start_date', 'end_date', 'top_n'],
            'description': 'Top categories by purchase amount'
        }
    },
    'seller': {
        'performance_overview': {
            'file': 'performance_overview.sql',
            'params': ['start_date', 'end_date'],
            'description': 'Sales, customers, and repeat purchase metrics'
        },
        'monthly_trends': {
            'file': 'monthly_trends.sql',
            'params': ['start_date', 'end_date'],
            'description': 'Month-over-month sales trends'
        },
        'quarterly_trends': {
            'file': 'quarterly_trends.sql',
            'params': ['start_date', 'end_date'],
            'description': 'Quarter-over-quarter sales trends'
        },
        'product_line_breakdown': {
            'file': 'product_line_breakdown.sql',
            'params': ['start_date', 'end_date'],
            'description': 'Revenue contribution by product category'
        },
        'sales_time_series': {
            'file': 'sales_time_series.sql',
            'params': ['start_date', 'end_date', 'time_resolution'],
            'description': 'Sales by configurable time period (day/week/month)'
        },
        'top_selling_products': {
            'file': 'top_selling_products.sql',
            'params': ['start_date', 'end_date', 'top_n'],
            'description': 'Top selling products by revenue'
        },
        'regional_distribution': {
            'file': 'regional_distribution.sql',
            'params': ['start_date', 'end_date'],
            'description': 'Sales distribution by geographic region'
        },
        'order_analysis': {
            'file': 'order_analysis.sql',
            'params': ['start_date', 'end_date'],
            'description': 'Order value vs quantity analysis'
        }
    }
}

# Insights Generation Settings
MAX_INSIGHTS_PER_ENTITY = 5
INSIGHT_PRIORITY_LEVELS = ['high', 'medium', 'low']