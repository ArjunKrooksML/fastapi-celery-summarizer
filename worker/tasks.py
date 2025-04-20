from celery import shared_task, states
from celery.exceptions import Ignore
from openai import OpenAI, AuthenticationError, RateLimitError, APIError
from app.utils.cache import Cache
from app.core.config import settings
import os
import logging
import hashlib

cache = Cache()

try:
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    if not settings.OPENAI_API_KEY:
        logging.error("OpenAI API Key is missing in settings.")
except Exception as client_init_error:
    logging.error(f"Failed to initialize OpenAI client: {client_init_error}", exc_info=True)
    client = None

@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def summarize_text(self, text: str, max_length: int = 150):
    task_id = self.request.id
    input_data = (text, max_length)
    cache_key = f"summary:{hashlib.sha256(str(input_data).encode()).hexdigest()}"

    if client is None:
         logging.error(f"OpenAI client not initialized for task {task_id}. Aborting.")
         self.update_state(state=states.FAILURE, meta={'status': 'OpenAI client initialization failed.'})
         raise Ignore()

    try:
        cached_result = cache.get(cache_key)
        if cached_result:
            logging.info(f"Cache hit for task {task_id} with key {cache_key}")
            self.update_state(state='SUCCESS', meta={'status': 'Retrieved from cache'})
            return cached_result

        logging.info(f"Cache miss for task {task_id} with key {cache_key}. Calling OpenAI.")
        self.update_state(state='PROGRESS', meta={'status': 'Calling OpenAI API...'})

        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes text concisely."},
                {"role": "user", "content": f"Summarize the following text in approximately {max_length} words: {text}"}
            ],
            max_tokens=max_length + 75,
            temperature=0.7,
        )

        summary = completion.choices[0].message.content.strip()

        cache.set(cache_key, summary)
        logging.info(f"OpenAI call successful for task {task_id}. Result cached with key {cache_key}")
        return summary

    except AuthenticationError as e:
         logging.error(f"OpenAI Authentication Error for task {task_id}: Status {e.status_code} - {e.message}")
         self.update_state(state=states.FAILURE, meta={'status': f'OpenAI Authentication Failed: {e.message}'})
         raise Ignore()
    except RateLimitError as e:
         logging.warning(f"OpenAI Rate Limit Hit for task {task_id}, retrying: {e}")
         retry_after = 10
         if e.response and hasattr(e.response, 'headers'):
              try:
                   retry_after = int(e.response.headers.get("retry-after", 10))
              except (ValueError, TypeError):
                   retry_after = 10
         self.update_state(state=states.RETRY, meta={'status': f'OpenAI Rate Limit Hit, retrying in {retry_after}s... ({self.request.retries + 1}/{self.max_retries})'})
         raise self.retry(exc=e, countdown=retry_after)
    except APIError as e:
         logging.error(f"OpenAI API Error for task {task_id}: Status {e.status_code} - {e.message}", exc_info=True)
         if e.status_code >= 500:
             self.update_state(state=states.RETRY, meta={'status': f'OpenAI API Error ({e.status_code}), retrying... ({self.request.retries + 1}/{self.max_retries})'})
             raise self.retry(exc=e)
         else:
              self.update_state(state=states.FAILURE, meta={'status': f'OpenAI API Error ({e.status_code}): {e.message}'})
              raise Ignore()
    except Exception as e:
        logging.error(f"An unexpected error occurred in task {task_id}: {e}", exc_info=True)
        self.update_state(state=states.RETRY, meta={'status': f'Unexpected error, retrying... ({self.request.retries + 1}/{self.max_retries})'})
        raise self.retry(exc=e)