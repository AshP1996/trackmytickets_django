"""
Database Connectors Package
"""
from .base import DatabaseConnector, DATABASE_CONFIGS
from .sqlite_connector import SQLiteConnector
from .postgres_connector import PostgreSQLConnector
from .mysql_connector import MySQLConnector
from .mongodb_connector import MongoDBConnector

# Connector factory
def get_connector(db_type: str, config: dict) -> DatabaseConnector:
    """
    Factory function to get the appropriate connector for a database type
    
    Args:
        db_type: Type of database (sqlite, postgres, mysql, mongodb, etc.)
        config: Connection configuration dictionary
        
    Returns:
        DatabaseConnector instance
        
    Raises:
        ValueError: If database type is not supported
    """
    connectors = {
        'sqlite': SQLiteConnector,
        'postgres': PostgreSQLConnector,
        'mysql': MySQLConnector,
        'mariadb': MySQLConnector,  # MariaDB uses same connector as MySQL
        'mongodb': MongoDBConnector,
    }
    
    connector_class = connectors.get(db_type)
    if not connector_class:
        raise ValueError(f"Unsupported database type: {db_type}")
    
    return connector_class(config)

__all__ = [
    'DatabaseConnector',
    'DATABASE_CONFIGS',
    'SQLiteConnector',
    'PostgreSQLConnector',
    'MySQLConnector',
    'MongoDBConnector',
    'get_connector'
]
