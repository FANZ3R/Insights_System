"""
Insights Generator: Reads raw query data and generates AI-powered insights
"""

import json
import os
import argparse
from datetime import datetime
from pathlib import Path
from openai import OpenAI
import config

class InsightsGenerator:
    def __init__(self, api_key=None):
        self.api_key = api_key or config.OPENROUTER_API_KEY
        self.client = OpenAI(
            base_url=config.OPENROUTER_BASE_URL,
            api_key=self.api_key
        )
    
    def load_raw_data(self, filepath):
        """Load raw data from JSON file"""
        with open(filepath, 'r') as f:
            return json.load(f)
    
    def get_latest_raw_file(self, entity_type, entity_id):
        """Get the most recent raw data file for an entity"""
        pattern = f"{entity_type}_{entity_id}_*.json"
        files = list(Path(config.RAW_DATA_DIR).glob(pattern))
        
        if not files:
            return None
        
        # Sort by modification time, get most recent
        latest_file = max(files, key=lambda f: f.stat().st_mtime)
        return str(latest_file)
    
    def format_data_for_llm(self, raw_data):
        """Format raw query data for LLM consumption"""
        entity_type = raw_data['entity_type']
        entity_id = raw_data['entity_id']
        
        formatted = {
            'entity_type': entity_type,
            'entity_id': entity_id,
            'period': {
                'start': raw_data['parameters'].get('start_date'),
                'end': raw_data['parameters'].get('end_date')
            },
            'data': {}
        }
        
        # Extract and organize query results
        for query_name, query_result in raw_data['queries'].items():
            if query_result.get('data'):
                formatted['data'][query_name] = query_result['data']
        
        return formatted
    
    def generate_buyer_insights(self, data):
        """Generate insights for buyer data"""
        prompt = f"""
You are a procurement analytics expert. Analyze this buyer's purchasing data and provide actionable insights.

BUYER DATA:
{json.dumps(data, indent=2)}

Provide 3-5 high-priority insights in the following JSON format:
{{
  "insights": [
    {{
      "title": "Brief insight title",
      "observation": "What the data shows",
      "recommendation": "Specific actionable recommendation",
      "priority": "high|medium|low",
      "metrics": ["relevant metric names from the data"]
    }}
  ]
}}

Focus on:
1. Spending patterns and efficiency (price per unit trends, supplier concentration)
2. Supplier diversity and risk (new vs existing suppliers, concentration risk)
3. Procurement growth (period-over-period changes)
4. Category performance (which categories show growth or decline)
5. Cost optimization opportunities

Respond ONLY with valid JSON, no additional text.
"""
        
        response = self.client.chat.completions.create(
            model=config.DEFAULT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        
        insights_text = response.choices[0].message.content.strip()
        
        # Parse JSON response
        try:
            # Remove markdown code blocks if present
            if insights_text.startswith('```'):
                insights_text = insights_text.split('```')[1]
                if insights_text.startswith('json'):
                    insights_text = insights_text[4:]
            
            insights = json.loads(insights_text)
            return insights.get('insights', [])
        except json.JSONDecodeError as e:
            print(f"Error parsing LLM response: {e}")
            print(f"Raw response: {insights_text}")
            return []
    
    def generate_seller_insights(self, data):
        """Generate insights for seller data"""
        prompt = f"""
You are a sales analytics expert. Analyze this seller's performance data and provide actionable insights.

SELLER DATA:
{json.dumps(data, indent=2)}

Provide 3-5 high-priority insights in the following JSON format:
{{
  "insights": [
    {{
      "title": "Brief insight title",
      "observation": "What the data shows",
      "recommendation": "Specific actionable recommendation",
      "priority": "high|medium|low",
      "metrics": ["relevant metric names from the data"]
    }}
  ]
}}

Focus on:
1. Revenue trends (month-over-month, quarter-over-quarter growth)
2. Customer retention (repeat purchase rate, customer loyalty)
3. Product performance (top sellers, revenue concentration)
4. Sales efficiency (average order value, units per order)
5. Growth opportunities (regional expansion, product diversification)

Respond ONLY with valid JSON, no additional text.
"""
        
        response = self.client.chat.completions.create(
            model=config.DEFAULT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        
        insights_text = response.choices[0].message.content.strip()
        
        # Parse JSON response
        try:
            # Remove markdown code blocks if present
            if insights_text.startswith('```'):
                insights_text = insights_text.split('```')[1]
                if insights_text.startswith('json'):
                    insights_text = insights_text[4:]
            
            insights = json.loads(insights_text)
            return insights.get('insights', [])
        except json.JSONDecodeError as e:
            print(f"Error parsing LLM response: {e}")
            print(f"Raw response: {insights_text}")
            return []
    
    def generate_insights(self, raw_data):
        """Generate insights based on entity type"""
        formatted_data = self.format_data_for_llm(raw_data)
        
        entity_type = raw_data['entity_type']
        
        if entity_type == 'buyer':
            insights = self.generate_buyer_insights(formatted_data)
        else:  # seller
            insights = self.generate_seller_insights(formatted_data)
        
        return insights
    
    def create_processed_output(self, raw_data, insights):
        """Create final processed output with metadata and insights"""
        return {
            'entity_type': raw_data['entity_type'],
            'entity_id': raw_data['entity_id'],
            'generated_at': datetime.now().isoformat(),
            'data_period': {
                'start': raw_data['parameters'].get('start_date'),
                'end': raw_data['parameters'].get('end_date')
            },
            'raw_data_summary': {
                query_name: {
                    'description': query_result.get('description'),
                    'result_count': query_result.get('result_count', 0)
                }
                for query_name, query_result in raw_data['queries'].items()
            },
            'insights': insights,
            'insights_count': len(insights),
            'high_priority_count': len([i for i in insights if i.get('priority') == 'high']),
            'source_file': raw_data.get('source_file', 'unknown')
        }
    
    def save_processed_data(self, entity_type, entity_id, processed_data):
        """Save processed insights to JSON file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{entity_type}_{entity_id}_insights_{timestamp}.json"
        filepath = os.path.join(config.PROCESSED_DATA_DIR, filename)
        
        with open(filepath, 'w') as f:
            json.dump(processed_data, f, indent=2)
        
        print(f"\n✓ Saved insights to: {filepath}")
        return filepath
    
    def process_raw_file(self, filepath):
        """Process a raw data file and generate insights"""
        print(f"\nProcessing: {filepath}")
        
        # Load raw data
        raw_data = self.load_raw_data(filepath)
        raw_data['source_file'] = filepath
        
        entity_type = raw_data['entity_type']
        entity_id = raw_data['entity_id']
        
        print(f"Generating insights for {entity_type} {entity_id}...")
        
        # Generate insights
        insights = self.generate_insights(raw_data)
        
        print(f"  ✓ Generated {len(insights)} insights")
        
        # Create processed output
        processed_data = self.create_processed_output(raw_data, insights)
        
        # Save processed data
        output_file = self.save_processed_data(entity_type, entity_id, processed_data)
        
        return output_file
    
    def process_entity(self, entity_type, entity_id):
        """Process the latest raw data for an entity"""
        filepath = self.get_latest_raw_file(entity_type, entity_id)
        
        if not filepath:
            print(f"No raw data found for {entity_type} {entity_id}")
            return None
        
        return self.process_raw_file(filepath)
    
    def process_all_raw_files(self, entity_type=None):
        """Process all raw data files"""
        pattern = f"{entity_type}_*.json" if entity_type else "*.json"
        files = list(Path(config.RAW_DATA_DIR).glob(pattern))
        
        print(f"\nFound {len(files)} raw data files to process")
        
        processed_files = []
        for i, filepath in enumerate(files, 1):
            print(f"\nProcessing {i}/{len(files)}...")
            try:
                output_file = self.process_raw_file(str(filepath))
                processed_files.append(output_file)
            except Exception as e:
                print(f"Error processing {filepath}: {e}")
                continue
        
        print(f"\n{'='*60}")
        print(f"Completed: {len(processed_files)}/{len(files)} files processed")
        print(f"{'='*60}")
        
        return processed_files


def main():
    parser = argparse.ArgumentParser(description='Generate AI insights from raw data')
    parser.add_argument('--entity', choices=['buyer', 'seller'],
                       help='Entity type to process')
    parser.add_argument('--id', type=int, help='Specific entity ID to process')
    parser.add_argument('--file', help='Specific raw data file to process')
    parser.add_argument('--all', action='store_true', help='Process all raw data files')
    
    args = parser.parse_args()
    
    generator = InsightsGenerator()
    
    if args.file:
        generator.process_raw_file(args.file)
    elif args.id and args.entity:
        generator.process_entity(args.entity, args.id)
    elif args.all:
        generator.process_all_raw_files(args.entity)
    else:
        print("Error: Specify --file, (--entity and --id), or --all")
        parser.print_help()


if __name__ == '__main__':
    main()