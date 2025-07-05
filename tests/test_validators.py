import pytest
from flask import Flask, request
from validators import validate_job_id, validate_file_upload
from werkzeug.datastructures import FileStorage
from io import BytesIO


class TestValidators:
    def test_validate_job_id_valid(self):
        """Test valid UUID format"""
        app = Flask(__name__)
        
        @app.route('/test/<job_id>')
        @validate_job_id
        def test_route(job_id):
            return {'job_id': job_id}, 200
        
        with app.test_client() as client:
            response = client.get('/test/123e4567-e89b-12d3-a456-426614174000')
            assert response.status_code == 200
            assert response.json['job_id'] == '123e4567-e89b-12d3-a456-426614174000'
    
    def test_validate_job_id_invalid(self):
        """Test invalid UUID format"""
        app = Flask(__name__)
        
        @app.route('/test/<job_id>')
        @validate_job_id
        def test_route(job_id):
            return {'job_id': job_id}, 200
        
        with app.test_client() as client:
            # Test various invalid formats
            invalid_ids = [
                'invalid-id',
                '123',
                '123e4567-e89b-12d3-a456',  # Too short
                '123e4567-e89b-12d3-a456-426614174000-extra',  # Too long
                'gggggggg-gggg-gggg-gggg-gggggggggggg',  # Invalid characters
            ]
            
            for invalid_id in invalid_ids:
                response = client.get(f'/test/{invalid_id}')
                assert response.status_code == 400
                assert 'Invalid job ID format' in response.json['error']
    
    def test_validate_file_upload_valid(self):
        """Test valid file upload"""
        app = Flask(__name__)
        
        with app.test_request_context(
            method='POST',
            data={'file': (BytesIO(b'PDF content'), 'test.pdf')}
        ):
            errors = validate_file_upload(request)
            assert errors == []
    
    def test_validate_file_upload_no_file(self):
        """Test upload with no file"""
        app = Flask(__name__)
        
        with app.test_request_context(method='POST'):
            errors = validate_file_upload(request)
            assert 'No file part in request' in errors
    
    def test_validate_file_upload_empty_filename(self):
        """Test upload with empty filename"""
        app = Flask(__name__)
        
        with app.test_request_context(
            method='POST',
            data={'file': (BytesIO(b''), '')}
        ):
            errors = validate_file_upload(request)
            assert 'No file selected' in errors
    
    def test_validate_file_upload_invalid_type(self):
        """Test upload with non-PDF file"""
        app = Flask(__name__)
        
        with app.test_request_context(
            method='POST',
            data={'file': (BytesIO(b'Text content'), 'test.txt')}
        ):
            errors = validate_file_upload(request)
            assert 'Invalid file type. Only PDF files are allowed' in errors