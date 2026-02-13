"""
Dashboard Executor: Run dashboard-specific queries for individual entities
"""

import psycopg2
import psycopg2.extras
import json
import os
import argparse
from datetime import datetime
from pathlib import Path
import config
from query_parser import QueryParser

class DashboardExecutor:
    def __init__(self, db_config=None):
        self.db_config = db_config or config.DB_CONFIG
        self.parser = QueryParser()
        
        # Ensure directories exist
        os.makedirs(config.DASHBOARD_RAW_DIR, exist_ok=True)
    
    def get_connection(self):
        """Create database connection"""
        return psycopg2.connect(**self.db_config)
    
    def get_active_entity_ids(self, entity_type, params):
        """Get all active entity IDs for a given entity type within date range"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        start_date = params['start_date']
        end_date = params['end_date']
        
        if entity_type == 'buyer':
            query = f"""
            SELECT DISTINCT pd.buyer_org_id 
            FROM po_details pd
            JOIN po_items pi ON pd.id = pi.po_id
            WHERE pd.buyer_org_id IS NOT NULL
              AND pi.updated_date BETWEEN '{start_date}' AND '{end_date}'
            ORDER BY pd.buyer_org_id
            """
        else:  # seller
            query = f"""
            SELECT DISTINCT pd.seller_org_id 
            FROM po_details pd
            JOIN po_items pi ON pd.id = pi.po_id
            WHERE pd.seller_org_id IS NOT NULL
              AND pi.created_date BETWEEN '{start_date}' AND '{end_date}'
            ORDER BY pd.seller_org_id
            """
        
        cursor.execute(query)
        ids = [row[0] for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        return ids
    
    def load_dashboard_queries(self, entity_type):
        """Load dashboard queries from SQL file"""
        query_file = config.DASHBOARD_QUERY_FILES[entity_type]
        query_path = os.path.join(config.DASHBOARD_QUERIES_DIR, entity_type, query_file)
        
        print(f"Loading dashboard queries from: {query_path}")
        queries = self.parser.parse_file(query_path)
        print(f"Found {len(queries)} queries: {[q['name'] for q in queries]}")
        
        return queries
    
    def execute_query(self, query, params):
        """Execute query with parameters"""
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        try:
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            # Convert to serializable format
            results_list = []
            for row in results:
                row_dict = dict(row)
                for key, value in row_dict.items():
                    if hasattr(value, 'isoformat'):
                        row_dict[key] = value.isoformat()
                    elif isinstance(value, (int, float, str, bool, type(None))):
                        pass
                    else:
                        row_dict[key] = str(value)
                results_list.append(row_dict)
            
            return results_list
        except Exception as e:
            print(f"Error executing query: {e}")
            raise
        finally:
            cursor.close()
            conn.close()
    
    def execute_for_entity(self, entity_type, entity_id, params=None):
        """Execute dashboard queries for specific entity"""
        if params is None:
            params = config.DEFAULT_PARAMS[entity_type].copy()
        
        print(f"\n{'='*60}")
        print(f"Executing Dashboard Queries")
        print(f"{'='*60}")
        print(f"Entity: {entity_type.upper()} {entity_id}")
        print(f"Period: {params['start_date']} to {params['end_date']}")
        print(f"{'='*60}\n")
        
        queries = self.load_dashboard_queries(entity_type)
        
        results = {
            'entity_type': entity_type,
            'entity_id': entity_id,
            'execution_timestamp': datetime.now().isoformat(),
            'parameters': params,
            'queries': {}
        }
        
        # Determine ID field name based on entity type
        id_field = 'buyer_org_id' if entity_type == 'buyer' else 'vendor_id'
        
        for query_info in queries:
            query_name = query_info['name']
            print(f"  Executing {query_name}...")
            
            try:
                query_results = self.execute_query(query_info['query'], params)
                
                # Filter for this entity
                filtered = [r for r in query_results if r.get(id_field) == entity_id]
                
                results['queries'][query_name] = {
                    'description': query_info['description'],
                    'result_count': len(filtered),
                    'data': filtered
                }
                
                print(f"    ✓ {len(filtered)} rows returned")
            except Exception as e:
                print(f"    ✗ Error: {e}")
                results['queries'][query_name] = {
                    'description': query_info['description'],
                    'error': str(e),
                    'data': []
                }
        
        return results
    
    def save_dashboard_raw(self, entity_type, entity_id, data):
        """Save dashboard raw data"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{entity_type}_{entity_id}_dashboard_{timestamp}.json"
        filepath = os.path.join(config.DASHBOARD_RAW_DIR, filename)
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"\n{'='*60}")
        print(f"✓ Saved dashboard raw data to:")
        print(f"  {filepath}")
        print(f"{'='*60}\n")
        
        return filepath
    
    def process_entity(self, entity_type, entity_id, params=None):
        """Execute queries and save for single entity"""
        results = self.execute_for_entity(entity_type, entity_id, params)
        filepath = self.save_dashboard_raw(entity_type, entity_id, results)
        return filepath
    
    def process_all_entities(self, entity_type, params=None, limit=None):
        """Process all active entities of a given type"""
        if params is None:
            params = config.DEFAULT_PARAMS[entity_type].copy()
        
        # Get active entity IDs
        print(f"\n{'='*60}")
        print(f"Finding Active {entity_type.upper()}S")
        print(f"{'='*60}")
        print(f"Period: {params['start_date']} to {params['end_date']}")
        print(f"{'='*60}\n")
        
        entity_ids = self.get_active_entity_ids(entity_type, params)
        
        if limit:
            entity_ids = entity_ids[:limit]
        
        print(f"Found {len(entity_ids)} active {entity_type}s to process")
        
        if not entity_ids:
            print(f"No active {entity_type}s found in the specified period.")
            return []
        
        processed_files = []
        errors = []
        
        for i, entity_id in enumerate(entity_ids, 1):
            print(f"\n{'='*60}")
            print(f"Processing {i}/{len(entity_ids)}")
            print(f"{'='*60}")
            
            try:
                filepath = self.process_entity(entity_type, entity_id, params)
                processed_files.append(filepath)
            except Exception as e:
                print(f"\n✗ Error processing {entity_type} {entity_id}: {e}")
                errors.append((entity_id, str(e)))
                continue
        
        # Summary
        print(f"\n{'='*60}")
        print(f"EXECUTION COMPLETE")
        print(f"{'='*60}")
        print(f"Successfully processed: {len(processed_files)}/{len(entity_ids)}")
        print(f"Errors: {len(errors)}")
        
        if errors:
            print("\nFailed entities:")
            for entity_id, error in errors[:10]:  # Show first 10 errors
                print(f"  - {entity_type} {entity_id}: {error}")
            if len(errors) > 10:
                print(f"  ... and {len(errors) - 10} more")
        
        print(f"{'='*60}\n")
        
        return processed_files


