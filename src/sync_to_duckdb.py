"""
sync_to_duckdb.py
Runs your existing total_queries against PostgreSQL
and stores results in DuckDB
Replaces populate_total_data.py
"""

import duckdb
import psycopg2
import os
import sys
import json
import logging
from datetime import datetime
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import config
from query_parser import QueryParser

os.makedirs(os.path.dirname(config.SYNC_CONFIG['log_path']), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.SYNC_CONFIG['log_path']),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DuckDBSync:
    def __init__(self):
        os.makedirs(config.ANALYTICS_DIR, exist_ok=True)
        self.duck_path = config.ANALYTICS_DB_PATH
        self.parser = QueryParser()
    
    # ============================================================
    # CONNECTIONS
    # ============================================================
    
    def get_duck_conn(self):
        return duckdb.connect(self.duck_path)
    
    def get_pg_conn(self):
        return psycopg2.connect(**config.DB_CONFIG)
    
    # ============================================================
    # SCHEMA - stores query results just like SQLite did
    # ============================================================
    
    def initialize_schema(self):
        """Create DuckDB tables to store query results"""
        conn = self.get_duck_conn()
        
        # Same concept as SQLite entities table
        # but now in DuckDB
        conn.execute("""
        CREATE TABLE IF NOT EXISTS entities (
            entity_id       INTEGER,
            entity_type     VARCHAR,
            queries_data    VARCHAR,    -- JSON string of all query results
            created_at      VARCHAR,
            updated_at      VARCHAR,
            PRIMARY KEY (entity_id, entity_type)
        )
        """)
        
        # Aggregates table (replaces buyers_aggregates.json)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS aggregates (
            entity_type     VARCHAR PRIMARY KEY,
            aggregates_data VARCHAR,    -- JSON string of aggregates
            calculated_at   VARCHAR
        )
        """)
        
        # Sync log
        conn.execute("""
        CREATE TABLE IF NOT EXISTS sync_log (
            synced_at       VARCHAR,
            entity_type     VARCHAR,
            entities_count  INTEGER,
            duration_s      DOUBLE,
            status          VARCHAR,
            error_message   VARCHAR
        )
        """)
        
        conn.close()
        logger.info("✓ DuckDB schema initialized")
    
    # ============================================================
    # EXECUTE QUERIES (same as populate_total_data.py did)
    # ============================================================
    
    def execute_pg_query(self, query, params):
        """Execute query against PostgreSQL - same as before"""
        conn = self.get_pg_conn()
        cursor = conn.cursor()
        
        try:
            cursor.execute(query, params)
            results = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            
            results_dicts = []
            for row in results:
                row_dict = dict(zip(columns, row))
                for key, value in row_dict.items():
                    if isinstance(value, Decimal):
                        row_dict[key] = float(value)
                    elif hasattr(value, 'isoformat'):
                        row_dict[key] = value.isoformat()
                results_dicts.append(row_dict) or results_dicts
            
            return results_dicts
        
        finally:
            cursor.close()
            conn.close()
    
    def load_and_execute_queries(self, entity_type, params):
        """
        Load SQL file and execute all queries against PostgreSQL
        Same logic as populate_total_data.py
        """
        # Load the same SQL files you already have!
        query_file = config.TOTAL_QUERY_FILES[entity_type]
        filepath = os.path.join(
            config.TOTAL_QUERIES_DIR,
            entity_type,
            query_file
        )
        
        logger.info(f"Loading queries from: {filepath}")
        queries = self.parser.parse_file(filepath)
        logger.info(f"Found {len(queries)} queries: {[q['name'] for q in queries]}")
        
        all_results = {}
        
        for query in queries:
            name = query['name']
            sql = query['query']
            
            logger.info(f"Executing {name}...")
            try:
                results = self.execute_pg_query(sql, params)
                all_results[name] = results
                logger.info(f"  ✓ {len(results)} rows")
            except Exception as e:
                logger.error(f"  ✗ Error: {e}")
                all_results[name] = []
        
        return all_results
    
    # ============================================================
    # ORGANIZE BY ENTITY (same as populate_total_data.py did)
    # ============================================================
    
    def organize_by_entity(self, entity_type, all_results):
        """Dynamically handles any number of queries via registry"""
        
        registry = config.QUERY_REGISTRY[entity_type]
        overview_key = registry['overview_query']       # from config, not hardcoded
        id_col = registry['entity_id_col']              # from config, not hardcoded
        
        overview_data = all_results.get(overview_key, [])
        
        entity_rows = [row for row in overview_data if row.get(id_col) is not None]
        summary_rows = [row for row in overview_data if row.get(id_col) is None]
        
        if summary_rows:
            logger.info(f"Found {len(summary_rows)} summary/total row(s)")
        
        entity_ids = [row[id_col] for row in entity_rows]
        logger.info(f"Found {len(entity_ids)} {entity_type} entities")
        
        # This loop handles ANY number of queries automatically!
        entities = {}
        for entity_id in entity_ids:
            entity_data = {}
            for query_name, results in all_results.items():
                entity_data[query_name] = [
                    row for row in results
                    if row.get(id_col) == entity_id
                ]
            entities[entity_id] = entity_data
        
        self._summary_rows = {
            entity_type: {
                'overview': summary_rows,
                'id_col': id_col
            }
        }
        
        return entities

    
    
    
    def save_entities_to_duckdb(self, entity_type, entities):
        import numpy as np
        
        # Read from config registry - not hardcoded!
        registry = config.QUERY_REGISTRY[entity_type]
        overview_key = registry['overview_query']
        spend_key = registry['spend_col']
        counterparty_key = registry['counterparty_col']
            
        """Save all entity data to DuckDB"""
        conn = self.get_duck_conn()
        now = datetime.now().isoformat()
        
        logger.info(f"Saving {len(entities)} {entity_type} entities to DuckDB...")
        
        # Delete existing data for this entity type
        conn.execute(
            "DELETE FROM entities WHERE entity_type = ?",
            [entity_type]
        )
        
        # Insert all entities
        for entity_id, queries_data in entities.items():
            conn.execute("""
            INSERT INTO entities (entity_id, entity_type, queries_data, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """, [
                entity_id,
                entity_type,
                json.dumps(queries_data),
                now,
                now
            ])
        
        conn.close()
        logger.info(f"✓ Saved {len(entities)} entities to DuckDB")
        


    def save_aggregates_to_duckdb(self, entity_type, entities):
        """
        Calculate aggregates - uses summary rows if available,
        otherwise calculates from entity rows
        """
        import numpy as np
        
        conn = self.get_duck_conn()
        now = datetime.now().isoformat()
        
        id_col = config.ENTITY_ID_COLUMNS[entity_type]
        overview_key = 'overview_metrics' if entity_type == 'buyer' else 'performance_overview'
        spend_key = 'current_period_purchases' if entity_type == 'buyer' else 'total_sales'
        counterparty_key = 'suppliers_current' if entity_type == 'buyer' else 'total_buyers'
        
        # ─────────────────────────────────────────────────
        # Check if we have summary rows (NULL entity rows)
        # These are MORE accurate for platform aggregates!
        # ─────────────────────────────────────────────────
        summary_data = getattr(self, '_summary_rows', {}).get(entity_type, {})
        summary_rows = summary_data.get('overview', [])
        
        if summary_rows:
            # Use the platform summary row directly
            logger.info(f"Using platform summary row for aggregates (more accurate!)")
            
            platform_total = summary_rows[0]  # The NULL entity_id row
            
            # This row has platform-wide totals
            # Calculate per-entity averages from entity data too
            spend_values = []
            counterparty_values = []
            
            for entity_id, data in entities.items():
                overview = data.get(overview_key, [])
                if overview:
                    spend = overview[0].get(spend_key, 0) or 0
                    counterparties = overview[0].get(counterparty_key, 0) or 0
                    spend_values.append(float(spend))
                    counterparty_values.append(float(counterparties))
            
            if spend_values:
                spend_arr = np.array(spend_values)
                counterparty_arr = np.array(counterparty_values)
                
                aggregates = {
                    'total_count': len(spend_values),
                    
                    # From entity rows (per-entity statistics)
                    'avg_period_spend': float(np.mean(spend_arr)),
                    'median_period_spend': float(np.median(spend_arr)),
                    'std_period_spend': float(np.std(spend_arr)),
                    'avg_counterparties': float(np.mean(counterparty_arr)),
                    'median_counterparties': float(np.median(counterparty_arr)),
                    'std_counterparties': float(np.std(counterparty_arr)),
                    
                    # Platform totals from summary row (valuable!)
                    'platform_total_spend': float(platform_total.get(spend_key, 0) or 0),
                    'platform_total_orders': float(platform_total.get('total_orders', 0) or 0),
                    'platform_total_counterparties': float(platform_total.get(counterparty_key, 0) or 0),
                    
                    # Percentiles
                    'percentiles': {
                        'p25': float(np.percentile(spend_arr, 25)),
                        'p50': float(np.percentile(spend_arr, 50)),
                        'p75': float(np.percentile(spend_arr, 75)),
                        'p90': float(np.percentile(spend_arr, 90))
                    }
                }
                
                logger.info(f"Platform total spend: {aggregates['platform_total_spend']:,.0f}")
        
        else:
            # No summary row - calculate everything from entity rows
            logger.info(f"No summary row found - calculating aggregates from entity rows")
            
            spend_values = []
            counterparty_values = []
            
            for entity_id, data in entities.items():
                overview = data.get(overview_key, [])
                if overview:
                    spend = overview[0].get(spend_key, 0) or 0
                    counterparties = overview[0].get(counterparty_key, 0) or 0
                    spend_values.append(float(spend))
                    counterparty_values.append(float(counterparties))
            
            if not spend_values:
                logger.warning("No data for aggregates")
                return
            
            spend_arr = np.array(spend_values)
            counterparty_arr = np.array(counterparty_values)
            
            aggregates = {
                'total_count': len(spend_values),
                'avg_period_spend': float(np.mean(spend_arr)),
                'median_period_spend': float(np.median(spend_arr)),
                'std_period_spend': float(np.std(spend_arr)),
                'avg_counterparties': float(np.mean(counterparty_arr)),
                'median_counterparties': float(np.median(counterparty_arr)),
                'std_counterparties': float(np.std(counterparty_arr)),
                'percentiles': {
                    'p25': float(np.percentile(spend_arr, 25)),
                    'p50': float(np.percentile(spend_arr, 50)),
                    'p75': float(np.percentile(spend_arr, 75)),
                    'p90': float(np.percentile(spend_arr, 90))
                }
            }
        
        # Save to DuckDB
        conn.execute("""
        INSERT OR REPLACE INTO aggregates 
        (entity_type, aggregates_data, calculated_at)
        VALUES (?, ?, ?)
        """, [entity_type, json.dumps(aggregates), now])
        
        conn.close()
        logger.info(f"✓ Saved aggregates for {len(entities)} {entity_type}s")
    # ============================================================
    # MAIN SYNC (replaces populate_total_data.py main function)
    # ============================================================
    
    def sync(self, entity_type=None):
        """
        Main sync - runs total queries and stores in DuckDB
        Replaces populate_total_data.py entirely
        """
        start_time = datetime.now()
        entity_types = [entity_type] if entity_type else ['buyer', 'seller']
        
        logger.info("=" * 60)
        logger.info("DUCKDB SYNC STARTED")
        logger.info(f"Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60)
        
        self.initialize_schema()
        
        results = {}
        
        for etype in entity_types:
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing {etype.upper()}S")
            logger.info(f"{'='*60}")
            
            try:
                # Use same params as before
                params = config.TOTAL_DATA_PARAMS[etype]
                
                # Step 1: Run total queries against PostgreSQL
                all_results = self.load_and_execute_queries(etype, params)
                
                # Step 2: Organize by entity
                entities = self.organize_by_entity(etype, all_results)
                
                # Step 3: Save to DuckDB
                self.save_entities_to_duckdb(etype, entities)
                
                # Step 4: Calculate and save aggregates
                self.save_aggregates_to_duckdb(etype, entities)
                
                results[etype] = len(entities)
                
                # Log success
                duck_conn = self.get_duck_conn()
                duck_conn.execute("""
                INSERT INTO sync_log VALUES (?, ?, ?, ?, 'success', NULL)
                """, [
                    datetime.now().isoformat(),
                    etype,
                    len(entities),
                    (datetime.now() - start_time).total_seconds()
                ])
                duck_conn.close()
                
            except Exception as e:
                logger.error(f"✗ Failed for {etype}: {e}")
                results[etype] = 0
        
        duration = (datetime.now() - start_time).total_seconds()
        
        logger.info("\n" + "=" * 60)
        logger.info("SYNC COMPLETE")
        logger.info(f"Duration: {duration:.2f}s")
        for etype, count in results.items():
            logger.info(f"  ✓ {etype}s: {count} entities")
        logger.info("=" * 60)
        
        return results
    
    # ============================================================
    # HEALTH CHECK
    # ============================================================
    
    def health_check(self):
        conn = self.get_duck_conn()
        
        buyer_count = conn.execute(
            "SELECT COUNT(*) FROM entities WHERE entity_type = 'buyer'"
        ).fetchone()[0]
        
        seller_count = conn.execute(
            "SELECT COUNT(*) FROM entities WHERE entity_type = 'seller'"
        ).fetchone()[0]
        
        last_sync = conn.execute("""
        SELECT synced_at, status 
        FROM sync_log 
        ORDER BY synced_at DESC 
        LIMIT 1
        """).fetchone()
        
        db_size = os.path.getsize(self.duck_path) / (1024*1024)
        
        conn.close()
        
        print("\n" + "=" * 50)
        print("DUCKDB HEALTH CHECK")
        print("=" * 50)
        print(f"DB Path:       {self.duck_path}")
        print(f"DB Size:       {db_size:.2f} MB")
        print(f"Buyers:        {buyer_count}")
        print(f"Sellers:       {seller_count}")
        if last_sync:
            print(f"Last Sync:     {last_sync[0]} ({last_sync[1]})")
        print("=" * 50)


def main():
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--entity', choices=['buyer', 'seller'])
    parser.add_argument('--health-check', action='store_true')
    args = parser.parse_args()
    
    syncer = DuckDBSync()
    
    if args.health_check:
        syncer.health_check()
        return
    
    syncer.sync(entity_type=args.entity)
    syncer.health_check()


if __name__ == '__main__':
    main()