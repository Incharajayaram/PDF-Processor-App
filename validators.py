import re
from functools import wraps
from flask import jsonify

def validate_job_id(func):
    """decorator to validate job_id format (UUID)"""
    @wraps(func)
    def wrapper(job_id, *args, **kwargs):
        #UUID pattern: 8-4-4-4-12 hexadecimal characters
        uuid_pattern = re.compile(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
            re.IGNORECASE
        )
        
        if not uuid_pattern.match(job_id):
            return jsonify({'error': 'Invalid job ID format'}), 400
        
        return func(job_id, *args, **kwargs)
    
    return wrapper

def validate_file_upload(request):
    """validate file upload request"""
    errors = []
    
    if 'file' not in request.files:
        errors.append('No file part in request')
    else:
        file = request.files['file']
        if file.filename == '':
            errors.append('No file selected')
        elif not file.filename.lower().endswith('.pdf'):
            errors.append('Invalid file type. Only PDF files are allowed')
    
    return errors