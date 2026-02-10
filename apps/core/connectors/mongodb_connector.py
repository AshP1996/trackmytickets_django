"""
MongoDB Database Connector
"""
from pymongo import MongoClient
from typing import List, Dict, Any, Optional
from .base import DatabaseConnector

class MongoDBConnector(DatabaseConnector):
    """
    Connector for MongoDB databases
    """
    
    def test_connection(self) -> Dict[str, Any]:
        """Test MongoDB database connection"""
        try:
            # Build connection string
            if self.config.get('username') and self.config.get('password'):
                conn_string = f"mongodb://{self.config.get('username')}:{self.config.get('password')}@{self.config.get('host')}:{self.config.get('port', 27017)}"
            else:
                conn_string = f"mongodb://{self.config.get('host')}:{self.config.get('port', 27017)}"
            
            if self.config.get('ssl_enabled'):
                conn_string += "?ssl=true"
            
            client = MongoClient(conn_string, serverSelectionTimeoutMS=5000)
            
            # Test connection
            client.server_info()
            
            # Get database
            db = client[self.config.get('database')]
            
            # Count collections
            collection_count = len(db.list_collection_names())
            
            # Get server info
            server_info = client.server_info()
            
            client.close()
            
            return {
                'success': True,
                'message': 'Successfully connected to MongoDB database',
                'details': {
                    'version': server_info.get('version'),
                    'collection_count': collection_count,
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
        """Get list of collections in MongoDB database"""
        try:
            if self.config.get('username') and self.config.get('password'):
                conn_string = f"mongodb://{self.config.get('username')}:{self.config.get('password')}@{self.config.get('host')}:{self.config.get('port', 27017)}"
            else:
                conn_string = f"mongodb://{self.config.get('host')}:{self.config.get('port', 27017)}"
            
            client = MongoClient(conn_string)
            db = client[self.config.get('database')]
            collections = db.list_collection_names()
            client.close()
            return collections
        except Exception as e:
            print(f"Error getting collections: {e}")
            return []
    
    def get_schema(self, table_name: str) -> List[Dict[str, Any]]:
        """Get schema for a MongoDB collection (sample-based)"""
        try:
            if self.config.get('username') and self.config.get('password'):
                conn_string = f"mongodb://{self.config.get('username')}:{self.config.get('password')}@{self.config.get('host')}:{self.config.get('port', 27017)}"
            else:
                conn_string = f"mongodb://{self.config.get('host')}:{self.config.get('port', 27017)}"
            
            client = MongoClient(conn_string)
            db = client[self.config.get('database')]
            collection = db[table_name]
            
            # Sample a document to infer schema
            sample = collection.find_one()
            
            columns = []
            if sample:
                for key, value in sample.items():
                    columns.append({
                        'name': key,
                        'type': type(value).__name__,
                        'nullable': True,  # MongoDB fields are inherently nullable
                        'default': None
                    })
            
            client.close()
            return columns
        except Exception as e:
            print(f"Error getting schema: {e}")
            return []
    
    def fetch_data(self, query: str, params: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Fetch data from MongoDB (query should be a dict filter)"""
        try:
            if self.config.get('username') and self.config.get('password'):
                conn_string = f"mongodb://{self.config.get('username')}:{self.config.get('password')}@{self.config.get('host')}:{self.config.get('port', 27017)}"
            else:
                conn_string = f"mongodb://{self.config.get('host')}:{self.config.get('port', 27017)}"
            
            client = MongoClient(conn_string)
            db = client[self.config.get('database')]
            
            # For MongoDB, query should be collection_name:filter_dict format
            # This is a simplified implementation
            collection_name = params.get('collection') if params else query
            filter_dict = params.get('filter', {}) if params else {}
            
            collection = db[collection_name]
            documents = list(collection.find(filter_dict))
            
            # Convert ObjectId to string
            for doc in documents:
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
            
            client.close()
            return documents
        except Exception as e:
            print(f"Error fetching data: {e}")
            return []
    
    def close(self):
        """Close connection"""
        if self.connection:
            self.connection.close()
