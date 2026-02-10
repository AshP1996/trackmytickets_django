"""
Base Database Connector class and configuration
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

# Database configuration
DATABASE_CONFIGS = {
    'sqlite': {
        'name': 'SQLite',
        'default_port': None,
        'icon': 'fa-database',
        'color': '#003B57',
        'requires': ['database'],
        'optional': [],
        'description': 'Lightweight file-based database, perfect for small to medium datasets'
    },
    'postgres': {
        'name': 'PostgreSQL',
        'default_port': 5432,
        'icon': 'fa-elephant',
        'color': '#336791',
        'requires': ['host', 'port', 'database', 'username', 'password'],
        'optional': ['ssl_enabled'],
        'description': 'Powerful open-source relational database'
    },
    'mysql': {
        'name': 'MySQL',
        'default_port': 3306,
        'icon': 'fa-database',
        'color': '#4479A1',
        'requires': ['host', 'port', 'database', 'username', 'password'],
        'optional': ['ssl_enabled'],
        'description': 'Popular open-source relational database'
    },
    'mariadb': {
        'name': 'MariaDB',
        'default_port': 3306,
        'icon': 'fa-database',
        'color': '#003545',
        'requires': ['host', 'port', 'database', 'username', 'password'],
        'optional': ['ssl_enabled'],
        'description': 'MySQL-compatible open-source database'
    },
    'mongodb': {
        'name': 'MongoDB',
        'default_port': 27017,
        'icon': 'fa-leaf',
        'color': '#47A248',
        'requires': ['host', 'port', 'database'],
        'optional': ['username', 'password', 'ssl_enabled'],
        'description': 'NoSQL document database for flexible data models'
    },
    'sqlserver': {
        'name': 'Microsoft SQL Server',
        'default_port': 1433,
        'icon': 'fa-server',
        'color': '#CC2927',
        'requires': ['host', 'port', 'database', 'username', 'password'],
        'optional': ['ssl_enabled'],
        'description': 'Enterprise-grade relational database from Microsoft'
    },
    'oracle': {
        'name': 'Oracle Database',
        'default_port': 1521,
        'icon': 'fa-database',
        'color': '#F80000',
        'requires': ['host', 'port', 'database', 'username', 'password'],
        'optional': [],
        'description': 'Enterprise database solution from Oracle'
    },
    'redis': {
        'name': 'Redis',
        'default_port': 6379,
        'icon': 'fa-bolt',
        'color': '#DC382D',
        'requires': ['host', 'port'],
        'optional': ['password', 'database'],
        'description': 'In-memory data structure store, used as cache or message broker'
    },
}

class DatabaseConnector(ABC):
    """
    Abstract base class for database connectors
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize connector with configuration
        
        Args:
            config: Dictionary containing connection parameters
                   (host, port, database, username, password, etc.)
        """
        self.config = config
        self.connection = None
    
    @abstractmethod
    def test_connection(self) -> Dict[str, Any]:
        """
        Test database connection
        
        Returns:
            Dict with keys: success (bool), message (str), details (dict)
        """
        pass
    
    @abstractmethod
    def get_tables(self) -> List[str]:
        """
        Get list of tables/collections in the database
        
        Returns:
            List of table/collection names
        """
        pass
    
    @abstractmethod
    def get_schema(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Get schema information for a specific table
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of column/field definitions with name, type, nullable, etc.
        """
        pass
    
    @abstractmethod
    def fetch_data(self, query: str, params: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """
        Execute a query and fetch results
        
        Args:
            query: SQL query or equivalent
            params: Optional query parameters
            
        Returns:
            List of rows as dictionaries
        """
        pass
    
    @abstractmethod
    def close(self):
        """
        Close database connection
        """
        pass
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
