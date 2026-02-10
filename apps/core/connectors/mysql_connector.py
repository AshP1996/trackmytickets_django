"""
MySQL/MariaDB Database Connector
"""
import pymysql
from typing import List, Dict, Any, Optional
from .base import DatabaseConnector

class MySQLConnector(DatabaseConnector):
    """
    Connector for MySQL and MariaDB databases
    """
    
    def test_connection(self) -> Dict[str, Any]:
        """Test MySQL database connection"""
        try:
            conn_params = {
                'host': self.config.get('host'),
                'port': self.config.get('port', 3306),
                'database': self.config.get('database'),
                'user': self.config.get('username'),
                'password': self.config.get('password')
            }
            
            if self.config.get('ssl_enabled'):
                conn_params['ssl'] = {'ssl': True}
            
            conn = pymysql.connect(**conn_params)
            cursor = conn.cursor()
            
            # Get MySQL version
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()[0]
            
            # Count tables
            cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE()")
            table_count = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'success': True,
                'message': 'Successfully connected to MySQL database',
                'details': {
                    'version': version,
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
        """Get list of tables in MySQL database"""
        try:
            conn = pymysql.connect(
                host=self.config.get('host'),
                port=self.config.get('port', 3306),
                database=self.config.get('database'),
                user=self.config.get('username'),
                password=self.config.get('password')
            )
            cursor = conn.cursor()
            cursor.execute("SHOW TABLES")
            tables = [row[0] for row in cursor.fetchall()]
            conn.close()
            return tables
        except Exception as e:
            print(f"Error getting tables: {e}")
            return []
    
    def get_schema(self, table_name: str) -> List[Dict[str, Any]]:
        """Get schema for a MySQL table"""
        try:
            conn = pymysql.connect(
                host=self.config.get('host'),
                port=self.config.get('port', 3306),
                database=self.config.get('database'),
                user=self.config.get('username'),
                password=self.config.get('password')
            )
            cursor = conn.cursor()
            cursor.execute(f"DESCRIBE {table_name}")
            
            columns = []
            for row in cursor.fetchall():
                columns.append({
                    'name': row[0],
                    'type': row[1],
                    'nullable': row[2] == 'YES',
                    'default': row[4],
                    'primary_key': row[3] == 'PRI'
                })
            conn.close()
            return columns
        except Exception as e:
            print(f"Error getting schema: {e}")
            return []
    
    def fetch_data(self, query: str, params: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Execute query and fetch data from MySQL"""
        try:
            conn = pymysql.connect(
                host=self.config.get('host'),
                port=self.config.get('port', 3306),
                database=self.config.get('database'),
                user=self.config.get('username'),
                password=self.config.get('password'),
                cursorclass=pymysql.cursors.DictCursor
            )
            cursor = conn.cursor()
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            rows = cursor.fetchall()
            conn.close()
            return rows
        except Exception as e:
            print(f"Error fetching data: {e}")
            return []
    
    def close(self):
        """Close connection"""
        if self.connection:
            self.connection.close()
