from datetime import datetime
from sqlalchemy import create_engine, Column, String, DateTime, Text, Integer
from sqlalchemy.orm import declarative_base, sessionmaker
import uuid

Base = declarative_base()

class Job(Base):
    __tablename__ = 'jobs'
    
    job_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    pdf_filename = Column(String(255), nullable=False)
    company_name = Column(String(255))
    github_org_data = Column(Text)  #json string
    github_members = Column(Text)  #json string
    timestamp = Column(DateTime, default=datetime.now)
    status = Column(String(50), default='pending')  #pending, processing, completed, failed
    error_message = Column(Text)
    task_id = Column(String(255))  # Celery task ID for async processing
    
    def to_dict(self):
        return {
            'job_id': self.job_id,
            'pdf_filename': self.pdf_filename,
            'company_name': self.company_name,
            'github_org_data': self.github_org_data,
            'github_members': self.github_members,
            'timestamp': self.timestamp.isoformat() if getattr(self, 'timestamp', None) is not None else None,
            'status': self.status,
            'error_message': self.error_message,
            'task_id': self.task_id
        }

#database initialization
def init_db(database_url='sqlite:///pdf_processor.db'):
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session

#helper function to get a session
def get_session():
    Session = init_db()
    return Session()