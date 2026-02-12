"""
Complete Pipeline Runner
Executes queries and generates insights for all buyers and sellers
"""

import argparse
import sys
from datetime import datetime
from query_executor import QueryExecutor
from insights_generator import InsightsGenerator
import config

class PipelineRunner:
    def __init__(self):
        self.executor = QueryExecutor()
        self.generator = InsightsGenerator()
        self.stats = {
            'buyer': {'queries': 0, 'insights': 0, 'errors': 0},
            'seller': {'queries': 0, 'insights': 0, 'errors': 0}
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
    
    def run_queries_for_entity_type(self, entity_type, limit=None):
        """Execute all queries for a given entity type"""
        self.print_section(f"STEP 1: Executing Queries for {entity_type.upper()}S")
        
        try:
            files = self.executor.process_all_entities(entity_type, limit=limit)
            self.stats[entity_type]['queries'] = len(files)
            print(f"\n✓ Successfully executed queries for {len(files)} {entity_type}s")
            return files
        except Exception as e:
            print(f"\n✗ Error executing queries for {entity_type}s: {e}")
            self.stats[entity_type]['errors'] += 1
            return []
    
    def generate_insights_for_entity_type(self, entity_type):
        """Generate insights for all entities of a given type"""
        self.print_section(f"STEP 2: Generating Insights for {entity_type.upper()}S")
        
        try:
            files = self.generator.process_all_raw_files(entity_type)
            self.stats[entity_type]['insights'] = len(files)
            print(f"\n✓ Successfully generated insights for {len(files)} {entity_type}s")
            return files
        except Exception as e:
            print(f"\n✗ Error generating insights for {entity_type}s: {e}")
            self.stats[entity_type]['errors'] += 1
            return []
    
    def run_full_pipeline(self, entity_types=['buyer', 'seller'], limit=None):
        """Run complete pipeline for specified entity types"""
        start_time = datetime.now()
        
        self.print_header(f"PROCUREMENT INSIGHTS PIPELINE - {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        print(f"Entity Types: {', '.join([e.capitalize() for e in entity_types])}")
        if limit:
            print(f"Limit: {limit} entities per type")
        print()
        
        # Process each entity type
        for entity_type in entity_types:
            self.print_header(f"Processing {entity_type.upper()}S")
            
            # Step 1: Execute queries
            query_files = self.run_queries_for_entity_type(entity_type, limit)
            
            if not query_files:
                print(f"\n⚠ Skipping insights generation for {entity_type}s (no query results)")
                continue
            
            # Step 2: Generate insights
            insight_files = self.generate_insights_for_entity_type(entity_type)
        
        # Print summary
        self.print_summary(start_time)
    
    def print_summary(self, start_time):
        """Print execution summary"""
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        self.print_header("EXECUTION SUMMARY")
        
        print(f"Start Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"End Time:   {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Duration:   {duration:.2f} seconds ({duration/60:.2f} minutes)")
        print()
        
        # Buyers summary
        print("BUYERS:")
        print(f"  Queries Executed: {self.stats['buyer']['queries']}")
        print(f"  Insights Generated: {self.stats['buyer']['insights']}")
        print(f"  Errors: {self.stats['buyer']['errors']}")
        print()
        
        # Sellers summary
        print("SELLERS:")
        print(f"  Queries Executed: {self.stats['seller']['queries']}")
        print(f"  Insights Generated: {self.stats['seller']['insights']}")
        print(f"  Errors: {self.stats['seller']['errors']}")
        print()
        
        # Totals
        total_queries = self.stats['buyer']['queries'] + self.stats['seller']['queries']
        total_insights = self.stats['buyer']['insights'] + self.stats['seller']['insights']
        total_errors = self.stats['buyer']['errors'] + self.stats['seller']['errors']
        
        print("TOTALS:")
        print(f"  Total Queries: {total_queries}")
        print(f"  Total Insights: {total_insights}")
        print(f"  Total Errors: {total_errors}")
        print()
        
        if total_errors == 0:
            print("✓ Pipeline completed successfully!")
        else:
            print(f"⚠ Pipeline completed with {total_errors} error(s)")
        
        print(f"\n{'='*70}\n")


def main():
    parser = argparse.ArgumentParser(
        description='Run complete insights pipeline for buyers and sellers',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process everything (all buyers and sellers)
  python run_all.py
  
  # Process only buyers
  python run_all.py --buyers-only
  
  # Process only sellers
  python run_all.py --sellers-only
  
  # Process limited number (10 buyers + 10 sellers)
  python run_all.py --limit 10
  
  # Process 5 buyers only
  python run_all.py --buyers-only --limit 5
        """
    )
    
    parser.add_argument(
        '--buyers-only',
        action='store_true',
        help='Process only buyers (skip sellers)'
    )
    
    parser.add_argument(
        '--sellers-only',
        action='store_true',
        help='Process only sellers (skip buyers)'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of entities to process per type'
    )
    
    parser.add_argument(
        '--start-date',
        help='Start date for queries (YYYY-MM-DD)'
    )
    
    parser.add_argument(
        '--end-date',
        help='End date for queries (YYYY-MM-DD)'
    )
    
    args = parser.parse_args()
    
    # Determine which entity types to process
    if args.buyers_only and args.sellers_only:
        print("Error: Cannot specify both --buyers-only and --sellers-only")
        sys.exit(1)
    
    entity_types = []
    if args.buyers_only:
        entity_types = ['buyer']
    elif args.sellers_only:
        entity_types = ['seller']
    else:
        entity_types = ['buyer', 'seller']
    
    # Update default params if dates provided
    if args.start_date or args.end_date:
        for entity_type in entity_types:
            if args.start_date:
                config.DEFAULT_PARAMS[entity_type]['start_date'] = args.start_date
            if args.end_date:
                config.DEFAULT_PARAMS[entity_type]['end_date'] = args.end_date
    
    # Run pipeline
    runner = PipelineRunner()
    runner.run_full_pipeline(entity_types, limit=args.limit)


if __name__ == '__main__':
    main()