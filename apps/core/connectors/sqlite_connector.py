"""
SQLite Database Connector
"""
import sqlite3
from typing import List, Dict, Any, Optional
from .base import DatabaseConnector

class SQLiteConnector(DatabaseConnector):
    """
    Connector for SQLite databases
    """
    
    def test_connection(self) -> Dict[str, Any]:
        """Test SQLite database connection"""
        try:
            database_path = self.config.get('database')
            if not database_path:
                return {
                    'success': False,
                    'message': 'Database path is required',
                    'details': {}
                }
            
            # Try to connect
            conn = sqlite3.connect(database_path)
            cursor = conn.cursor()
            
            # Get SQLite version
            cursor.execute("SELECT sqlite_version()")
            version = cursor.fetchone()[0]
            
            # Count tables
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            table_count = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'success': True,
                'message': f'Successfully connected to SQLite database',
                'details': {
                    'version': version,
                    'table_count': table_count,
                    'database_path': database_path
                }
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Connection failed: {str(e)}',
                'details': {'error': str(e)}
            }
    
    def get_tables(self) -> List[str]:
        """Get list of tables in SQLite database"""
        try:
            conn = sqlite3.connect(self.config.get('database'))
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            tables = [row[0] for row in cursor.fetchall()]
            conn.close()
            return tables
        except Exception as e:
            print(f"Error getting tables: {e}")
            return []
    
    def get_schema(self, table_name: str) -> List[Dict[str, Any]]:
        """Get schema for a SQLite table"""
        try:
            conn = sqlite3.connect(self.config.get('database'))
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = []
            for row in cursor.fetchall():
                columns.append({
                    'name': row[1],
                    'type': row[2],
                    'nullable': not row[3],
                    'default': row[4],
                    'primary_key': bool(row[5])
                })
            conn.close()
            return columns
        except Exception as e:
            print(f"Error getting schema: {e}")
            return []
    
    def fetch_data(self, query: str, params: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Execute query and fetch data from SQLite"""
        try:
            conn = sqlite3.connect(self.config.get('database'))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            rows = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return rows
        except Exception as e:
            print(f"Error fetching data: {e}")
            return []
    
    def close(self):
        """Close connection (no-op for SQLite as we open/close per operation)"""
        pass
