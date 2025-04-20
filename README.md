A simple backend service using FastAPI and Celery to provide text summarization powered by OpenAI's GPT models.

1. pip install -r requirements.txt

2. Ensure your local Redis server is running.

3. uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload #FastAPI

4. Run Celery: celery -A app.celery_app worker --loglevel=info
