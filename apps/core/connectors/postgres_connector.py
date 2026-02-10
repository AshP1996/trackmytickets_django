"""
PostgreSQL Database Connector
"""
import psycopg2
import psycopg2.extras
from typing import List, Dict, Any, Optional
from .base import DatabaseConnector

class PostgreSQLConnector(DatabaseConnector):
    """
    Connector for PostgreSQL databases
    """
    
    def test_connection(self) -> Dict[str, Any]:
        """Test PostgreSQL database connection"""
        try:
            conn_params = {
                'host': self.config.get('host'),
                'port': self.config.get('port', 5432),
                'database': self.config.get('database'),
                'user': self.config.get('username'),
                'password': self.config.get('password')
            }
            
            if self.config.get('ssl_enabled'):
                conn_params['sslmode'] = 'require'
            
            conn = psycopg2.connect(**conn_params)
            cursor = conn.cursor()
            
            # Get PostgreSQL version
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            
            # Count tables
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            table_count = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'success': True,
                'message': 'Successfully connected to PostgreSQL database',
                'details': {
                    'version': version.split(',')[0],
                    'table_count': table_count,
                    'host': self.config.get('host'),
                    'database': self.config.get('database')
                }
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Connection failed: {str(e)}',
                'details': {'error': str(e)}
            }
    
    def get_tables(self) -> List[str]:
        """Get list of tables in PostgreSQL database"""
        try:
            conn = psycopg2.connect(
                host=self.config.get('host'),
                port=self.config.get('port', 5432),
                database=self.config.get('database'),
                user=self.config.get('username'),
                password=self.config.get('password')
            )
            cursor = conn.cursor()
            cursor.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            """)
            tables = [row[0] for row in cursor.fetchall()]
            conn.close()
            return tables
        except Exception as e:
            print(f"Error getting tables: {e}")
            return []
    
    def get_schema(self, table_name: str) -> List[Dict[str, Any]]:
        """Get schema for a PostgreSQL table"""
        try:
            conn = psycopg2.connect(
                host=self.config.get('host'),
                port=self.config.get('port', 5432),
                database=self.config.get('database'),
                user=self.config.get('username'),
                password=self.config.get('password')
            )
            cursor = conn.cursor()
            cursor.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = %s
                ORDER BY ordinal_position
            """, (table_name,))
            
            columns = []
            for row in cursor.fetchall():
                columns.append({
                    'name': row[0],
                    'type': row[1],
                    'nullable': row[2] == 'YES',
                    'default': row[3]
                })
            conn.close()
            return columns
        except Exception as e:
            print(f"Error getting schema: {e}")
            return []
    
    def fetch_data(self, query: str, params: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Execute query and fetch data from PostgreSQL"""
        try:
            conn = psycopg2.connect(
                host=self.config.get('host'),
                port=self.config.get('port', 5432),
                database=self.config.get('database'),
                user=self.config.get('username'),
                password=self.config.get('password')
            )
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
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
        """Close connection"""
        if self.connection:
            self.connection.close()
