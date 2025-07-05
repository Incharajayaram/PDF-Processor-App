import pytest
import json
import tempfile
import os
from api import create_app
from models import init_db, Job
from io import BytesIO


class TestAPI:
    @pytest.fixture
    def app(self, monkeypatch):
        """Create test Flask app"""
        # Create temporary database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        db_url = f'sqlite:///{db_path}'
        
        # Monkey patch the get_session function to use test database
        from models import init_db
        from sqlalchemy.orm import close_all_sessions
        
        test_session_factory = init_db(db_url)
        
        def mock_get_session():
            return test_session_factory()
        
        monkeypatch.setattr('models.get_session', mock_get_session)
        monkeypatch.setattr('api.get_session', mock_get_session)
        
        app = create_app()
        app.config['TESTING'] = True
        
        yield app
        
        # Close all sessions before cleanup
        close_all_sessions()
        
        # Force garbage collection to release file handles
        import gc
        gc.collect()
        
        # Try to remove the file, ignore errors on Windows
        try:
            os.unlink(db_path)
        except PermissionError:
            pass  # Windows sometimes holds the file open
    
    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return app.test_client()
    
    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get('/health')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'healthy'
        assert 'timestamp' in data
    
    def test_upload_document_no_file(self, client):
        """Test upload with no file"""
        response = client.post('/api/documents/upload')
        assert response.status_code == 400
        data = response.get_json()
        assert 'No file part in request' in data['error']
    
    def test_upload_document_empty_filename(self, client):
        """Test upload with empty filename"""
        response = client.post(
            '/api/documents/upload',
            data={'file': (BytesIO(b''), '')}
        )
        assert response.status_code == 400
        data = response.get_json()
        assert 'No file selected' in data['error']
    
    def test_upload_document_invalid_type(self, client):
        """Test upload with non-PDF file"""
        response = client.post(
            '/api/documents/upload',
            data={'file': (BytesIO(b'text content'), 'test.txt')}
        )
        assert response.status_code == 400
        data = response.get_json()
        assert 'Invalid file type' in data['error']
    
    def test_upload_document_success(self, client, mocker, monkeypatch):
        """Test successful document upload"""
        # Create temporary directory for uploads
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            # Mock the PDFProcessor class before the app creates it
            mock_pdf_processor = mocker.Mock()
            mock_pdf_processor.save_uploaded_file.return_value = os.path.join(tmpdir, 'test.pdf')
            mock_pdf_processor.process_pdf.return_value = 'Sample PDF text content'
            
            # Mock the LLMService class  
            mock_llm_service = mocker.Mock()
            mock_llm_service.extract_company_name.return_value = 'Test Company'
            
            # Mock the GitHubService class
            mock_github_service = mocker.Mock()
            mock_github_service.get_organization_info.return_value = {'name': 'test-org'}
            mock_github_service.get_organization_members.return_value = ['user1', 'user2']
            
            # Patch the classes at import time
            monkeypatch.setattr('api.PDFProcessor', lambda *args, **kwargs: mock_pdf_processor)
            monkeypatch.setattr('api.LLMService', lambda *args, **kwargs: mock_llm_service)
            monkeypatch.setattr('api.GitHubService', lambda *args, **kwargs: mock_github_service)
            
            # Re-create the app with mocked services
            from api import create_app
            test_app = create_app()
            test_client = test_app.test_client()
            
            response = test_client.post(
                '/api/documents/upload',
                data={'file': (BytesIO(b'PDF content'), 'test.pdf')},
                content_type='multipart/form-data'
            )
            
            assert response.status_code == 201
            data = response.get_json()
            assert 'job_id' in data
            assert data['status'] in ['pending', 'processing', 'completed']
    
    def test_get_job_status_invalid_id(self, client):
        """Test status check with invalid job ID"""
        response = client.get('/api/documents/status/invalid-id')
        assert response.status_code == 400
        data = response.get_json()
        assert 'Invalid job ID format' in data['error']
    
    def test_get_job_status_not_found(self, client):
        """Test status check for non-existent job"""
        response = client.get('/api/documents/status/123e4567-e89b-12d3-a456-426614174000')
        assert response.status_code == 404
        data = response.get_json()
        assert 'Job not found' in data['error']
    
    def test_get_job_status_success(self, client, app):
        """Test successful status check"""
        # Create a job in the database
        from models import get_session, Job
        session = get_session()
        job = Job(
            job_id='123e4567-e89b-12d3-a456-426614174000',
            pdf_filename='test.pdf',
            status='completed',
            company_name='Test Company',
            github_org_data='{"name": "test-org"}',
            github_members='["user1", "user2"]'
        )
        session.add(job)
        session.commit()
        session.close()
        
        response = client.get('/api/documents/status/123e4567-e89b-12d3-a456-426614174000')
        assert response.status_code == 200
        data = response.get_json()
        assert data['job_id'] == '123e4567-e89b-12d3-a456-426614174000'
        assert data['status'] == 'completed'
        assert data['company_name'] == 'Test Company'
        assert data['github_org_data']['name'] == 'test-org'
        assert data['github_members'] == ['user1', 'user2']
        assert data['members_count'] == 2
    
    def test_list_documents(self, client, app):
        """Test listing all documents"""
        # Create some jobs
        from models import get_session, Job
        session = get_session()
        
        for i in range(3):
            job = Job(
                pdf_filename=f'test{i}.pdf',
                status='completed',
                company_name=f'Company {i}'
            )
            session.add(job)
        
        session.commit()
        session.close()
        
        response = client.get('/api/documents')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['documents']) == 3
        # API doesn't return 'total' field, only 'documents'