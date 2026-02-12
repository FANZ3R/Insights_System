"""
Query Parser: Extract and label individual queries from multi-query SQL files
"""

import re

class QueryParser:
    def __init__(self):
        self.query_separator = ';'
    
    def parse_file(self, filepath):
        """
        Parse SQL file containing multiple queries separated by semicolons
        Returns list of {name, query, description} dicts
        """
        with open(filepath, 'r') as f:
            content = f.read()
        
        queries = []
        current_query = []
        current_name = None
        current_description = None
        
        for line in content.split('\n'):
            stripped = line.strip()
            
            # Check for query name marker (-- @name: query_name)
            name_match = re.match(r'--\s*@name:\s*(.+)', stripped, re.IGNORECASE)
            if name_match:
                current_name = name_match.group(1).strip()
                continue
            
            # Check for query description (-- @description: text)
            desc_match = re.match(r'--\s*@description:\s*(.+)', stripped, re.IGNORECASE)
            if desc_match:
                current_description = desc_match.group(1).strip()
                continue
            
            # Collect query lines
            current_query.append(line)
            
            # Check if query ends with semicolon
            if stripped.endswith(';'):
                query_text = '\n'.join(current_query).strip()
                
                # Remove trailing semicolon
                if query_text.endswith(';'):
                    query_text = query_text[:-1].strip()
                
                # Only add non-empty queries
                if query_text and not query_text.startswith('--'):
                    queries.append({
                        'name': current_name or f'query_{len(queries) + 1}',
                        'description': current_description or 'No description',
                        'query': query_text
                    })
                
                # Reset for next query
                current_query = []
                current_name = None
                current_description = None
        
        return queries
    
    def extract_parameters(self, query):
        """Extract parameter placeholders from query"""
        # Find all %(param_name)s patterns
        params = re.findall(r'%\(([^)]+)\)', query)
        return list(set(params))  # Remove duplicates