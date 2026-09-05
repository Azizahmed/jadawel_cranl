from rest_framework.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

ERROR_KANBAN_VIEW_HAS_NO_SINGLE_SELECT_FIELD = (
    "ERROR_KANBAN_VIEW_HAS_NO_SINGLE_SELECT_FIELD",
    HTTP_400_BAD_REQUEST,
    "The kanban view does not have a single select field to group by.",
)

ERROR_KANBAN_VIEW_STACK_DOES_NOT_EXIST = (
    "ERROR_KANBAN_VIEW_STACK_DOES_NOT_EXIST",
    HTTP_404_NOT_FOUND,
    "The requested stack is not an option of the kanban view's single select field.",
)
