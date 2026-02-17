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


# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

# PostgreSQL (production - source of truth)
DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'database': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'port': os.getenv('DB_PORT')
}

# ============================================================================
# DUCKDB ANALYTICS DATABASE
# ============================================================================
ANALYTICS_DIR = os.path.join(str(BASE_DIR), 'data', 'analytics')
ANALYTICS_DB_PATH = os.path.join(ANALYTICS_DIR, 'vipani_analytics.db')

os.makedirs(ANALYTICS_DIR, exist_ok=True)

# Entity ID columns in your PostgreSQL/DuckDB table
ENTITY_ID_COLUMNS = {
    'buyer': 'buyer_org_id',   # ← Change if your column name differs
    'seller': 'vendor_id'      # ← Change if your column name differs
}

# Baseline period for historical comparison (days)
BASELINE_DAYS = 365

# Sync configuration (PostgreSQL → DuckDB)
SYNC_CONFIG = {
    'batch_size': 10000,
    'log_path': os.path.join(str(BASE_DIR), 'cron', 'cron_logs', 'sync.log'),
    'incremental_column': 'updated_at'  # ← Column used to detect new rows
}

# ============================================================================
# LLM CONFIGURATION
# ============================================================================

OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
OPENROUTER_BASE_URL = 'https://openrouter.ai/api/v1'
DEFAULT_MODEL = 'openai/gpt-4o-mini'

LLM_CONFIG = {
    'temperature': 0.3,
    'max_tokens': 1500,
    'response_format': 'json'
}

# ============================================================================
# DIRECTORY PATHS
# ============================================================================

QUERIES_DIR = os.path.join(str(BASE_DIR), 'queries')
DASHBOARD_QUERIES_DIR = os.path.join(QUERIES_DIR, 'dashboard_specific')

DATA_DIR = os.path.join(str(BASE_DIR), 'data')
DASHBOARD_DATA_DIR = os.path.join(DATA_DIR, 'dashboard_data')
DASHBOARD_RAW_DIR = os.path.join(DASHBOARD_DATA_DIR, 'raw')
DASHBOARD_PROCESSED_DIR = os.path.join(DASHBOARD_DATA_DIR, 'processed')

# ============================================================================
# QUERY FILES (Dashboard only - total queries replaced by DuckDB)
# ============================================================================

DASHBOARD_QUERY_FILES = {
    'buyer': 'buyer_dashboard_queries.sql',
    'seller': 'seller_dashboard_queries.sql'
}



# ADD BACK - needed for sync_to_duckdb.py
TOTAL_QUERIES_DIR = os.path.join(QUERIES_DIR, 'total_queries')

TOTAL_QUERY_FILES = {
    'buyer': 'buyer_total_queries.sql',
    'seller': 'seller_total_queries.sql'
}

TOTAL_DATA_PARAMS = {
    'buyer': {
        'start_date': (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d'),
        'end_date': datetime.now().strftime('%Y-%m-%d'),
        'top_n': 20
    },
    'seller': {
        'start_date': (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d'),
        'end_date': datetime.now().strftime('%Y-%m-%d'),
        'top_n': 30,
        'time_resolution': 'month'
    }
}









# ============================================================================
# QUERY PARAMETERS
# ============================================================================

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
# INSIGHTS GENERATION SETTINGS
# ============================================================================

INSIGHTS_CONFIG = {
    'buyer': {
        'min_insights': 5,
        'max_insights': 7,
        'target_insights': 6
    },
    'seller': {
        'min_insights': 5,
        'max_insights': 7,
        'target_insights': 6
    }
}

INSIGHT_PRIORITY_LEVELS = ['high', 'medium', 'low']
COMPARISON_TYPES = ['self', 'benchmark', 'both']

PRIORITY_THRESHOLDS = {
    'high': {
        'self_deviation': 30,
        'benchmark_deviation': 50
    },
    'medium': {
        'self_deviation': 15,
        'benchmark_deviation': 25
    }
}

# ============================================================================
# INSIGHT VALIDATION
# ============================================================================

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






# Actual column names from your SQL queries
SPEND_COLUMNS = {
    'buyer': 'current_period_purchases',
    'seller': 'total_sales'
}

COUNTERPARTY_COLUMNS = {
    'buyer': 'suppliers_current',
    'seller': 'total_buyers'
}



# ============================================================================
# QUERY REGISTRY - Add new queries here, nowhere else!
# ============================================================================

QUERY_REGISTRY = {
    'buyer': {
        # overview_query: which query has the entity ID and main metrics
        'overview_query': 'overview_metrics',
        'entity_id_col': 'buyer_org_id',
        'spend_col': 'current_period_purchases',
        'counterparty_col': 'suppliers_current',
        
        # All queries and what they contain
        # Add new queries here when you create them!
        'queries': {
            'overview_metrics': {
                'description': 'Period-over-period buyer metrics',
                'entity_id_col': 'buyer_org_id',
                'type': 'overview'
            },
            'top_products': {
                'description': 'Top products by spend',
                'entity_id_col': 'buyer_org_id',
                'type': 'ranking'
            },
            'top_suppliers': {
                'description': 'Top suppliers by spend',
                'entity_id_col': 'buyer_org_id',
                'type': 'ranking'
            },
            'top_categories': {
                'description': 'Top categories by spend',
                'entity_id_col': 'buyer_org_id',
                'type': 'ranking'
            },
            # When you add new queries to SQL file, just add here:
            # 'monthly_trends': {
            #     'description': 'Monthly spend trends',
            #     'entity_id_col': 'buyer_org_id',
            #     'type': 'time_series'
            # },
        }
    },
    
    'seller': {
        'overview_query': 'performance_overview',
        'entity_id_col': 'vendor_id',
        'spend_col': 'total_sales',
        'counterparty_col': 'total_buyers',
        
        'queries': {
            'performance_overview': {
                'description': 'Sales and customer metrics',
                'entity_id_col': 'vendor_id',
                'type': 'overview'
            },
            'monthly_trends': {
                'description': 'Monthly sales trends',
                'entity_id_col': 'vendor_id',
                'type': 'time_series'
            },
            'quarterly_trends': {
                'description': 'Quarterly sales trends',
                'entity_id_col': 'vendor_id',
                'type': 'time_series'
            },
            'product_line_breakdown': {
                'description': 'Revenue by product line',
                'entity_id_col': 'vendor_id',
                'type': 'breakdown'
            },
            'sales_time_series': {
                'description': 'Daily/weekly sales series',
                'entity_id_col': 'vendor_id',
                'type': 'time_series'
            },
            'top_selling_products': {
                'description': 'Top products by revenue',
                'entity_id_col': 'vendor_id',
                'type': 'ranking'
            },
            'regional_distribution': {
                'description': 'Sales by region',
                'entity_id_col': 'vendor_id',
                'type': 'distribution'
            },
            'order_analysis': {
                'description': 'Order patterns and sizes',
                'entity_id_col': 'vendor_id',
                'type': 'analysis'
            },
            # Add new seller queries here when you create them!
        }
    }
}