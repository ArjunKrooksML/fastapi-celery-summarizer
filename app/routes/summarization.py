from fastapi import APIRouter, HTTPException, status, Depends
from app.models.pydantic_models import SummText
from app.celery_app import celery # Import the configured celery instance
from celery.result import AsyncResult
from app.utils.cache import Cache
from app.dependencies import get_cache
import logging
import hashlib


router = APIRouter()

@router.post("/summarize", status_code=status.HTTP_202_ACCEPTED, name="summarize:text")
async def summarization_task(text_data: SummText, cache: Cache = Depends(get_cache)):
    try:
        input_data = (text_data.text, text_data.max_length)
        task = celery.send_task("worker.tasks.summarize_text", args=[text_data.text, text_data.max_length])
        logging.info(f"Sent task {task.id} for summarization.")
        return {"task_id": task.id}
    except Exception as e:
        logging.error(f"Failed to send task to Celery: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to initiate summarization task.")


@router.get("/status/{task_id}", name="summarize:status")
async def task_status(task_id: str):
    try:
        task = AsyncResult(task_id, app=celery)
        response = {
            "task_id": task_id,
            "state": task.state,
            "status": "Pending" # Default status message
        }

        if task.state == 'PENDING':
            response["status"] = "Task is waiting to be processed."
        elif task.state == 'STARTED':
             response["status"] = "Task has started."
        elif task.state == 'PROGRESS':
             response["status"] = task.info.get('status', 'Processing...')
        elif task.state == 'SUCCESS':
            response["status"] = "Task completed successfully."
            response["result_ready"] = True
        elif task.state == 'FAILURE':
            response["status"] = "Task failed."
            # Extract error info
            error_info = str(task.info) if isinstance(task.info, Exception) else task.info.get('status', 'Unknown error')
            response["error"] = error_info
            logging.error(f"Task {task_id} failed: {error_info}")
        elif task.state == 'RETRY':
            response["status"] = task.info.get('status', f'Task waiting for retry...')

        return response

    except Exception as e:
        logging.error(f"Error retrieving status for task {task_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task ID '{task_id}' not found or invalid."
        )


@router.get("/result/{task_id}", name="summarize:result")
async def task_result(task_id: str):
    try:
        task = AsyncResult(task_id, app=celery)

        if task.state == 'SUCCESS':
            result = task.get() #actual result
            return {"task_id": task_id, "state": task.state, "result": result}
        elif task.state in ['PENDING', 'STARTED', 'PROGRESS', 'RETRY']:
             raise HTTPException(
                status_code=status.HTTP_202_ACCEPTED, #means request is ok, but processing not complete
                detail=f"Task '{task_id}' is not completed yet. Current state: {task.state}"
            )
        elif task.state == 'FAILURE':
             error_info = str(task.info) if isinstance(task.info, Exception) else task.info.get('status', 'Unknown error')
             raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Task '{task_id}' failed. Error: {error_info}"
            )
        else:
             raise HTTPException(
                 status_code=status.HTTP_404_NOT_FOUND,
                 detail=f"Result for Task ID '{task_id}' not found or state unknown: {task.state}"
             )

    except Exception as e:
        logging.error(f"Error retrieving result for task {task_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not retrieve result for task '{task_id}'. Reason: {str(e)}"
        )