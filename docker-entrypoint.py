#!/usr/bin/env python
import os
import sys
import subprocess

# Get PORT from environment, default to 8080
port = os.environ.get('PORT', '8080')

# Build the gunicorn command
cmd = [
    'gunicorn',
    'app:app',
    '--bind', f'0.0.0.0:{port}',
    '--workers', '1',
    '--threads', '8',
    '--timeout', '0'
]

print(f"Starting server on port {port}...")
print(f"Command: {' '.join(cmd)}")

# Execute gunicorn
subprocess.run(cmd)