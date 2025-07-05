import json
import logging
import os
from celery import Celery
from celery.result import AsyncResult
from config import Config
from models import get_session, Job
from pdf_processor import PDFProcessor
from llm_service import LLMService
from github_service import GitHubService

logger = logging.getLogger(__name__)

#initialize celery
celery_app = Celery('pdf_processor')
celery_app.config_from_object({
    'broker_url': Config.CELERY_BROKER_URL,
    'result_backend': Config.CELERY_RESULT_BACKEND,
    'task_serializer': 'json',
    'accept_content': ['json'],
    'result_serializer': 'json',
    'timezone': 'UTC',
    'enable_utc': True,
})

#initialize services
pdf_processor = PDFProcessor(Config.UPLOAD_FOLDER)
llm_service = LLMService(
    api_key=Config.GEMINI_API_KEY or Config.HUGGINGFACE_API_KEY
)
github_service = GitHubService(token=Config.GITHUB_TOKEN)

@celery_app.task(name='process_pdf')
def process_pdf_async(job_id: str, file_path: str):
    """async task to process pdf and extract company information"""
    import random
    import time as time_module
    
    session = get_session()
    job = session.query(Job).filter_by(job_id=job_id).first()
    
    if not job:
        logger.error(f"Job {job_id} not found")
        return {'status': 'failed', 'error': 'Job not found'}
    
    try:
        # update status to processing
        setattr(job, 'status', 'processing')
        session.commit()
        
        # simulate long processing time (30-300 seconds)
        delay = random.randint(30, 300)
        logger.info(f"Simulating processing delay of {delay} seconds for job {job_id}")
        time_module.sleep(delay)
        
        #extract text from pdf
        logger.info(f"Processing PDF for job {job_id}")
        pdf_text = pdf_processor.process_pdf(file_path)
        
        #extract company name using llm
        logger.info(f"Extracting company name for job {job_id}")
        company_name = llm_service.extract_company_name(pdf_text)
        
        if company_name:
            setattr(job, 'company_name', company_name)
            logger.info(f"Found company: {company_name}")
            
            #get github organization info
            logger.info(f"Fetching GitHub info for {company_name}")
            org_info = github_service.get_organization_info(company_name)
            
            if org_info:
                setattr(job, 'github_org_data', json.dumps(org_info))
                
                #get organization members
                members = github_service.get_organization_members(company_name)
                setattr(job, 'github_members', json.dumps(members))
                logger.info(f"Found {len(members)} members for {company_name}")
            else:
                logger.warning(f"No GitHub info found for {company_name}")
        else:
            logger.warning(f"No company name extracted for job {job_id}")
        
        setattr(job, 'status', 'completed')
        session.commit()
        
        return {
            'status': 'completed',
            'job_id': job_id,
            'company_name': company_name,
            'members_count': len(json.loads(getattr(job, 'github_members'))) if getattr(job, 'github_members', None) else 0
            }
    except Exception as e:
        setattr(job, 'status', 'failed')
        setattr(job, 'error_message', str(e))
        session.commit()
        return {
            'status': 'failed',
            'job_id': job_id,
            'error': str(e)
        }
        
    finally:
        session.close()
        
        #clean up uploaded file
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            logger.error(f"Error cleaning up file {file_path}: {str(e)}")

def get_task_status(task_id: str):
    """get the status of a celery task"""
    result = AsyncResult(task_id, app=celery_app)
    
    if result.ready():
        if result.successful():
            return {
                'status': 'completed',
                'result': result.result
            }
        else:
            return {
                'status': 'failed',
                'error': str(result.info)
            }
    else:
        return {
            'status': 'processing',
            'current': result.info.get('current', 0) if result.info else 0,
            'total': result.info.get('total', 1) if result.info else 1
        }