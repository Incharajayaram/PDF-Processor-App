import pytest
import tempfile
import os
from datetime import datetime
from models import Job, init_db, get_session
import json


class TestModels:
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        db_url = f'sqlite:///{db_path}'
        init_db(db_url)
        yield db_url
        
        # Close all sessions before cleanup
        from sqlalchemy.orm import close_all_sessions
        close_all_sessions()
        
        # Force garbage collection
        import gc
        gc.collect()
        
        # Try to remove the file, ignore errors on Windows
        try:
            os.unlink(db_path)
        except PermissionError:
            pass  # Windows sometimes holds the file open
    
    def test_job_creation(self, temp_db):
        """Test creating a new job"""
        Session = init_db(temp_db)
        session = Session()
        
        job = Job(
            pdf_filename='test.pdf',
            status='pending'
        )
        session.add(job)
        session.commit()
        
        # Check job was created
        assert job.job_id is not None
        assert len(job.job_id) == 36  # UUID length
        assert job.pdf_filename == 'test.pdf'
        assert job.status == 'pending'
        assert job.timestamp is not None
        
        session.close()
    
    def test_job_to_dict(self, temp_db):
        """Test job serialization to dictionary"""
        Session = init_db(temp_db)
        session = Session()
        
        job = Job(
            pdf_filename='test.pdf',
            company_name='Test Company',
            status='completed',
            github_org_data='{"name": "test-org"}',
            github_members='["user1", "user2"]',
            task_id='celery-task-123'
        )
        session.add(job)
        session.commit()
        
        # Manually set timestamp for consistent testing
        job.timestamp = datetime(2024, 1, 1, 12, 0, 0)
        session.commit()
        
        result = job.to_dict()
        
        assert result['pdf_filename'] == 'test.pdf'
        assert result['company_name'] == 'Test Company'
        assert result['status'] == 'completed'
        assert result['github_org_data'] == '{"name": "test-org"}'
        assert result['github_members'] == '["user1", "user2"]'
        assert result['task_id'] == 'celery-task-123'
        assert result['timestamp'] == '2024-01-01T12:00:00'
        
        session.close()
    
    def test_job_update(self, temp_db):
        """Test updating job status and data"""
        Session = init_db(temp_db)
        session = Session()
        
        # Create job
        job = Job(pdf_filename='test.pdf', status='pending')
        session.add(job)
        session.commit()
        job_id = job.job_id
        
        # Update job
        job.status = 'processing'
        job.company_name = 'GitHub'
        job.task_id = 'task-456'
        session.commit()
        
        # Verify updates
        updated_job = session.query(Job).filter_by(job_id=job_id).first()
        assert updated_job.status == 'processing'
        assert updated_job.company_name == 'GitHub'
        assert updated_job.task_id == 'task-456'
        
        session.close()
    
    def test_job_with_error(self, temp_db):
        """Test job with error message"""
        Session = init_db(temp_db)
        session = Session()
        
        job = Job(
            pdf_filename='test.pdf',
            status='failed',
            error_message='Failed to process PDF'
        )
        session.add(job)
        session.commit()
        
        assert job.status == 'failed'
        assert job.error_message == 'Failed to process PDF'
        
        session.close()