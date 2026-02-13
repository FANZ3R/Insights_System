"""
Populate Total Data: Execute comprehensive queries and build single JSON files
"""

import psycopg2
import psycopg2.extras
import json
import os
import argparse
from datetime import datetime, timedelta
from pathlib import Path
import config
from query_parser import QueryParser

class TotalDataPopulator:
    def __init__(self, db_config=None):
        self.db_config = db_config or config.DB_CONFIG
        self.parser = QueryParser()
        
        # Ensure directories exist
        os.makedirs(config.TOTAL_DATA_DIR, exist_ok=True)
    
    def get_connection(self):
        """Create database connection"""
        return psycopg2.connect(**self.db_config)
    
    def load_total_queries(self, entity_type):
        """Load total queries from SQL file"""
        query_file = config.TOTAL_QUERY_FILES[entity_type]
        query_path = os.path.join(config.TOTAL_QUERIES_DIR, entity_type, query_file)
        
        print(f"Loading total queries from: {query_path}")
        queries = self.parser.parse_file(query_path)
        print(f"Found {len(queries)} queries: {[q['name'] for q in queries]}")
        
        return queries
    
    def execute_query(self, query, params):
        """Execute query and return all results"""
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
    
    def build_total_data(self, entity_type, params=None):
        """Execute all total queries and build comprehensive JSON"""
        
        if params is None:
            params = config.TOTAL_DATA_PARAMS[entity_type].copy()
        
        print(f"\n{'='*60}")
        print(f"Building Total Data for {entity_type.upper()}S")
        print(f"{'='*60}")
        print(f"Baseline Period: {params['start_date']} to {params['end_date']}")
        duration_days = (datetime.strptime(params['end_date'], '%Y-%m-%d') - 
                        datetime.strptime(params['start_date'], '%Y-%m-%d')).days
        print(f"Duration: {duration_days} days")
        print(f"{'='*60}\n")
        
        queries = self.load_total_queries(entity_type)
        
        # Execute all queries with parameters
        all_query_results = {}
        for query_info in queries:
            query_name = query_info['name']
            print(f"Executing {query_name}...")
            
            try:
                results = self.execute_query(query_info['query'], params)
                all_query_results[query_name] = {
                    'description': query_info['description'],
                    'result_count': len(results),
                    'data': results
                }
                print(f"  ✓ {len(results)} rows returned")
            except Exception as e:
                print(f"  ✗ Error: {e}")
                all_query_results[query_name] = {
                    'description': query_info['description'],
                    'error': str(e),
                    'data': []
                }
        
        # Organize by entity ID
        id_field = 'buyer_org_id' if entity_type == 'buyer' else 'vendor_id'
        entities = {}
        
        for query_name, query_result in all_query_results.items():
            for row in query_result.get('data', []):
                entity_id = row.get(id_field)
                if entity_id is None:
                    continue
                
                # Convert to string for consistent key access
                entity_id_str = str(entity_id)
                
                if entity_id_str not in entities:
                    entities[entity_id_str] = {
                        'entity_id': entity_id,
                        'entity_type': entity_type,
                        'queries': {}
                    }
                
                if query_name not in entities[entity_id_str]['queries']:
                    entities[entity_id_str]['queries'][query_name] = []
                
                entities[entity_id_str]['queries'][query_name].append(row)
        
        # Build final structure
        total_data = {
            'entity_type': entity_type,
            'generated_at': datetime.now().isoformat(),
            'baseline_period': params,
            'total_entities': len(entities),
            'queries_executed': list(all_query_results.keys()),
            'entities': entities
        }
        
        # Calculate aggregates
        print("\nCalculating platform aggregates...")
        aggregates = self.calculate_aggregates(entities, entity_type)
        total_data['aggregates'] = aggregates
        
        return total_data
    
    def calculate_aggregates(self, entities, entity_type):
        """Calculate industry/platform-wide aggregates with percentiles"""
        
        # Extract all overview metrics (from the parameterized queries)
        overview_metrics = []
        for entity_id, entity_data in entities.items():
            #For buyer: look for overview_metrics
            #For seller: look for performance_overview
            if 'overview_metrics' in entity_data['queries']:
                metrics = entity_data['queries']['overview_metrics']
                if metrics:
                    overview_metrics.append(metrics[0])
            elif 'performance_overview' in entity_data['queries']:
                metrics = entity_data['queries']['performance_overview']
                if metrics:
                    overview_metrics.append(metrics[0])
        
        if not overview_metrics:
            print("  ⚠ No overview metrics found for aggregate calculation")
            return {}
        
        print(f"  Processing {len(overview_metrics)} entities for aggregates...")
        
        # Extract values based on entity type (using CURRENT field names from parameterized queries)
        if entity_type == 'buyer':
            spend_values = [float(m.get('current_period_purchases', 0)) for m in overview_metrics]
            quantity_values = [float(m.get('current_period_quantity', 0)) for m in overview_metrics]
            supplier_values = [float(m.get('suppliers_current', 0)) for m in overview_metrics if m.get('suppliers_current')]
            items_values = [float(m.get('items_purchased_current', 0)) for m in overview_metrics if m.get('items_purchased_current')]
        else:  # seller
            spend_values = [float(m.get('total_sales', 0)) for m in overview_metrics]
            buyer_values = [float(m.get('total_buyers', 0)) for m in overview_metrics]
            aov_values = [float(m.get('average_order_value', 0)) for m in overview_metrics if m.get('average_order_value')]
            repeat_rate_values = [float(m.get('repeat_purchase_rate_pct', 0)) for m in overview_metrics if m.get('repeat_purchase_rate_pct')]
                
        # Calculate basic aggregates
        total_count = len(overview_metrics)
        
        aggregates = {
            'total_count': total_count
        }

        if entity_type == 'buyer':
            aggregates.update({
                'avg_period_spend': sum(spend_values) / len(spend_values) if spend_values else 0,
                'avg_period_quantity': sum(quantity_values) / len(quantity_values) if quantity_values else 0,
                'avg_suppliers': sum(supplier_values) / len(supplier_values) if supplier_values else 0,
                'avg_items_purchased': sum(items_values) / len(items_values) if items_values else 0
            })
        else:
            aggregates.update({
                'avg_period_sales': sum(spend_values) / len(spend_values) if spend_values else 0,
                'avg_period_buyers': sum(buyer_values) / len(buyer_values) if buyer_values else 0,
                'avg_order_value': sum(aov_values) / len(aov_values) if aov_values else 0,
                'avg_repeat_rate': sum(repeat_rate_values) / len(repeat_rate_values) if repeat_rate_values else 0
            })
        # Calculate percentiles
        try:
            import numpy as np
            
            aggregates['percentiles'] = {}
            
            for p in config.AGGREGATE_PERCENTILES:
                percentile_data = {
                    'spend': float(np.percentile(spend_values, p)) if spend_values else 0
                }
              
                if entity_type == 'buyer':
                    percentile_data['quantity'] = float(np.percentile(quantity_values, p)) if quantity_values else 0
                    percentile_data['suppliers'] = float(np.percentile(supplier_values, p)) if supplier_values else 0
                    percentile_data['items'] = float(np.percentile(items_values, p)) if items_values else 0
                else:
                    percentile_data['buyers'] = float(np.percentile(buyer_values, p)) if buyer_values else 0
                    percentile_data['aov'] = float(np.percentile(aov_values, p)) if aov_values else 0
                    percentile_data['repeat_rate'] = float(np.percentile(repeat_rate_values, p)) if repeat_rate_values else 0
                
                aggregates['percentiles'][f'p{p}'] = percentile_data
                        
            print(f"  ✓ Calculated percentiles: {config.AGGREGATE_PERCENTILES}")
        
        except ImportError:
            print("  ⚠ NumPy not installed - skipping percentile calculations")
            print("    Install with: pip install numpy --break-system-packages")
        
        return aggregates
    
    def save_total_data(self, entity_type, data):
        """Save total data to JSON file"""
        filename = config.TOTAL_DATA_FILES[entity_type]
        filepath = os.path.join(config.TOTAL_DATA_DIR, filename)
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"\n{'='*60}")
        print(f"✓ Saved total data to: {filepath}")
        print(f"{'='*60}")
        print(f"Baseline period: {data['baseline_period']['start_date']} to {data['baseline_period']['end_date']}")
        print(f"Total entities: {data['total_entities']}")
        print(f"Queries executed: {len(data['queries_executed'])}")
        print(f"Aggregates calculated: {len(data.get('aggregates', {}))}")
        
        if 'percentiles' in data.get('aggregates', {}):
            print(f"Percentiles: {list(data['aggregates']['percentiles'].keys())}")
        
        print(f"{'='*60}\n")
        
        return filepath
    
    def populate(self, entity_types=['buyer', 'seller'], params = None):
        """Populate total data for specified entity types"""
        start_time = datetime.now()
        
        print(f"\n{'='*60}")
        print(f"TOTAL DATA POPULATION")
        print(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")
        
        results = {}
        
        for entity_type in entity_types:
            try:
                # Use custom params if provided, otherwise use defaults
                entity_params = params.get(entity_type) if params else None
                total_data = self.build_total_data(entity_type, entity_params)
                filepath = self.save_total_data(entity_type, total_data)
                results[entity_type] = {
                    'success': True,
                    'filepath': filepath,
                    'entities': total_data['total_entities']
                }
            except Exception as e:
                print(f"\n✗ Error processing {entity_type}s: {e}")
                results[entity_type] = {
                    'success': False,
                    'error': str(e)
                }
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Final summary
        print(f"\n{'='*60}")
        print(f"POPULATION COMPLETE")
        print(f"{'='*60}")
        print(f"Duration: {duration:.2f} seconds ({duration/60:.2f} minutes)")
        print(f"\nResults:")
        
        for entity_type, result in results.items():
            if result['success']:
                print(f"  ✓ {entity_type.capitalize()}s: {result['entities']} entities")
                print(f"    File: {result['filepath']}")
            else:
                print(f"  ✗ {entity_type.capitalize()}s: Failed")
                print(f"    Error: {result['error']}")
        
        print(f"{'='*60}\n")
        
        return results


def main():
    parser = argparse.ArgumentParser(
        description='Populate total data files with configurable baseline period',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
    Examples:
    # Default (365 days from config)
    python populate_total_data.py
    
    # Only buyers with default
    python populate_total_data.py --buyers-only
    
    # Custom period
    python populate_total_data.py --start-date 2024-01-01 --end-date 2026-02-13
    
    # Last 730 days (2 years)
    python populate_total_data.py --days 730

    # Last 180 days (6 months)
    python populate_total_data.py --days 180

    Output:
    Creates JSON files in data/total_data/:
    - buyers_total.json   (baseline data for specified period)
    - sellers_total.json  (baseline data for specified period)
            """
        )
    
    parser.add_argument('--buyers-only', action='store_true', help='Process only buyers')
    parser.add_argument('--sellers-only', action='store_true', help='Process only sellers')
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD)')
    parser.add_argument('--days', type=int, help='Number of days back from today (e.g., 365, 730)')
    parser.add_argument('--top-n', type=int, help='Number of top items in rankings')
    
    args = parser.parse_args()
    
    # Determine entity types
    entity_types = []
    if args.buyers_only:
        entity_types = ['buyer']
    elif args.sellers_only:
        entity_types = ['seller']
    else:
        entity_types = ['buyer', 'seller']
    
    # Build custom parameters if provided
    custom_params = {}
    
    if args.days or args.start_date or args.end_date or args.top_n:
        for entity_type in entity_types:
            params = config.TOTAL_DATA_PARAMS[entity_type].copy()
            
            if args.days:
                params['start_date'] = (datetime.now() - timedelta(days=args.days)).strftime('%Y-%m-%d')
                params['end_date'] = datetime.now().strftime('%Y-%m-%d')
            
            if args.start_date:
                params['start_date'] = args.start_date
            if args.end_date:
                params['end_date'] = args.end_date
            if args.top_n:
                params['top_n'] = args.top_n
            
            custom_params[entity_type] = params
    
    # Run population
    populator = TotalDataPopulator()
    results = populator.populate(entity_types, custom_params if custom_params else None)
    
    # Exit code based on results
    all_success = all(r['success'] for r in results.values())
    exit(0 if all_success else 1)
    
if __name__ == '__main__':
    main()