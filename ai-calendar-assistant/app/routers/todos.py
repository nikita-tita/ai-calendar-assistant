"""Todos API router for web application."""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
import structlog

from app.services.todos_service import todos_service
from app.schemas.todos import Todo, TodoDTO, TodoPriority, TodoIntentType
from app.routers.events import validate_user_id  # SEC-010: Shared validation

logger = structlog.get_logger()

router = APIRouter()


# Pydantic models for API
class TodoCreateRequest(BaseModel):
    """Request model for creating a todo."""
    title: str
    completed: bool = False
    priority: TodoPriority = TodoPriority.MEDIUM
    due_date: Optional[datetime] = None
    notes: Optional[str] = None


class TodoUpdateRequest(BaseModel):
    """Request model for updating a todo."""
    title: Optional[str] = None
    completed: Optional[bool] = None
    priority: Optional[TodoPriority] = None
    due_date: Optional[datetime] = None
    notes: Optional[str] = None


class TodoResponse(BaseModel):
    """Response model for todo."""
    id: str
    title: str
    completed: bool
    priority: TodoPriority
    due_date: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


@router.get("/todos/{user_id}", response_model=List[TodoResponse])
async def get_user_todos(
    request: Request,
    user_id: str,
    completed: Optional[bool] = Query(None, description="Filter by completion status"),
    priority: Optional[TodoPriority] = Query(None, description="Filter by priority")
):
    """
    Get all todos for a user with optional filters.

    Note: user_id is validated by TelegramAuthMiddleware via HMAC signature.
    """
    # SEC-010: Validate user_id format before processing
    validate_user_id(user_id)

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

        logger.info("fetching_todos", user_id=user_id, completed=completed, priority=priority)

        todos = await todos_service.list_todos(user_id, completed=completed, priority=priority)

        # Convert to response format
        response_todos = []
        for todo in todos:
            response_todos.append(TodoResponse(
                id=todo.id,
                title=todo.title,
                completed=todo.completed,
                priority=todo.priority,
                due_date=todo.due_date,
                notes=todo.notes,
                created_at=todo.created_at,
                updated_at=todo.updated_at
            ))

        logger.info("todos_fetched", user_id=user_id, count=len(response_todos))
        return response_todos

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_todos_error", user_id=user_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch todos: {str(e)}")


@router.post("/todos/{user_id}", response_model=TodoResponse)
async def create_todo(request: Request, user_id: str, todo: TodoCreateRequest):
    """
    Create a new todo for a user.

    Note: user_id is validated by TelegramAuthMiddleware via HMAC signature.
    """
    # SEC-010: Validate user_id format before processing
    validate_user_id(user_id)

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

        # Create TodoDTO
        todo_dto = TodoDTO(
            intent=TodoIntentType.CREATE,
            title=todo.title,
            completed=todo.completed,
            priority=todo.priority,
            due_date=todo.due_date,
            notes=todo.notes
        )

        # Create todo
        todo_id = await todos_service.create_todo(user_id, todo_dto)

        if not todo_id:
            raise HTTPException(status_code=500, detail="Failed to create todo")

        logger.info("todo_created", user_id=user_id, todo_id=todo_id)

        # Return created todo
        created_todo = await todos_service.get_todo(user_id, todo_id)
        if not created_todo:
            raise HTTPException(status_code=500, detail="Failed to retrieve created todo")

        return TodoResponse(
            id=created_todo.id,
            title=created_todo.title,
            completed=created_todo.completed,
            priority=created_todo.priority,
            due_date=created_todo.due_date,
            notes=created_todo.notes,
            created_at=created_todo.created_at,
            updated_at=created_todo.updated_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("create_todo_error", user_id=user_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create todo: {str(e)}")


@router.put("/todos/{user_id}/{todo_id}", response_model=TodoResponse)
async def update_todo(request: Request, user_id: str, todo_id: str, todo: TodoUpdateRequest):
    """
    Update an existing todo for a specific user.

    Note: user_id is validated by TelegramAuthMiddleware via HMAC signature.
    """
    # SEC-010: Validate user_id format before processing
    validate_user_id(user_id)

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

        # Create TodoDTO with updated fields
        todo_dto = TodoDTO(
            intent=TodoIntentType.UPDATE,
            title=todo.title,
            completed=todo.completed,
            priority=todo.priority,
            due_date=todo.due_date,
            notes=todo.notes
        )

        # Update todo
        success = await todos_service.update_todo(user_id, todo_id, todo_dto)

        if not success:
            raise HTTPException(status_code=404, detail="Todo not found")

        logger.info("todo_updated", user_id=user_id, todo_id=todo_id)

        # Return updated todo
        updated_todo = await todos_service.get_todo(user_id, todo_id)
        if not updated_todo:
            raise HTTPException(status_code=500, detail="Failed to retrieve updated todo")

        return TodoResponse(
            id=updated_todo.id,
            title=updated_todo.title,
            completed=updated_todo.completed,
            priority=updated_todo.priority,
            due_date=updated_todo.due_date,
            notes=updated_todo.notes,
            created_at=updated_todo.created_at,
            updated_at=updated_todo.updated_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("update_todo_error", user_id=user_id, todo_id=todo_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update todo: {str(e)}")


@router.post("/todos/{user_id}/{todo_id}/toggle")
async def toggle_todo(request: Request, user_id: str, todo_id: str):
    """
    Toggle completion status of a todo.

    Note: user_id is validated by TelegramAuthMiddleware via HMAC signature.
    """
    # SEC-010: Validate user_id format before processing
    validate_user_id(user_id)

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

        logger.info("todo_toggled", user_id=user_id, todo_id=todo_id)

        # Return updated todo
        updated_todo = await todos_service.get_todo(user_id, todo_id)
        if not updated_todo:
            raise HTTPException(status_code=500, detail="Failed to retrieve todo")

        return TodoResponse(
            id=updated_todo.id,
            title=updated_todo.title,
            completed=updated_todo.completed,
            priority=updated_todo.priority,
            due_date=updated_todo.due_date,
            notes=updated_todo.notes,
            created_at=updated_todo.created_at,
            updated_at=updated_todo.updated_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("toggle_todo_error", user_id=user_id, todo_id=todo_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to toggle todo: {str(e)}")


@router.delete("/todos/{user_id}/{todo_id}")
async def delete_todo(request: Request, user_id: str, todo_id: str):
    """
    Delete a todo for a specific user.

    Note: user_id is validated by TelegramAuthMiddleware via HMAC signature.
    """
    # SEC-010: Validate user_id format before processing
    validate_user_id(user_id)

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

        return {"status": "deleted", "id": todo_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("delete_todo_error", user_id=user_id, todo_id=todo_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete todo: {str(e)}")


@router.get("/health")
async def todos_health():
    """Health check for todos API."""
    return {
        "status": "ok",
        "service": "todos"
    }
