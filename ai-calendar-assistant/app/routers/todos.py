"""TODO API router for web application."""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
import structlog

from app.services.todos_service import todos_service
from app.schemas.todos import Todo as TodoSchema, TodoDTO, TodoPriority
from app.models.analytics import ActionType
from app.services.analytics_service import analytics_service

logger = structlog.get_logger()

router = APIRouter()


class TodoCreateRequest(BaseModel):
    """Request model for creating a todo."""
    title: str
    completed: bool = False
    due_date: Optional[datetime] = None


class TodoUpdateRequest(BaseModel):
    """Request model for updating a todo."""
    title: Optional[str] = None
    completed: Optional[bool] = None
    due_date: Optional[datetime] = None


class TodoResponse(BaseModel):
    """Response model for todo."""
    id: str
    title: str
    completed: bool
    due_date: Optional[datetime] = None
    created_at: datetime


@router.get("/todos/{user_id}", response_model=List[TodoResponse])
async def get_user_todos(request: Request, user_id: str):
    """
    Get all todos for a user.

    Note: user_id is validated by TelegramAuthMiddleware via HMAC signature.
    """
    try:
        # Get validated user_id from middleware
        authenticated_user_id = request.state.telegram_user_id

        # Verify that path user_id matches authenticated user_id
        if user_id != authenticated_user_id:
            logger.warning(
                "user_id_mismatch",
                requested_user_id=user_id,
                authenticated_user_id=authenticated_user_id
            )
            raise HTTPException(
                status_code=403,
                detail="Forbidden: Cannot access other user's todos"
            )

        logger.info("fetching_todos", user_id=user_id)

        # Log WebApp todo access
        analytics_service.log_action(
            user_id=user_id,
            action_type=ActionType.WEBAPP_OPEN,
            details="WebApp: Opened todos list"
        )

        todos = await todos_service.list_todos(user_id)

        logger.info("todos_fetched", user_id=user_id, count=len(todos))
        return todos

    except Exception as e:
        logger.error("get_todos_error", user_id=user_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch todos: {str(e)}")


@router.post("/todos/{user_id}", response_model=TodoResponse)
async def create_todo(request: Request, user_id: str, todo: TodoCreateRequest):
    """
    Create a new todo for a user.

    Note: user_id is validated by TelegramAuthMiddleware via HMAC signature.
    """
    try:
        # Get validated user_id from middleware
        authenticated_user_id = request.state.telegram_user_id

        # Verify that path user_id matches authenticated user_id
        if user_id != authenticated_user_id:
            logger.warning(
                "user_id_mismatch",
                requested_user_id=user_id,
                authenticated_user_id=authenticated_user_id
            )
            raise HTTPException(
                status_code=403,
                detail="Forbidden: Cannot create todos for other users"
            )

        logger.info("creating_todo", user_id=user_id, title=todo.title)

        todo_dto = TodoDTO(
            title=todo.title,
            completed=todo.completed,
            due_date=todo.due_date
        )

        todo_id = await todos_service.create_todo(user_id, todo_dto)

        if not todo_id:
            raise HTTPException(status_code=500, detail="Failed to create todo")

        created_todo = await todos_service.get_todo(user_id, todo_id)

        logger.info("todo_created", user_id=user_id, todo_id=todo_id)

        # Log to analytics
        analytics_service.log_action(
            user_id=user_id,
            action_type=ActionType.TODO_CREATE,
            details=f"API: Created {todo.title}"
        )

        return created_todo

    except HTTPException:
        raise
    except Exception as e:
        logger.error("create_todo_error", user_id=user_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create todo: {str(e)}")


@router.post("/todos/{user_id}/{todo_id}/toggle", response_model=TodoResponse)
async def toggle_todo(request: Request, user_id: str, todo_id: str):
    """
    Toggle todo completed status.

    Note: user_id is validated by TelegramAuthMiddleware via HMAC signature.
    """
    try:
        # Get validated user_id from middleware
        authenticated_user_id = request.state.telegram_user_id

        # Verify that path user_id matches authenticated user_id
        if user_id != authenticated_user_id:
            logger.warning(
                "user_id_mismatch",
                requested_user_id=user_id,
                authenticated_user_id=authenticated_user_id
            )
            raise HTTPException(
                status_code=403,
                detail="Forbidden: Cannot toggle other user's todos"
            )

        logger.info("toggling_todo", user_id=user_id, todo_id=todo_id)

        success = await todos_service.toggle_todo(user_id, todo_id)

        if not success:
            raise HTTPException(status_code=404, detail="Todo not found")

        updated_todo = await todos_service.get_todo(user_id, todo_id)

        logger.info("todo_toggled", user_id=user_id, todo_id=todo_id, completed=updated_todo.completed)

        # Log to analytics
        action = ActionType.TODO_COMPLETE if updated_todo.completed else ActionType.TODO_CREATE
        analytics_service.log_action(
            user_id=user_id,
            action_type=action,
            details=f"API: Toggled {updated_todo.title}"
        )

        return updated_todo

    except HTTPException:
        raise
    except Exception as e:
        logger.error("toggle_todo_error", user_id=user_id, todo_id=todo_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to toggle todo: {str(e)}")


@router.delete("/todos/{user_id}/{todo_id}")
async def delete_todo(request: Request, user_id: str, todo_id: str):
    """
    Delete a todo.

    Note: user_id is validated by TelegramAuthMiddleware via HMAC signature.
    """
    try:
        # Get validated user_id from middleware
        authenticated_user_id = request.state.telegram_user_id

        # Verify that path user_id matches authenticated user_id
        if user_id != authenticated_user_id:
            logger.warning(
                "user_id_mismatch",
                requested_user_id=user_id,
                authenticated_user_id=authenticated_user_id
            )
            raise HTTPException(
                status_code=403,
                detail="Forbidden: Cannot delete other user's todos"
            )

        logger.info("deleting_todo", user_id=user_id, todo_id=todo_id)

        success = await todos_service.delete_todo(user_id, todo_id)

        if not success:
            raise HTTPException(status_code=404, detail="Todo not found")

        logger.info("todo_deleted", user_id=user_id, todo_id=todo_id)

        # Log to analytics
        analytics_service.log_action(
            user_id=user_id,
            action_type=ActionType.TODO_DELETE,
            details=f"API: Deleted todo"
        )

        return {"status": "success"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("delete_todo_error", user_id=user_id, todo_id=todo_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete todo: {str(e)}")


@router.put("/todos/{user_id}/{todo_id}", response_model=TodoResponse)
async def update_todo(request: Request, user_id: str, todo_id: str, todo: TodoUpdateRequest):
    """
    Update a todo.

    Note: user_id is validated by TelegramAuthMiddleware via HMAC signature.
    """
    try:
        # Get validated user_id from middleware
        authenticated_user_id = request.state.telegram_user_id

        # Verify that path user_id matches authenticated user_id
        if user_id != authenticated_user_id:
            logger.warning(
                "user_id_mismatch",
                requested_user_id=user_id,
                authenticated_user_id=authenticated_user_id
            )
            raise HTTPException(
                status_code=403,
                detail="Forbidden: Cannot update other user's todos"
            )

        logger.info("updating_todo", user_id=user_id, todo_id=todo_id)

        # Create TodoDTO with only provided fields
        todo_dto = TodoDTO(
            title=todo.title,
            completed=todo.completed,
            due_date=todo.due_date
        )

        success = await todos_service.update_todo(user_id, todo_id, todo_dto)

        if not success:
            raise HTTPException(status_code=404, detail="Todo not found")

        updated_todo = await todos_service.get_todo(user_id, todo_id)

        logger.info("todo_updated", user_id=user_id, todo_id=todo_id)

        # Log to analytics
        analytics_service.log_action(
            user_id=user_id,
            action_type=ActionType.TODO_CREATE,
            details=f"API: Updated {updated_todo.title}"
        )

        return updated_todo

    except HTTPException:
        raise
    except Exception as e:
        logger.error("update_todo_error", user_id=user_id, todo_id=todo_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update todo: {str(e)}")
