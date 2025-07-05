import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///pdf_processor.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    #llm configuration
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    HUGGINGFACE_API_KEY = os.environ.get('HUGGINGFACE_API_KEY')
    
    #github configuration
    GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
    
    #celery configuration
    CELERY_BROKER_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    CELERY_RESULT_BACKEND = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    
    #upload configuration
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  #16 mb max file size
    ALLOWED_EXTENSIONS = {'pdf'}