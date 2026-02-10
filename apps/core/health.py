"""
Health check view for monitoring
"""
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
import sys

def health_check(request):
    """
    Health check endpoint for Docker and monitoring
    Returns 200 if all systems are operational
    """
    status = {
        'status': 'healthy',
        'checks': {}
    }
    
    # Check database connection
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        status['checks']['database'] = 'ok'
    except Exception as e:
        status['status'] = 'unhealthy'
        status['checks']['database'] = f'error: {str(e)}'
    
    # Check cache connection
    try:
        cache.set('health_check', 'ok', 10)
        cache_value = cache.get('health_check')
        if cache_value == 'ok':
            status['checks']['cache'] = 'ok'
        else:
            status['checks']['cache'] = 'error: cache not working'
            status['status'] = 'unhealthy'
    except Exception as e:
        status['checks']['cache'] = f'error: {str(e)}'
        status['status'] = 'unhealthy'
    
    # Python version
    status['python_version'] = sys.version
    
    # Return appropriate status code
    status_code = 200 if status['status'] == 'healthy' else 503
    
    return JsonResponse(status, status=status_code)
