from abc import ABC

from jadawel.core.registries import OperationType


class DashboardOperationType(OperationType, ABC):
    context_scope_name = "dashboard"
