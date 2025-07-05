# PDF Processing API

A Flask-based API service that processes PDF documents to extract company information using LLMs and integrates with GitHub API to fetch organization details.

## Features

- **PDF Upload & Processing**: Upload PDF files and extract text content using PyMuPDF
- **Company Extraction**: Use free LLM APIs (Google Gemini or Hugging Face) to identify tech companies
- **GitHub Organization Search**: Search and fetch organization details and public members from GitHub
- **Async Processing**: Background processing with simulated delays (30-300s) using Celery and Redis
- **SQLite Database**: Persistent storage for job tracking and results
- **RESTful API**: Clean API endpoints for document upload and status checking

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd backend-assignment
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Copy the environment configuration:
```bash
cp .env.example .env
```

4. Configure your environment variables in `.env`:
   - `GEMINI_API_KEY` - Get free key from [Google AI Studio](https://makersuite.google.com/app/apikey)
   - `HUGGINGFACE_API_KEY` (optional - some models work without key)
   - `GITHUB_TOKEN` (optional, but recommended for higher rate limits)
   - `REDIS_URL` (for async processing)

5. Initialize the database:
```bash
python app.py --init-db
```

## Usage

### Running in Synchronous Mode

```bash
python app.py
```

### Running in Asynchronous Mode

1. Start Redis server:
```bash
redis-server
```

2. Start Celery worker:
```bash
celery -A celery_worker worker --loglevel=info
```

3. Start Flask app with async mode:
```bash
python app.py --async
```

## API Endpoints

### Upload PDF Document
```http
POST /api/documents/upload
Content-Type: multipart/form-data

file: <pdf-file>
```

Response:
```json
{
  "job_id": "uuid",
  "status": "pending",
  "message": "File uploaded successfully. Processing started."
}
```

### Check Job Status
```http
GET /api/documents/status/{job_id}
```

Response:
```json
{
  "job_id": "uuid",
  "status": "completed",
  "pdf_filename": "document.pdf",
  "company_name": "microsoft",
  "github_org_data": {
    "login": "microsoft",
    "name": "Microsoft",
    "public_repos": 5000,
    ...
  },
  "github_members": [...],
  "members_count": 100
}
```

### List All Documents
```http
GET /api/documents
```

Response:
```json
{
  "documents": [
    {
      "job_id": "uuid",
      "pdf_filename": "document.pdf",
      "status": "completed",
      "company_name": "microsoft",
      "members_count": 100,
      "timestamp": "2024-01-01T00:00:00"
    }
  ]
}
```

## Configuration

### LLM Integration

The API uses free LLM services in the following order:
1. **Google Gemini** - Requires free API key from Google AI Studio
2. **Hugging Face** - Free inference API (works without key for some models)
3. **Fallback** - Pattern matching for common tech companies

### File Upload Limits

- Maximum file size: 16MB
- Allowed formats: PDF only

## Project Structure

```
├── app.py              # Main entry point
├── api.py              # Synchronous Flask API
├── api_async.py        # Asynchronous Flask API with 30-300s delay
├── models.py           # SQLAlchemy database models
├── pdf_processor.py    # PDF processing logic (uses PyMuPDF)
├── llm_service.py      # Free LLM integration (Gemini/HuggingFace)
├── github_service.py   # GitHub API with organization search
├── tasks.py            # Celery async tasks with simulated delays
├── celery_worker.py    # Celery worker entry point
├── config.py           # Application configuration
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

## Error Handling

The API includes comprehensive error handling for:
- Invalid file types
- File size limits
- LLM API failures (with fallback to pattern matching)
- GitHub API rate limits
- Network timeouts
- Processing failures

## Database Schema

The SQLite database stores job information with the following fields:
- `job_id`: Unique identifier
- `pdf_filename`: Original filename
- `company_name`: Extracted company name
- `github_org_data`: JSON organization details
- `github_members`: JSON list of public members
- `timestamp`: Upload timestamp
- `status`: Job status (pending/processing/completed/failed)
- `error_message`: Error details if failed

## Development

To run in development mode with hot reloading:
```bash
export FLASK_ENV=development
python app.py
```

## License

MIT License