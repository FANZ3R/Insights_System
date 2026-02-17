"""
Insights Generator: Compare dashboard data vs total data with benchmarking
"""

import json
import os
import argparse
from datetime import datetime
from pathlib import Path
from openai import OpenAI
import config
import sqlite3

class BenchmarkingInsightsGenerator:
    def __init__(self, api_key=None):
        self.api_key = api_key or config.OPENROUTER_API_KEY
        self.client = OpenAI(
            base_url=config.OPENROUTER_BASE_URL,
            api_key=self.api_key
        )
        
        self._aggregates_cache ={}
        
    def get_sqlite_path(self, entity_type):
        """Get SQLite database path"""
        filename = config.TOTAL_DATA_DB_FILES[entity_type]
        return os.path.join(config.TOTAL_DATA_DIR, filename)
        
    def get_aggregates_path(self, entity_type):
        """Get aggregates JSON path"""
        filename = config.AGGREGATES_FILES[entity_type]
        return os.path.join(config.TOTAL_DATA_DIR, filename)
    
    def load_entity_from_duckdb(self, entity_type, entity_id):
        """Loads all queries dynamically - no hardcoding"""
        import duckdb
        
        conn = duckdb.connect(config.ANALYTICS_DB_PATH)
        
        result = conn.execute("""
        SELECT queries_data FROM entities 
        WHERE entity_id = ? AND entity_type = ?
        """, [entity_id, entity_type]).fetchone()
        
        conn.close()
        
        if not result:
            raise ValueError(f"No data found for {entity_type} {entity_id}")
        
        data = json.loads(result[0])
        
        # Log what queries are available - useful for debugging!
        available_queries = list(data.keys())
        print(f"✓ Loaded {len(available_queries)} queries: {available_queries}")
        
        return data
    
    
    def load_aggregates_from_duckdb(self, entity_type):
        """Load aggregates from DuckDB - replaces JSON files"""
        import duckdb
        
        # Cache per session
        if entity_type in self._aggregates_cache:
            print(f"✓ Loaded aggregates from cache")
            return self._aggregates_cache[entity_type]
        
        print(f"Loading platform aggregates from DuckDB...")
        
        conn = duckdb.connect(config.ANALYTICS_DB_PATH)
        
        result = conn.execute("""
        SELECT aggregates_data FROM aggregates 
        WHERE entity_type = ?
        """, [entity_type]).fetchone()
        
        conn.close()
        
        if not result:
            raise ValueError(f"No aggregates found for {entity_type}")
        
        aggregates = json.loads(result[0])
        self._aggregates_cache[entity_type] = aggregates
        
        count = aggregates.get('total_count', 0)
        print(f"✓ Loaded platform aggregates ({count} {entity_type}s)")
        
        return aggregates
    
    
    
    
    
    
    def load_total_data(self, entity_type):
        """Load complete total data file"""
        filename = config.TOTAL_DATA_FILES[entity_type]
        filepath = os.path.join(config.TOTAL_DATA_DIR, filename)
        
        with open(filepath, 'r') as f:
            return json.load(f)
    
    def load_dashboard_raw(self, filepath):
        """Load dashboard raw data"""
        with open(filepath, 'r') as f:
            return json.load(f)
    
    def get_entity_from_total(self, total_data, entity_id):
        """Extract specific entity from total data"""
        return total_data['entities'].get(str(entity_id))
    
    def generate_buyer_insights(self, dashboard_data, entity_total_data, aggregates):
        """Generate buyer insights with benchmarking"""
        
        # Use config for insight counts
        target = config.INSIGHTS_CONFIG['buyer']['target_insights']
        
        # Use config for thresholds
        high_self = config.PRIORITY_THRESHOLDS['high']['self_deviation']
        high_bench = config.PRIORITY_THRESHOLDS['high']['benchmark_deviation']
        medium_self = config.PRIORITY_THRESHOLDS['medium']['self_deviation']
        medium_bench = config.PRIORITY_THRESHOLDS['medium']['benchmark_deviation']
        
        prompt = f"""
You are a procurement analytics expert. Analyze this buyer's current performance against their historical data and industry benchmarks.

CURRENT DASHBOARD DATA (Last 90 days):
{json.dumps(dashboard_data, indent=2)}

BUYER'S LIFETIME/HISTORICAL DATA:
{json.dumps(entity_total_data, indent=2)}

INDUSTRY BENCHMARKS (All Buyers):
{json.dumps(aggregates, indent=2)}

IMPORTANT - Available Benchmark Metrics:
- avg_period_spend: Mean (average) - sensitive to outliers
- median_period_spend: Median (50th percentile) - ROBUST, use this for "typical" comparisons
- std_period_spend: Standard deviation - use to identify if entity is an outlier
- percentiles: p25 (bottom quartile), p50 (median), p75 (top quartile), p90 (top 10%)

Provide {target} insights in the following JSON format:
{{
  "insights": [
    {{
      "title": "Brief insight title",
      "observation": "What the data shows",
      "recommendation": "Specific actionable recommendation",
      "priority": "{"|".join(config.INSIGHT_PRIORITY_LEVELS)}",
      "comparison_type": "{"|".join(config.COMPARISON_TYPES)}",
      "metrics": ["relevant metric names"]
    }}
  ]
}}

Focus on THREE types of comparisons:

1. SELF-COMPARISON (comparison_type: "self"):
   - Current period vs buyer's own historical performance
   - Examples:
     * "Your spending increased 25% vs your lifetime average"
     * "You're ordering 30% more frequently than your historical pattern"
     * "Supplier count dropped from 20 to 5 compared to your average of 15"

2. BENCHMARK COMPARISON (comparison_type: "benchmark"):
   - Current performance vs industry/platform averages
   - Compare against MEDIAN (not just average) for more accurate industry comparison
   - Use STANDARD DEVIATION to identify outliers (>2 std dev = significant outlier)
   - Use PERCENTILES to show ranking position
   - Examples:
     * "Your avg order value ($500) is 40% below platform average ($850)"
     * "Your supplier count (5) is in the bottom 20% percentile"
     * "Your spending per supplier is 2x the industry norm"
     * "Your spending ($500k) is below industry median ($532k) but above average ($850k), indicating a few high spenders skew the market"
     * "Your supplier count (1) is 2.1 standard deviations below the mean (3.7 ± 1.3), making you an outlier"
     * "You're at the 15th percentile for spending (below p25), significantly below typical buyers"
     * "Your price volatility (std: $500) is 2x the industry average (std: $250)"

3. COMBINED INSIGHTS (comparison_type: "both"):
   - When both comparisons tell an interesting story
   - Examples:
     * "You've reduced suppliers from 20 to 5 (75% drop vs historical), but this is still above platform average of 3"
     * "Your price per unit rose 30% vs your average, while industry average only increased 8%"

Prioritization Rules:
- HIGH: Deviations >{high_self}% from self OR >{high_bench}% from benchmark
- MEDIUM: Deviations >{medium_self}% from self OR >{medium_bench}% from benchmark
- LOW: Minor deviations or positive confirmations

Key Focus Areas:
1. Spending patterns and efficiency (price per unit trends, supplier concentration)
2. Supplier diversity and risk (new vs existing suppliers, concentration risk)
3. Procurement growth (current vs historical trends)
4. Category performance (shifts in category spending)
5. Cost optimization opportunities (benchmark comparisons)

Respond ONLY with valid JSON, no additional text.
"""
        
        response = self.client.chat.completions.create(
            model=config.DEFAULT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=config.LLM_CONFIG['temperature'],
            max_tokens=config.LLM_CONFIG['max_tokens']
        )
        
        insights_text = response.choices[0].message.content.strip()
        
        # Parse and validate
        insights = self._parse_and_validate_insights(insights_text)
        
        return insights
    
    def generate_seller_insights(self, dashboard_data, entity_total_data, aggregates):
        """Generate seller insights with benchmarking"""
        
        # Use config for insight counts
        target = config.INSIGHTS_CONFIG['seller']['target_insights']
        
        # Use config for thresholds
        high_self = config.PRIORITY_THRESHOLDS['high']['self_deviation']
        high_bench = config.PRIORITY_THRESHOLDS['high']['benchmark_deviation']
        medium_self = config.PRIORITY_THRESHOLDS['medium']['self_deviation']
        medium_bench = config.PRIORITY_THRESHOLDS['medium']['benchmark_deviation']
        
        prompt = f"""
You are a sales analytics expert. Analyze this seller's current performance against their historical data and industry benchmarks.

CURRENT DASHBOARD DATA (Last 90 days):
{json.dumps(dashboard_data, indent=2)}

SELLER'S LIFETIME/HISTORICAL DATA:
{json.dumps(entity_total_data, indent=2)}

INDUSTRY BENCHMARKS (All Sellers):
{json.dumps(aggregates, indent=2)}


IMPORTANT - Available Benchmark Metrics (Note: "spend" fields contain sales/revenue data for sellers):
- avg_period_spend: Mean sales revenue (average) - sensitive to outliers
- median_period_spend: Median sales revenue (50th percentile) - ROBUST, use this for "typical" comparisons
- std_period_spend: Sales revenue standard deviation - use to identify if entity is an outlier
- avg_suppliers: Mean buyer count (in seller context, this is number of buyers)
- median_suppliers: Median buyer count
- percentiles: p25 (bottom quartile), p50 (median), p75 (top quartile), p90 (top 10%)


Provide {target} insights in the following JSON format:
{{
  "insights": [
    {{
      "title": "Brief insight title",
      "observation": "What the data shows",
      "recommendation": "Specific actionable recommendation",
      "priority": "{"|".join(config.INSIGHT_PRIORITY_LEVELS)}",
      "comparison_type": "{"|".join(config.COMPARISON_TYPES)}",
      "metrics": ["relevant metric names"]
    }}
  ]
}}

Focus on THREE types of comparisons:

1. SELF-COMPARISON (comparison_type: "self"):
   - Current period vs seller's own historical performance
   - Examples:
     * "Your revenue is up 40% vs your quarterly average"
     * "Customer acquisition rate doubled vs historical"
     * "Repeat purchase rate dropped from 35% to 25% compared to your lifetime average"

2. BENCHMARK COMPARISON (comparison_type: "benchmark"):
   - Current performance vs industry/platform averages
   - Compare against MEDIAN (not just average) for more accurate industry comparison
   - Use STANDARD DEVIATION to identify outliers (>2 std dev = significant outlier)
   - Use PERCENTILES to show ranking position
   - Examples:
     * "Your repeat purchase rate (25%) is below platform average (35%)"
     * "Your AOV ($450) is in the top 10% of all sellers"
     * "Your customer count is 50% below industry median"
     * "Your revenue ($2.3M) exceeds industry median ($1.8M) but is below average ($3.5M), indicating top sellers significantly outperform"
     * "Your buyer count (25) is 1.8 standard deviations above the mean (12.5 ± 6.8), showing strong market reach"
     * "You're at the 85th percentile for revenue (above p75), placing you in the top 15% of sellers"
     * "Your monthly sales volatility (std: $450k) is 50% lower than industry average (std: $900k), indicating stable performance"
     * "Your repeat purchase rate (62%) is at the median, but top quartile sellers (p75: 78%) achieve 25% higher retention"
     * "Your average order value ($1,850) is below both median ($2,100) and average ($2,450), suggesting opportunity to upsell"

3. COMBINED INSIGHTS (comparison_type: "both"):
   - When both comparisons tell an interesting story
   - Examples:
     * "Your revenue per customer ($5000) improved 20% vs your average, and is now 15% above platform benchmark"
     * "Monthly sales volatility decreased 30% vs your historical pattern, approaching industry stability levels"

Prioritization Rules:
- HIGH: Deviations >{high_self}% from self OR >{high_bench}% from benchmark
- MEDIUM: Deviations >{medium_self}% from self OR >{medium_bench}% from benchmark
- LOW: Minor deviations or positive confirmations

Key Focus Areas:
1. Revenue trends (current vs historical growth patterns)
2. Customer retention (repeat purchase rate vs self and benchmark)
3. Product performance (top sellers, revenue concentration)
4. Sales efficiency (average order value, units per order vs benchmarks)
5. Growth opportunities (regional expansion, product diversification based on benchmark gaps)

Respond ONLY with valid JSON, no additional text.
"""
        
        response = self.client.chat.completions.create(
            model=config.DEFAULT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=config.LLM_CONFIG['temperature'],
            max_tokens=config.LLM_CONFIG['max_tokens']
        )
        
        insights_text = response.choices[0].message.content.strip()
        
        # Parse and validate
        insights = self._parse_and_validate_insights(insights_text)
        
        return insights
    
    def _parse_and_validate_insights(self, insights_text):
        """Parse LLM response and validate against config rules"""
        try:
            # Remove markdown code blocks if present
            if insights_text.startswith('```'):
                insights_text = insights_text.split('```')[1]
                if insights_text.startswith('json'):
                    insights_text = insights_text[4:]
            
            data = json.loads(insights_text)
            insights = data.get('insights', [])
            
            # Validate each insight
            validated = []
            for insight in insights:
                if self._validate_insight(insight):
                    validated.append(insight)
                else:
                    print(f"⚠ Skipping invalid insight: {insight.get('title', 'No title')}")
            
            return validated
        
        except json.JSONDecodeError as e:
            print(f"Error parsing LLM response: {e}")
            print(f"Raw response: {insights_text}")
            return []
    
    def _validate_insight(self, insight):
        """Validate single insight against config rules"""
        rules = config.INSIGHT_VALIDATION
        
        # Required fields
        if rules['require_title'] and not insight.get('title'):
            return False
        if rules['require_observation'] and not insight.get('observation'):
            return False
        if rules['require_recommendation'] and not insight.get('recommendation'):
            return False
        if rules['require_priority'] and not insight.get('priority'):
            return False
        if rules['require_comparison_type'] and not insight.get('comparison_type'):
            return False
        
        # Length validation
        title = insight.get('title', '')
        if len(title) < rules['min_title_length'] or len(title) > rules['max_title_length']:
            return False
        
        observation = insight.get('observation', '')
        if len(observation) < rules['min_observation_length']:
            return False
        
        recommendation = insight.get('recommendation', '')
        if len(recommendation) < rules['min_recommendation_length']:
            return False
        
        # Valid enum values
        if insight.get('priority') not in config.INSIGHT_PRIORITY_LEVELS:
            return False
        
        if insight.get('comparison_type') not in config.COMPARISON_TYPES:
            return False
        
        # Metrics count
        metrics = insight.get('metrics', [])
        if len(metrics) > rules['max_metrics_per_insight']:
            return False
        
        return True
    
    # def generate_insights(self, dashboard_raw_filepath):
    #     """Generate insights by comparing dashboard vs total data"""
    #     print(f"\n{'='*60}")
    #     print(f"Generating Benchmarked Insights")
    #     print(f"{'='*60}")
    #     print(f"Processing: {dashboard_raw_filepath}")
        
    #     # Load dashboard data
    #     dashboard_data = self.load_dashboard_raw(dashboard_raw_filepath)
    #     entity_type = dashboard_data['entity_type']
    #     entity_id = dashboard_data['entity_id']
        
    #     print(f"\nEntity: {entity_type.upper()} {entity_id}")
    #     print(f"Dashboard Period: {dashboard_data['parameters']['start_date']} to {dashboard_data['parameters']['end_date']}")
        
    #     # Load total data
    #     print(f"\nLoading total data for {entity_type}s...")
    #     total_data = self.load_total_data(entity_type)
    #     entity_total = self.get_entity_from_total(total_data, entity_id)
    #     aggregates = total_data.get('aggregates', {})
        
    #     if not entity_total:
    #         print(f"⚠ Warning: No historical data found for {entity_type} {entity_id}")
    #         print(f"   Insights will be limited to current period analysis only")
    #         entity_total = {}
    #     else:
    #         print(f"✓ Found historical data for {entity_type} {entity_id}")
        
    #     print(f"✓ Loaded platform aggregates ({aggregates.get('total_count', 0)} {entity_type}s)")
        
    #     # Format data for LLM
    #     formatted_dashboard = {
    #         'parameters': dashboard_data['parameters'],
    #         'queries': dashboard_data['queries']
    #     }
        
    #     # Generate insights based on entity type
    #     print(f"\nGenerating insights with LLM...")
    #     if entity_type == 'buyer':
    #         insights = self.generate_buyer_insights(formatted_dashboard, entity_total, aggregates)
    #     else:  # seller
    #         insights = self.generate_seller_insights(formatted_dashboard, entity_total, aggregates)
        
    #     print(f"✓ Generated {len(insights)} insights")
        
    #     # Count comparison types
    #     comparison_counts = {
    #         'self': len([i for i in insights if i.get('comparison_type') == 'self']),
    #         'benchmark': len([i for i in insights if i.get('comparison_type') == 'benchmark']),
    #         'both': len([i for i in insights if i.get('comparison_type') == 'both'])
    #     }
        
    #     print(f"\nInsight breakdown:")
    #     print(f"  Self-comparison: {comparison_counts['self']}")
    #     print(f"  Benchmark comparison: {comparison_counts['benchmark']}")
    #     print(f"  Combined: {comparison_counts['both']}")
        
    #     priority_counts = {
    #         'high': len([i for i in insights if i.get('priority') == 'high']),
    #         'medium': len([i for i in insights if i.get('priority') == 'medium']),
    #         'low': len([i for i in insights if i.get('priority') == 'low'])
    #     }
        
    #     print(f"\nPriority breakdown:")
    #     print(f"  High: {priority_counts['high']}")
    #     print(f"  Medium: {priority_counts['medium']}")
    #     print(f"  Low: {priority_counts['low']}")
        
    #     # Create processed output
    #     processed = {
    #         'entity_type': entity_type,
    #         'entity_id': entity_id,
    #         'generated_at': datetime.now().isoformat(),
    #         'dashboard_period': dashboard_data['parameters'],
    #         'insights': insights,
    #         'insights_count': len(insights),
    #         'high_priority_count': priority_counts['high'],
    #         'comparison_types': comparison_counts,
    #         'source_dashboard_file': dashboard_raw_filepath,
    #         'total_data_version': total_data.get('generated_at'),
    #         'has_historical_data': entity_total is not None and len(entity_total) > 0
    #     }
        
    #     # Save
    #     output_filepath = self.save_insights(entity_type, entity_id, processed)
        
    #     return output_filepath
    
    
    def generate_insights(self, dashboard_raw_filepath):
        """Generate insights by comparing dashboard vs total data"""
        print(f"\n{'='*60}")
        print(f"Generating Benchmarked Insights")
        print(f"{'='*60}")
        print(f"Processing: {dashboard_raw_filepath}")
        
        # Load dashboard data
        dashboard_data = self.load_dashboard_raw(dashboard_raw_filepath)
        entity_type = dashboard_data['entity_type']
        entity_id = dashboard_data['entity_id']
        
        print(f"\nEntity: {entity_type.upper()} {entity_id}")
        print(f"Dashboard Period: {dashboard_data['parameters']['start_date']} to {dashboard_data['parameters']['end_date']}")
        
        # Load entity's historical data from SQLite DATABASE (FAST!)
        print(f"\nLoading historical data for {entity_type} {entity_id} from DuckDB...")
        entity_total = self.load_entity_from_duckdb(entity_type, entity_id)
        
        if not entity_total:
            print(f"⚠ Warning: No historical data found for {entity_type} {entity_id}")
            print(f"   Insights will be limited to current period analysis only")
            entity_total = {}
        else:
            print(f"✓ Loaded historical data ({len(entity_total)} queries)")
        
        # Load platform aggregates (cached after first load)
        print(f"Loading platform aggregates...")
        aggregates_data = self.load_aggregates_from_duckdb(entity_type)
        aggregates = aggregates_data
        
        print(f"✓ Loaded platform aggregates ({aggregates.get('total_count', 0)} {entity_type}s)")
        
        # Format data for LLM
        formatted_dashboard = {
            'parameters': dashboard_data['parameters'],
            'queries': dashboard_data['queries']
        }
        
        # Generate insights based on entity type
        print(f"\nGenerating insights with LLM...")
        if entity_type == 'buyer':
            insights = self.generate_buyer_insights(formatted_dashboard, entity_total, aggregates)
        else:  # seller
            insights = self.generate_seller_insights(formatted_dashboard, entity_total, aggregates)
        
        print(f"✓ Generated {len(insights)} insights")
        
        # Count comparison types
        comparison_counts = {
            'self': len([i for i in insights if i.get('comparison_type') == 'self']),
            'benchmark': len([i for i in insights if i.get('comparison_type') == 'benchmark']),
            'both': len([i for i in insights if i.get('comparison_type') == 'both'])
        }
        
        print(f"\nInsight breakdown:")
        print(f"  Self-comparison: {comparison_counts['self']}")
        print(f"  Benchmark comparison: {comparison_counts['benchmark']}")
        print(f"  Combined: {comparison_counts['both']}")
        
        priority_counts = {
            'high': len([i for i in insights if i.get('priority') == 'high']),
            'medium': len([i for i in insights if i.get('priority') == 'medium']),
            'low': len([i for i in insights if i.get('priority') == 'low'])
        }
        
        print(f"\nPriority breakdown:")
        print(f"  High: {priority_counts['high']}")
        print(f"  Medium: {priority_counts['medium']}")
        print(f"  Low: {priority_counts['low']}")
        
        # Create processed output
        processed = {
            'entity_type': entity_type,
            'entity_id': entity_id,
            'generated_at': datetime.now().isoformat(),
            'dashboard_period': dashboard_data['parameters'],
            'insights': insights,
            'insights_count': len(insights),
            'high_priority_count': priority_counts['high'],
            'comparison_types': comparison_counts,
            'source_dashboard_file': dashboard_raw_filepath,
            'total_data_version': aggregates_data.get('generated_at'),
            'has_historical_data': entity_total is not None and len(entity_total) > 0
        }
        
        # Save
        output_filepath = self.save_insights(entity_type, entity_id, processed)
        
        return output_filepath
    
    
    def save_insights(self, entity_type, entity_id, processed_data):
        """Save processed insights to JSON file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{entity_type}_{entity_id}_insights_{timestamp}.json"
        filepath = os.path.join(config.DASHBOARD_PROCESSED_DIR, filename)
        
        # Ensure directory exists
        os.makedirs(config.DASHBOARD_PROCESSED_DIR, exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(processed_data, f, indent=2)
        
        print(f"\n✓ Saved insights to: {filepath}")
        
        return filepath
    
    def process_all_dashboard_raw(self, entity_type=None):
        """Process all dashboard raw files"""
        pattern = f"{entity_type}_*_dashboard_*.json" if entity_type else "*_dashboard_*.json"
        files = list(Path(config.DASHBOARD_RAW_DIR).glob(pattern))
        
        print(f"\n{'='*60}")
        print(f"Processing All Dashboard Raw Files")
        print(f"{'='*60}")
        print(f"\nFound {len(files)} dashboard raw files")
        
        if not files:
            print("No dashboard raw files found. Run dashboard_executor.py first.")
            return []
        
        processed_files = []
        errors = []
        
        for i, filepath in enumerate(files, 1):
            print(f"\n{'='*60}")
            print(f"File {i}/{len(files)}")
            print(f"{'='*60}")
            
            try:
                output_file = self.generate_insights(str(filepath))
                processed_files.append(output_file)
            except Exception as e:
                print(f"\n✗ Error processing {filepath.name}: {e}")
                errors.append((filepath.name, str(e)))
                continue
        
        # Summary
        print(f"\n{'='*60}")
        print(f"PROCESSING COMPLETE")
        print(f"{'='*60}")
        print(f"Successfully processed: {len(processed_files)}/{len(files)}")
        print(f"Errors: {len(errors)}")
        
        if errors:
            print("\nFailed files:")
            for filename, error in errors:
                print(f"  - {filename}: {error}")
        
        return processed_files


def main():
    parser = argparse.ArgumentParser(
        description='Generate benchmarked insights from dashboard data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process single dashboard raw file
  python insights_generator.py --file data/dashboard_data/raw/buyer_5098_dashboard_20260212.json
  
  # Process all buyer dashboard files
  python insights_generator.py --all --entity buyer
  
  # Process all dashboard files (buyers + sellers)
  python insights_generator.py --all
        """
    )
    
    parser.add_argument(
        '--file',
        help='Specific dashboard raw data file to process'
    )
    
    parser.add_argument(
        '--all',
        action='store_true',
        help='Process all dashboard raw files'
    )
    
    parser.add_argument(
        '--entity',
        choices=['buyer', 'seller'],
        help='Filter by entity type (use with --all)'
    )
    
    args = parser.parse_args()
    
    generator = BenchmarkingInsightsGenerator()
    
    if args.file:
        generator.generate_insights(args.file)
    elif args.all:
        generator.process_all_dashboard_raw(args.entity)
    else:
        print("Error: Specify either --file or --all")
        parser.print_help()


if __name__ == '__main__':
    main()