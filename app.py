#!/usr/bin/env python3
import os
import sys
import argparse
import logging

from models import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description='PDF Processing API')
    parser.add_argument('--async-mode', action='store_true', help='Run with async processing enabled')
    parser.add_argument('--port', type=int, default=5000, help='Port to run the server on')
    parser.add_argument('--host', default='0.0.0.0', help='Host to run the server on')
    parser.add_argument('--init-db', action='store_true', help='Initialize database')
    
    args = parser.parse_args()
    
    # Initialize database
    if args.init_db or not os.path.exists('pdf_processor.db'):
        logger.info("Initializing database...")
        init_db()
        logger.info("Database initialized successfully")
        if args.init_db:
            return
    
    # Import and create app based on mode
    if args.async_mode:
        logger.info("Starting Flask app with async processing enabled")
        from api_async import create_async_app
        app = create_async_app()
    else:
        logger.info("Starting Flask app with synchronous processing")
        from api import create_app
        app = create_app()
    
    # Run the app
    app.run(host=args.host, port=args.port, debug=True)

if __name__ == '__main__':
    main()

# For deployment - create app instance for gunicorn
app = create_app()
# Initialize database on startup
from models import init_db
init_db()