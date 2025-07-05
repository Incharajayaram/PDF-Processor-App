from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import json
import logging
from datetime import datetime

from config import Config
from models import get_session, Job
from pdf_processor import PDFProcessor
from llm_service import LLMService
from github_service import GitHubService
from validators import validate_job_id, validate_file_upload

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    CORS(app)
    
    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Initialize services
    pdf_processor = PDFProcessor(app.config['UPLOAD_FOLDER'])
    llm_service = LLMService(
        api_key=app.config.get('GEMINI_API_KEY') or app.config.get('HUGGINGFACE_API_KEY')
    )
    github_service = GitHubService(token=app.config.get('GITHUB_TOKEN'))
    
    def allowed_file(filename):
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']
    
    @app.route('/health', methods=['GET'])
    def health_check():
        return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})
    
    @app.route('/api/documents/upload', methods=['POST'])
    def upload_document():
        """Upload a PDF document for processing"""
        try:
            # Validate file upload
            validation_errors = validate_file_upload(request)
            if validation_errors:
                return jsonify({'error': validation_errors[0]}), 400
            
            file = request.files['file']
            
            # Create new job
            session = get_session()
            job = Job(
                pdf_filename=secure_filename(file.filename or ""),
                status='pending'
            )
            session.add(job)
            session.commit()
            
            # Save file
            filename = f"{job.job_id}_{secure_filename(file.filename or '')}"
            file_path = pdf_processor.save_uploaded_file(file, filename)
            
            # Store job info before processing
            job_id = job.job_id
            
            # Process synchronously for now (will make async later)
            try:
                # Update status to processing
                setattr(job, "status", "processing")
                session.commit()
                
                # Extract text from PDF
                pdf_text = pdf_processor.process_pdf(file_path)
                
                # Extract company name using LLM
                company_name = llm_service.extract_company_name(pdf_text)
                
                if company_name:
                    setattr(job, "company_name", company_name)
                    
                    # Get GitHub organization info
                    org_info = github_service.get_organization_info(company_name)
                    if org_info:
                        setattr(job, "github_org_data", json.dumps(org_info))
                        
                        # Get organization members
                        members = github_service.get_organization_members(company_name)
                        setattr(job, "github_members", json.dumps(members))
                
                setattr(job, "status", "completed")
                session.commit()
                
            except Exception as e:
                logger.error(f"Error processing job {job.job_id}: {str(e)}")
                setattr(job, "status", "failed")
                setattr(job, "error_message", str(e))
                session.commit()
                
            # Get the final status before closing session
            status = job.status
            
            session.close()
            
            return jsonify({
                'job_id': job_id,
                'status': status,
                'message': 'File uploaded successfully. Processing started.'
            }), 201
            
        except Exception as e:
            logger.error(f"Upload error: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/documents/status/<job_id>', methods=['GET'])
    @validate_job_id
    def get_job_status(job_id):
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
                'timestamp': job.timestamp.isoformat() if getattr(job, "timestamp", None) is not None else None
            }

            if getattr(job, "status", None) == 'completed':
                response['company_name'] = job.company_name

                github_org_data = getattr(job, "github_org_data", None)
                if github_org_data is not None and isinstance(github_org_data, str):
                    response['github_org_data'] = json.loads(github_org_data)
                else:
                    response['github_org_data'] = None

                github_members = getattr(job, "github_members", None)
                if github_members is not None and isinstance(github_members, str):
                    members_list = json.loads(github_members)
                    response['github_members'] = members_list
                    response['members_count'] = len(members_list)
                else:
                    response['github_members'] = None
                    response['members_count'] = 0

            elif getattr(job, "status", None) == 'failed':
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
                doc = {
                    'job_id': job.job_id,
                    'pdf_filename': job.pdf_filename,
                    'status': job.status,
                    'timestamp': job.timestamp.isoformat() if getattr(job, "timestamp", None) is not None else None,
                    'company_name': job.company_name
                }
                
                github_members = getattr(job, "github_members", None)
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
    app = create_app()
    app.run(debug=True)