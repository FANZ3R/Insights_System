"""
Query Executor: Runs SQL queries from combined files and saves raw results
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

class QueryExecutor:
    def __init__(self, db_config=None):
        self.db_config = db_config or config.DB_CONFIG
        self.parser = QueryParser()
        
        # Ensure data directories exist
        os.makedirs(config.RAW_DATA_DIR, exist_ok=True)
        os.makedirs(config.PROCESSED_DATA_DIR, exist_ok=True)
    
    def get_connection(self):
        """Create database connection"""
        return psycopg2.connect(**self.db_config)
    
    def get_entity_ids(self, entity_type):
        """Get all IDs for a given entity type - ONLY ACTIVE ONES"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get date range from default params
        params = config.DEFAULT_PARAMS[entity_type]
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
    
    def load_queries_from_file(self, entity_type):
        """Load and parse all queries from combined SQL file"""
        query_file = config.QUERY_FILES[entity_type]
        query_path = os.path.join(config.QUERIES_DIR, entity_type, query_file)
        
        print(f"Loading queries from: {query_path}")
        queries = self.parser.parse_file(query_path)
        print(f"Found {len(queries)} queries: {[q['name'] for q in queries]}")
        
        return queries
    
    def execute_query(self, query, params):
        """Execute query with parameters and return results"""
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        try:
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            # Convert to list of dicts and handle Decimal/datetime serialization
            results_list = []
            for row in results:
                row_dict = dict(row)
                # Convert any non-serializable types
                for key, value in row_dict.items():
                    if hasattr(value, 'isoformat'):
                        row_dict[key] = value.isoformat()
                    elif isinstance(value, (int, float, str, bool, type(None))):
                        pass  # Already serializable
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
    
    def execute_all_queries_for_entity(self, entity_type, entity_id, params=None):
        """Execute all queries for a specific entity and return combined results"""
        if params is None:
            params = config.DEFAULT_PARAMS[entity_type].copy()
        
        results = {
            'entity_type': entity_type,
            'entity_id': entity_id,
            'execution_timestamp': datetime.now().isoformat(),
            'parameters': params,
            'queries': {}
        }
        
        # Load queries from combined file
        queries = self.load_queries_from_file(entity_type)
        
        for query_info in queries:
            query_name = query_info['name']
            print(f"  Executing {query_name}...")
            
            try:
                # Execute query
                query_results = self.execute_query(query_info['query'], params)
                
                # Filter results for this entity_id
                id_field = 'buyer_org_id' if entity_type == 'buyer' else 'vendor_id'
                filtered_results = [r for r in query_results if r.get(id_field) == entity_id]
                
                results['queries'][query_name] = {
                    'description': query_info['description'],
                    'result_count': len(filtered_results),
                    'data': filtered_results
                }
                
                print(f"    ✓ {len(filtered_results)} rows returned")
                
            except Exception as e:
                print(f"    ✗ Error: {e}")
                results['queries'][query_name] = {
                    'description': query_info['description'],
                    'error': str(e),
                    'data': []
                }
        
        return results
    
    def save_raw_data(self, entity_type, entity_id, data):
        """Save raw query results to JSON file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{entity_type}_{entity_id}_{timestamp}.json"
        filepath = os.path.join(config.RAW_DATA_DIR, filename)
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"\n✓ Saved raw data to: {filepath}")
        return filepath
    
    def process_entity(self, entity_type, entity_id, params=None):
        """Execute all queries for an entity and save results"""
        print(f"\n{'='*60}")
        print(f"Processing {entity_type.upper()} ID: {entity_id}")
        print(f"{'='*60}")
        
        results = self.execute_all_queries_for_entity(entity_type, entity_id, params)
        filepath = self.save_raw_data(entity_type, entity_id, results)
        
        return filepath
    
    def process_all_entities(self, entity_type, params=None, limit=None):
        """Process all entities of a given type"""
        entity_ids = self.get_entity_ids(entity_type)
        
        if limit:
            entity_ids = entity_ids[:limit]
        
        print(f"\nFound {len(entity_ids)} active {entity_type}s to process")
        
        processed_files = []
        for i, entity_id in enumerate(entity_ids, 1):
            print(f"\nProcessing {i}/{len(entity_ids)}...")
            try:
                filepath = self.process_entity(entity_type, entity_id, params)
                processed_files.append(filepath)
            except Exception as e:
                print(f"Error processing {entity_type} {entity_id}: {e}")
                continue
        
        print(f"\n{'='*60}")
        print(f"Completed: {len(processed_files)}/{len(entity_ids)} {entity_type}s processed")
        print(f"{'='*60}")
        
        return processed_files


def main():
    parser = argparse.ArgumentParser(description='Execute queries and save raw data')
    parser.add_argument('--entity', choices=['buyer', 'seller'], required=True,
                       help='Entity type to process')
    parser.add_argument('--id', type=int, help='Specific entity ID to process')
    parser.add_argument('--all', action='store_true', help='Process all entities')
    parser.add_argument('--limit', type=int, help='Limit number of entities to process')
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD)')
    parser.add_argument('--top-n', type=int, help='Number of top items to return')
    
    args = parser.parse_args()
    
    # Build parameters
    params = config.DEFAULT_PARAMS[args.entity].copy()
    if args.start_date:
        params['start_date'] = args.start_date
    if args.end_date:
        params['end_date'] = args.end_date
    if args.top_n:
        params['top_n'] = args.top_n
    
    # Execute
    executor = QueryExecutor()
    
    if args.id:
        executor.process_entity(args.entity, args.id, params)
    elif args.all:
        executor.process_all_entities(args.entity, params, limit=args.limit)
    else:
        print("Error: Either --id or --all must be specified")
        parser.print_help()


if __name__ == '__main__':
    main()