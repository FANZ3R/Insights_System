"""
Complete Dashboard Pipeline Runner
Executes dashboard queries and generates benchmarked insights
(Does NOT populate total data - run populate_total_data.py separately)
"""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path
from dashboard_executor import DashboardExecutor
from insights_generator import BenchmarkingInsightsGenerator
import config

class DashboardPipeline:
    def __init__(self):
        self.executor = DashboardExecutor()
        self.generator = BenchmarkingInsightsGenerator()
        self.stats = {
            'queries_executed': 0,
            'insights_generated': 0,
            'errors': []
        }
    
    def print_header(self, text):
        """Print formatted header"""
        print(f"\n{'='*70}")
        print(f"  {text}")
        print(f"{'='*70}\n")
    
    def print_section(self, text):
        """Print section separator"""
        print(f"\n{'-'*70}")
        print(f"  {text}")
        print(f"{'-'*70}\n")
    
    def verify_total_data_exists(self, entity_type):
        """Check if total data file exists"""
        filename = config.TOTAL_DATA_FILES[entity_type]
        filepath = Path(config.TOTAL_DATA_DIR) / filename
        
        if not filepath.exists():
            print(f"\n{'='*70}")
            print(f"  ⚠ WARNING: Total Data Not Found")
            print(f"{'='*70}")
            print(f"\nMissing file: {filepath}")
            print(f"\nYou need to populate total data first by running:")
            print(f"  python src/populate_total_data.py")
            print(f"\nThis creates the baseline data for benchmarking.")
            print(f"{'='*70}\n")
            return False
        
        return True
    
    def run_for_single_entity(self, entity_type, entity_id, params=None):
        """Run complete pipeline for single entity"""
        
        # Verify total data exists
        if not self.verify_total_data_exists(entity_type):
            return None
        
        self.print_header(f"Dashboard Pipeline: {entity_type.upper()} {entity_id}")
        
        # Step 1: Execute dashboard queries
        self.print_section("STEP 1: Executing Dashboard Queries")
        
        try:
            dashboard_file = self.executor.process_entity(entity_type, entity_id, params)
            self.stats['queries_executed'] += 1
            print(f"✓ Dashboard queries executed successfully")
        except Exception as e:
            print(f"✗ Error executing dashboard queries: {e}")
            self.stats['errors'].append(('query', entity_id, str(e)))
            return None
        
        # Step 2: Generate insights
        self.print_section("STEP 2: Generating Benchmarked Insights")
        
        try:
            insights_file = self.generator.generate_insights(dashboard_file)
            self.stats['insights_generated'] += 1
            print(f"✓ Insights generated successfully")
            
            return insights_file
        except Exception as e:
            print(f"✗ Error generating insights: {e}")
            self.stats['errors'].append(('insights', entity_id, str(e)))
            return None
    
    def run_for_all_entities(self, entity_type, params=None, limit=None):
        """Run complete pipeline for all active entities"""
        
        # Verify total data exists
        if not self.verify_total_data_exists(entity_type):
            sys.exit(1)
        
        self.print_header(f"Dashboard Pipeline: All {entity_type.upper()}S")
        
        if limit:
            print(f"Limit: {limit} entities")
        
        # Step 1: Execute dashboard queries for all entities
        self.print_section("STEP 1: Executing Dashboard Queries")
        
        try:
            dashboard_files = self.executor.process_all_entities(entity_type, params, limit)
            self.stats['queries_executed'] = len(dashboard_files)
            
            if not dashboard_files:
                print(f"No dashboard files created. Exiting.")
                return []
        except Exception as e:
            print(f"✗ Error executing dashboard queries: {e}")
            return []
        
        # Step 2: Generate insights for all dashboard files
        self.print_section("STEP 2: Generating Benchmarked Insights")
        
        insight_files = []
        
        for i, dashboard_file in enumerate(dashboard_files, 1):
            print(f"\nProcessing {i}/{len(dashboard_files)}: {Path(dashboard_file).name}")
            
            try:
                insights_file = self.generator.generate_insights(dashboard_file)
                insight_files.append(insights_file)
                self.stats['insights_generated'] += 1
            except Exception as e:
                print(f"✗ Error generating insights: {e}")
                self.stats['errors'].append(('insights', dashboard_file, str(e)))
                continue
        
        return insight_files
    
    def print_summary(self, start_time):
        """Print execution summary"""
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        self.print_header("PIPELINE SUMMARY")
        
        print(f"Start Time:  {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"End Time:    {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Duration:    {duration:.2f} seconds ({duration/60:.2f} minutes)")
        print()
        
        print(f"Dashboard Queries Executed:  {self.stats['queries_executed']}")
        print(f"Insights Generated:          {self.stats['insights_generated']}")
        print(f"Errors:                      {len(self.stats['errors'])}")
        print()
        
        if self.stats['errors']:
            print("Errors:")
            for error_type, entity, message in self.stats['errors'][:5]:
                print(f"  - [{error_type}] {entity}: {message}")
            if len(self.stats['errors']) > 5:
                print(f"  ... and {len(self.stats['errors']) - 5} more")
            print()
        
        if len(self.stats['errors']) == 0:
            print("✓ Pipeline completed successfully!")
        else:
            print(f"⚠ Pipeline completed with {len(self.stats['errors'])} error(s)")
        
        print(f"\n{'='*70}\n")


def main():
    parser = argparse.ArgumentParser(
        description='Run dashboard pipeline: execute queries + generate insights',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
IMPORTANT: This pipeline requires total data to exist first!
If you haven't populated total data yet, run:
  python src/populate_total_data.py

Examples:
  # Single entity (default 90 days)
  python src/run_all.py --entity buyer --id 5098
  
  # Last 30 days
  python src/run_all.py --entity buyer --id 5098 --days 30
  
  # Last 180 days
  python src/run_all.py --entity seller --id 7 --days 180
  
  # Custom date range
  python src/run_all.py --entity buyer --id 5098 \\
    --start-date 2025-11-01 --end-date 2026-02-13
  
  # All buyers (limited)
  python src/run_all.py --entity buyer --all --limit 10

What this does:
  1. Executes dashboard_specific queries for the entity/entities
  2. Saves results to data/dashboard_data/raw/
  3. Loads total_data for comparison
  4. Generates benchmarked insights comparing dashboard vs total
  5. Saves insights to data/dashboard_data/processed/

What this does NOT do:
  - Does NOT populate total data (run populate_total_data.py for that)
  - Does NOT modify existing total data files
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
        help='Limit number of entities (use with --all)'
    )
    
    parser.add_argument(
        '--days',
        type=int,
        help='Number of days back from today (e.g., 30, 90, 180, 365)'
    )
    
    parser.add_argument(
        '--start-date',
        help='Start date for dashboard period (YYYY-MM-DD)'
    )
    
    parser.add_argument(
        '--end-date',
        help='End date for dashboard period (YYYY-MM-DD)'
    )
    
    parser.add_argument(
        '--top-n',
        type=int,
        help='Number of top items in rankings'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.id and not args.all:
        print("Error: Must specify either --id or --all")
        parser.print_help()
        sys.exit(1)
    
    if args.id and args.all:
        print("Error: Cannot use both --id and --all")
        parser.print_help()
        sys.exit(1)
    
    # Build parameters
    params = config.DEFAULT_PARAMS[args.entity].copy()
    
    # Handle --days argument (takes precedence over default)
    if args.days:
        params['start_date'] = (datetime.now() - timedelta(days=args.days)).strftime('%Y-%m-%d')
        params['end_date'] = datetime.now().strftime('%Y-%m-%d')
        print(f"\nUsing --days={args.days}: {params['start_date']} to {params['end_date']}\n")
    
    # Handle explicit dates (override --days)
    if args.start_date:
        params['start_date'] = args.start_date
    if args.end_date:
        params['end_date'] = args.end_date
    if args.top_n:
        params['top_n'] = args.top_n
    
    # Run pipeline
    start_time = datetime.now()
    pipeline = DashboardPipeline()
    
    if args.id:
        pipeline.run_for_single_entity(args.entity, args.id, params)
    elif args.all:
        pipeline.run_for_all_entities(args.entity, params, args.limit)
    
    pipeline.print_summary(start_time)


if __name__ == '__main__':
    main()