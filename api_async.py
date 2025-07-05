from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import json
import logging
from datetime import datetime

from config import Config
from models import get_session, Job
from pdf_processor import PDFProcessor
from tasks import process_pdf_async, get_task_status
from validators import validate_job_id, validate_file_upload

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_async_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    CORS(app)
    
    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Initialize services
    pdf_processor = PDFProcessor(app.config['UPLOAD_FOLDER'])
    
    def allowed_file(filename):
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']
    
    @app.route('/')
    def index():
        return render_template('index.html')
    
    @app.route('/health', methods=['GET'])
    def health_check():
        return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()})
    
    @app.route('/api/documents/upload', methods=['POST'])
    def upload_document():
        """Upload a PDF document for async processing"""
        try:
            # Validate file upload
            validation_errors = validate_file_upload(request)
            if validation_errors:
                return jsonify({'error': validation_errors[0]}), 400
            
            file = request.files['file']
            
            # Create new job
            session = get_session()
            if file.filename is None:
                return jsonify({'error': 'No file selected'}), 400
            job = Job(
                pdf_filename=secure_filename(file.filename),
                status='pending'
            )
            session.add(job)
            session.commit()
            
            # Save file
            filename = f"{job.job_id}_{secure_filename(file.filename)}"
            file_path = pdf_processor.save_uploaded_file(file, filename)
            
            # Queue async task
            task = process_pdf_async.delay(job.job_id, file_path)
            
            # Store task ID in job for tracking
            job.task_id = task.id
            session.commit()
            session.close()
            
            return jsonify({
                'job_id': job.job_id,
                'status': 'pending',
                'message': 'File uploaded successfully. Processing queued.',
                'task_id': task.id
            }), 201
            
        except Exception as e:
            logger.error(f"Upload error: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

    @app.route('/api/documents/status/<string:job_id>', methods=['GET'])
    @validate_job_id
    def get_job_status(job_id: str):
        """Get the status of a processing job"""
        try:
            session = get_session()
            job = session.query(Job).filter_by(job_id=job_id).first()
            
            if not job:
                return jsonify({'error': 'Job not found'}), 404
            
            response = {
                'job_id': job.job_id,
                'status': job.status,
                'pdf_filename': job.pdf_filename,
                'timestamp': job.timestamp.isoformat() if getattr(job, 'timestamp', None) is not None else None
            }
            # Check if we have a task_id stored
            if job.task_id is not None:
                task_status = get_task_status(str(job.task_id))
                response['task_status'] = task_status
            if getattr(job, 'status', None) == 'completed':
                response['company_name'] = getattr(job, 'company_name', None)
                github_org_data = getattr(job, 'github_org_data', None)
                github_members = getattr(job, 'github_members', None)
                response['github_org_data'] = json.loads(github_org_data) if github_org_data is not None else None
                if github_members is not None:
                    try:
                        members_list = json.loads(github_members)
                        response['github_members'] = members_list
                        response['members_count'] = len(members_list)
                    except Exception:
                        response['github_members'] = None
                        response['members_count'] = 0
                else:
                    response['github_members'] = None
                    response['members_count'] = 0
            elif getattr(job, 'status', None) == 'failed' and getattr(job, 'error_message', None):
                response['error_message'] = job.error_message

            session.close()
            return jsonify(response), 200
            
        except Exception as e:
            logger.error(f"Status check error: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/documents', methods=['GET'])
    def list_documents():
        """List all processed documents"""
        try:
            session = get_session()
            jobs = session.query(Job).order_by(Job.timestamp.desc()).all()
            
            documents = []
            for job in jobs:
                # Skip jobs with task_id in error_message
                error_message = getattr(job, 'error_message', None)
                if error_message is not None and isinstance(error_message, str) and error_message.startswith('task_id:'):
                    error_msg = None
                else:
                    error_msg = error_message
                
                doc = {
                    'job_id': job.job_id,
                    'pdf_filename': job.pdf_filename,
                    'status': job.status,
                    'timestamp': job.timestamp.isoformat() if getattr(job, 'timestamp', None) is not None else None,
                    'company_name': getattr(job, 'company_name', None)
                }
                
                if error_msg:
                    doc['error_message'] = error_msg
                
                github_members = getattr(job, 'github_members', None)
                if github_members is not None and isinstance(github_members, str):
                    members_list = json.loads(github_members)
                    doc['members_count'] = len(members_list)
                else:
                    doc['members_count'] = 0
                
                documents.append(doc)
            
            session.close()
            return jsonify({'documents': documents}), 200
            
        except Exception as e:
            logger.error(f"List documents error: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.errorhandler(413)
    def request_entity_too_large(error):
        return jsonify({'error': 'File too large. Maximum size is 16MB'}), 413
    
    return app

if __name__ == '__main__':
    app = create_async_app()
    app.run(debug=True)