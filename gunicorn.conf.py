"""
Gunicorn configuration file for production
"""
import multiprocessing
import os

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
# Worker processes
# Formula: (2 x CPUs) + 1 is recommendation, but with threads we can be more conservative
workers = 3  # Assuming 1-2 core environment, safe default
worker_class = "gthread"
threads = 4
worker_connections = 1000
timeout = 30
keepalive = 2

# Memory leak prevention
max_requests = 1000
max_requests_jitter = 50

# Logging
accesslog = "/app/logs/gunicorn_access.log"
errorlog = "/app/logs/gunicorn_error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = "ticket_system"

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (if terminating SSL at gunicorn instead of nginx)
# keyfile = None
# certfile = None

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190
