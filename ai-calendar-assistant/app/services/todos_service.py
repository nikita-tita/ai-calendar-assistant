"""Service for managing todos with encrypted storage."""

import uuid
import os
from datetime import datetime
from typing import List, Optional, Dict
import structlog
from threading import Lock

from app.schemas.todos import Todo, TodoDTO, TodoPriority
from app.services.encrypted_storage import EncryptedStorage

logger = structlog.get_logger()

# Analytics service - optional, fallback if not available
try:
    from app.services.analytics_service import analytics_service
    from app.models.analytics import ActionType
    ANALYTICS_ENABLED = True
except ImportError:
    analytics_service = None
    ANALYTICS_ENABLED = False


class TodosService:
    """Service for storing and managing user todos with encrypted storage."""

    def __init__(self, data_dir: Optional[str] = None):
        """
        Initialize todos service with encrypted storage.

        Args:
            data_dir: Directory path for storing encrypted todo files
        """
        if data_dir is None:
            data_dir = os.getenv("TODOS_DATA_DIR", "/var/lib/calendar-bot/todos")
            
        # Development fallback if we can't write to the target directory
        try:
            # We don't create it here, EncryptedStorage does, but we can check parent
            pass
        except Exception:
            pass
            
        # If we are local and the path is /var/lib, we might want to fallback automatically
        # but explicit env var is better.
            
        self.storage = EncryptedStorage(data_dir=data_dir)
        self._lock = Lock()
        logger.info("todos_service_initialized_encrypted", data_dir=data_dir)

    def _get_user_filename(self, user_id: str) -> str:
        """Get filename for user's todos."""
        return f"user_{user_id}.json"

    def _load_todos(self, user_id: str) -> Dict[str, dict]:
        """
        Load todos for a user from encrypted storage.

        Returns:
            Dictionary mapping todo_id to todo data
        """
        try:
            filename = self._get_user_filename(user_id)
            data = self.storage.load(filename, default={})

            # Convert datetime strings back to datetime objects
            for todo_id, todo_data in data.items():
                if todo_data.get('due_date'):
                    todo_data['due_date'] = datetime.fromisoformat(todo_data['due_date'])
                if todo_data.get('created_at'):
                    todo_data['created_at'] = datetime.fromisoformat(todo_data['created_at'])
                if todo_data.get('updated_at'):
                    todo_data['updated_at'] = datetime.fromisoformat(todo_data['updated_at'])
            return data
        except Exception as e:
            logger.error("load_todos_error", user_id=user_id, error=str(e))
            return {}

    def _save_todos(self, user_id: str, todos: Dict[str, dict]) -> bool:
        """
        Save todos for a user to encrypted storage.

        Args:
            user_id: User ID
            todos: Dictionary mapping todo_id to todo data

        Returns:
            True if successful
        """
        try:
            with self._lock:
                # Convert datetime objects to strings for JSON serialization
                serializable_todos = {}
                for todo_id, todo_data in todos.items():
                    todo_copy = todo_data.copy()
                    if todo_copy.get('due_date'):
                        todo_copy['due_date'] = todo_copy['due_date'].isoformat()
                    if todo_copy.get('created_at'):
                        todo_copy['created_at'] = todo_copy['created_at'].isoformat()
                    if todo_copy.get('updated_at'):
                        todo_copy['updated_at'] = todo_copy['updated_at'].isoformat()
                    serializable_todos[todo_id] = todo_copy

                filename = self._get_user_filename(user_id)
                self.storage.save(serializable_todos, filename, encrypt=True)
            return True
        except Exception as e:
            logger.error("save_todos_error", user_id=user_id, error=str(e))
            return False

    async def create_todo(self, user_id: str, todo_dto: TodoDTO) -> Optional[str]:
        """
        Create a new todo.

        Args:
            user_id: User ID
            todo_dto: Todo data

        Returns:
            Todo ID if successful, None otherwise
        """
        try:
            todo_id = str(uuid.uuid4())
            now = datetime.now()

            todo_data = {
                'id': todo_id,
                'title': todo_dto.title or "Новая задача",
                'completed': todo_dto.completed,
                'priority': todo_dto.priority or TodoPriority.MEDIUM,
                'due_date': todo_dto.due_date,
                'notes': todo_dto.notes,
                'created_at': now,
                'updated_at': now
            }

            todos = self._load_todos(user_id)
            todos[todo_id] = todo_data

            if self._save_todos(user_id, todos):
                logger.info("todo_created", user_id=user_id, todo_id=todo_id, title=todo_dto.title)
                # Log to analytics
                if ANALYTICS_ENABLED and analytics_service:
                    try:
                        analytics_service.log_action(
                            user_id=user_id,
                            action_type=ActionType.TODO_CREATE,
                            details=f"Todo: {todo_dto.title[:100]}" if todo_dto.title else "Todo created",
                            event_id=todo_id,
                            success=True
                        )
                    except Exception as e:
                        logger.warning("analytics_todo_log_failed", error=str(e))
                return todo_id
            else:
                return None

        except Exception as e:
            logger.error("create_todo_error", user_id=user_id, error=str(e), exc_info=True)
            return None

    async def list_todos(
        self,
        user_id: str,
        completed: Optional[bool] = None,
        priority: Optional[TodoPriority] = None
    ) -> List[Todo]:
        """
        Get todos for a user with optional filters.

        Args:
            user_id: User ID
            completed: Filter by completion status (None = all)
            priority: Filter by priority (None = all)

        Returns:
            List of todos
        """
        try:
            todos = self._load_todos(user_id)
            result = []

            for todo_data in todos.values():
                # Apply filters
                if completed is not None and todo_data['completed'] != completed:
                    continue
                if priority is not None and todo_data['priority'] != priority:
                    continue

                result.append(Todo(**todo_data))

            # Sort: incomplete first, then by priority (high to low), then by creation date
            priority_order = {TodoPriority.HIGH: 0, TodoPriority.MEDIUM: 1, TodoPriority.LOW: 2}
            result.sort(key=lambda t: (
                t.completed,
                priority_order.get(t.priority, 1),
                t.created_at
            ))

            logger.info("todos_listed", user_id=user_id, count=len(result))
            return result

        except Exception as e:
            logger.error("list_todos_error", user_id=user_id, error=str(e), exc_info=True)
            return []

    async def update_todo(self, user_id: str, todo_id: str, todo_dto: TodoDTO) -> bool:
        """
        Update an existing todo.

        Args:
            user_id: User ID
            todo_id: Todo ID
            todo_dto: Updated todo data

        Returns:
            True if successful
        """
        try:
            todos = self._load_todos(user_id)

            if todo_id not in todos:
                logger.warning("todo_not_found", user_id=user_id, todo_id=todo_id)
                return False

            todo_data = todos[todo_id]

            # Update fields if provided
            if todo_dto.title is not None:
                todo_data['title'] = todo_dto.title
            if todo_dto.completed is not None:
                todo_data['completed'] = todo_dto.completed
            if todo_dto.priority is not None:
                todo_data['priority'] = todo_dto.priority
            if todo_dto.due_date is not None:
                todo_data['due_date'] = todo_dto.due_date
            if todo_dto.notes is not None:
                todo_data['notes'] = todo_dto.notes

            todo_data['updated_at'] = datetime.now()

            if self._save_todos(user_id, todos):
                logger.info("todo_updated", user_id=user_id, todo_id=todo_id)
                # Log to analytics
                if ANALYTICS_ENABLED and analytics_service:
                    try:
                        analytics_service.log_action(
                            user_id=user_id,
                            action_type=ActionType.TODO_UPDATE,
                            details=f"Todo updated: {todo_data.get('title', '')[:100]}",
                            event_id=todo_id,
                            success=True
                        )
                    except Exception as e:
                        logger.warning("analytics_todo_log_failed", error=str(e))
                return True
            else:
                return False

        except Exception as e:
            logger.error("update_todo_error", user_id=user_id, todo_id=todo_id, error=str(e), exc_info=True)
            return False

    async def toggle_todo(self, user_id: str, todo_id: str) -> bool:
        """
        Toggle completion status of a todo.

        Args:
            user_id: User ID
            todo_id: Todo ID

        Returns:
            True if successful
        """
        try:
            todos = self._load_todos(user_id)

            if todo_id not in todos:
                logger.warning("todo_not_found", user_id=user_id, todo_id=todo_id)
                return False

            todos[todo_id]['completed'] = not todos[todo_id]['completed']
            todos[todo_id]['updated_at'] = datetime.now()

            if self._save_todos(user_id, todos):
                logger.info(
                    "todo_toggled",
                    user_id=user_id,
                    todo_id=todo_id,
                    completed=todos[todo_id]['completed']
                )
                # Log to analytics
                if ANALYTICS_ENABLED and analytics_service:
                    try:
                        analytics_service.log_action(
                            user_id=user_id,
                            action_type=ActionType.TODO_COMPLETE,
                            details=f"Todo {'completed' if todos[todo_id]['completed'] else 'uncompleted'}: {todos[todo_id].get('title', '')[:100]}",
                            event_id=todo_id,
                            success=True
                        )
                    except Exception as e:
                        logger.warning("analytics_todo_log_failed", error=str(e))
                return True
            else:
                return False

        except Exception as e:
            logger.error("toggle_todo_error", user_id=user_id, todo_id=todo_id, error=str(e), exc_info=True)
            return False

    async def delete_todo(self, user_id: str, todo_id: str) -> bool:
        """
        Delete a todo.

        Args:
            user_id: User ID
            todo_id: Todo ID

        Returns:
            True if successful
        """
        try:
            todos = self._load_todos(user_id)

            if todo_id not in todos:
                logger.warning("todo_not_found", user_id=user_id, todo_id=todo_id)
                return False

            # Get title before deletion for analytics
            todo_title = todos[todo_id].get('title', '')
            del todos[todo_id]

            if self._save_todos(user_id, todos):
                logger.info("todo_deleted", user_id=user_id, todo_id=todo_id)
                # Log to analytics
                if ANALYTICS_ENABLED and analytics_service:
                    try:
                        analytics_service.log_action(
                            user_id=user_id,
                            action_type=ActionType.TODO_DELETE,
                            details=f"Todo deleted: {todo_title[:100]}",
                            event_id=todo_id,
                            success=True
                        )
                    except Exception as e:
                        logger.warning("analytics_todo_log_failed", error=str(e))
                return True
            else:
                return False

        except Exception as e:
            logger.error("delete_todo_error", user_id=user_id, todo_id=todo_id, error=str(e), exc_info=True)
            return False

    async def get_todo(self, user_id: str, todo_id: str) -> Optional[Todo]:
        """
        Get a specific todo by ID.

        Args:
            user_id: User ID
            todo_id: Todo ID

        Returns:
            Todo if found, None otherwise
        """
        try:
            todos = self._load_todos(user_id)

            if todo_id not in todos:
                return None

            return Todo(**todos[todo_id])

        except Exception as e:
            logger.error("get_todo_error", user_id=user_id, todo_id=todo_id, error=str(e), exc_info=True)
            return None


# Global instance
todos_service = TodosService()
