.PHONY: help install test test-cov lint run run-async celery redis clean

help:
	@echo "Available commands:"
	@echo "  make install      - Install dependencies"
	@echo "  make test         - Run tests"
	@echo "  make test-cov     - Run tests with coverage"
	@echo "  make lint         - Run linters"
	@echo "  make run          - Run Flask app (sync mode)"
	@echo "  make run-async    - Run Flask app (async mode)"
	@echo "  make celery       - Run Celery worker"
	@echo "  make redis        - Start Redis server"
	@echo "  make clean        - Clean up temporary files"

install:
	pip install -r requirements.txt
	pip install -r requirements-test.txt

test:
	pytest

test-cov:
	pytest --cov=. --cov-report=html --cov-report=term

lint:
	python -m py_compile *.py
	@echo "Basic syntax check passed"

run:
	python app.py --init-db
	python app.py

run-async:
	python app.py --init-db
	python app.py --async-mode

celery:
	celery -A celery_worker.celery_app worker --loglevel=info

redis:
	redis-server

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -f pdf_processor.db