def main():
    parser = argparse.ArgumentParser(
        description='Execute dashboard queries for buyers/sellers',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single entity
  python dashboard_executor.py --entity buyer --id 5098
  
  # Custom date range
  python dashboard_executor.py --entity buyer --id 5098 \\
    --start-date 2025-11-01 --end-date 2026-02-12
  
  # All buyers (current period from config)
  python dashboard_executor.py --entity buyer --all
  
  # All sellers with limit
  python dashboard_executor.py --entity seller --all --limit 10
  
  # All buyers with custom date range
  python dashboard_executor.py --entity buyer --all \\
    --start-date 2025-01-01 --end-date 2025-12-31

Output:
  Creates files in data/dashboard_data/raw/:
  - buyer_5098_dashboard_20260212_143024.json
  - seller_7_dashboard_20260212_143156.json

Next Steps:
  After running this, use insights_generator.py to generate insights:
  python insights_generator.py --all
        """
    )
    
    parser.add_argument(
        '--entity',
        choices=['buyer', 'seller'],
        required=True,
        help='Entity type to process'
    )
    
    parser.add_argument(
        '--id',
        type=int,
        help='Specific entity ID to process'
    )
    
    parser.add_argument(
        '--all',
        action='store_true',
        help='Process all active entities'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of entities to process (use with --all)'
    )
    
    parser.add_argument(
        '--start-date',
        help='Start date (YYYY-MM-DD). Default from config.'
    )
    
    parser.add_argument(
        '--end-date',
        help='End date (YYYY-MM-DD). Default from config.'
    )
    
    parser.add_argument(
        '--top-n',
        type=int,
        help='Number of top items to return in rankings. Default from config.'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.id and not args.all:
        print("Error: Must specify either --id or --all")
        parser.print_help()
        exit(1)
    
    if args.id and args.all:
        print("Error: Cannot use both --id and --all")
        parser.print_help()
        exit(1)
    
    # Build parameters
    params = config.DEFAULT_PARAMS[args.entity].copy()
    
    if args.start_date:
        params['start_date'] = args.start_date
    if args.end_date:
        params['end_date'] = args.end_date
    if args.top_n:
        params['top_n'] = args.top_n
    
    # Execute
    executor = DashboardExecutor()
    
    if args.id:
        executor.process_entity(args.entity, args.id, params)
    elif args.all:
        executor.process_all_entities(args.entity, params, limit=args.limit)


if __name__ == '__main__':
    main()