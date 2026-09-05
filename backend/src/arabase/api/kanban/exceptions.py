class KanbanViewHasNoSingleSelectField(Exception):
    """Raised when a kanban view without a grouping field is listed."""


class KanbanViewStackDoesNotExist(Exception):
    """Raised when the requested stack is not an option of the grouping field."""
