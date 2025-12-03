"""Service for managing todos."""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict
import structlog
from threading import Lock

from app.schemas.todos import Todo, TodoDTO, TodoPriority

logger = structlog.get_logger()


class TodosService:
    """Service for storing and managing user todos."""

    def __init__(self, storage_path: str = "./data/todos"):
        """
        Initialize todos service.

        Args:
            storage_path: Directory path for storing todo files
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        logger.info("todos_service_initialized", storage_path=str(self.storage_path))

    def _get_user_file(self, user_id: str) -> Path:
        """Get path to user's todos file."""
        return self.storage_path / f"user_{user_id}.json"

    def _load_todos(self, user_id: str) -> Dict[str, dict]:
        """
        Load todos for a user from file.

        Returns:
            Dictionary mapping todo_id to todo data
        """
        user_file = self._get_user_file(user_id)
        if not user_file.exists():
            return {}

        try:
            with open(user_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
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
        Save todos for a user to file.

        Args:
            user_id: User ID
            todos: Dictionary mapping todo_id to todo data

        Returns:
            True if successful
        """
        user_file = self._get_user_file(user_id)

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

                with open(user_file, 'w', encoding='utf-8') as f:
                    json.dump(serializable_todos, f, ensure_ascii=False, indent=2)
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

            del todos[todo_id]

            if self._save_todos(user_id, todos):
                logger.info("todo_deleted", user_id=user_id, todo_id=todo_id)
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
