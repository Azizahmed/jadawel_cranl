"""The fork's workspace-level VIEWER role (#36).

Upstream's OSS permission model only has ADMIN and MEMBER; the richer role
system lived in the enterprise plugin this fork deletes. This module adds a
third workspace membership role, VIEWER, as an additive permission manager:

* the role is stored on the existing ``WorkspaceUser.permissions`` CharField
  (a plain string, so no schema change and no migration);
* the manager denies VIEWER members the operations that mutate a view's
  *configuration* — decorations, filters, filter groups, sortings and group
  bys — while leaving every read path untouched. Row data and view listings
  behave exactly as for MEMBER, so a viewer sees the same tables, rows and
  row colors as everyone else;
* for any other role (or any other operation) the manager stays silent, and
  the decision falls through to the core ``basic`` manager unchanged.

The manager is inserted before ``basic`` in ``settings.PERMISSION_MANAGERS``
from ``ArabaseConfig.ready()``, so no core file is edited.
"""

from typing import List

from jadawel.core.exceptions import UserInvalidWorkspacePermissionsError
from jadawel.core.models import WorkspaceUser
from jadawel.core.registries import PermissionManagerType
from jadawel.core.subjects import UserSubjectType

WORKSPACE_USER_PERMISSION_VIEWER = "VIEWER"


class ViewerRolePermissionManagerType(PermissionManagerType):
    """Denies view-configuration mutations for VIEWER workspace members."""

    type = "viewer_role"
    supported_actor_types = [UserSubjectType.type]

    # Operation type names (not classes) so this module never has to import
    # from `contrib.database` and risk a circular import at app load time.
    VIEWER_DENIED_OPERATIONS: List[str] = [
        # Row coloring and the other view decoration resources.
        "database.table.view.create_decoration",
        "database.table.view.decoration.update",
        "database.table.view.decoration.delete",
        # View filters and nested filter groups.
        "database.table.view.create_filter",
        "database.table.view.filter.update",
        "database.table.view.filter.delete",
        "database.table.view.create_filter_group",
        "database.table.view.filter_group.update",
        "database.table.view.filter_group.delete",
        # Sortings and group bys.
        "database.table.view.create_sort",
        "database.table.view.sort.update",
        "database.table.view.sort.delete",
        "database.table.view.create_group_by",
        "database.table.view.group_by.update",
        "database.table.view.group_by.delete",
    ]

    def _viewer_user_ids(self, workspace, actors, include_trash=False):
        """Map of user id -> is VIEWER, for the given actors of a workspace."""

        manager = (
            WorkspaceUser.objects_and_trash if include_trash else WorkspaceUser.objects
        )
        return {
            workspace_user.user_id: workspace_user.permissions
            == WORKSPACE_USER_PERMISSION_VIEWER
            for workspace_user in manager.filter(
                workspace=workspace, user_id__in=[actor.id for actor in actors]
            )
        }

    def check_multiple_permissions(self, checks, workspace=None, include_trash=False):
        if workspace is None:
            return {}

        gated_checks = [
            check
            for check in checks
            if check.operation_name in self.VIEWER_DENIED_OPERATIONS
        ]
        if not gated_checks:
            return {}

        is_viewer_by_user_id = self._viewer_user_ids(
            workspace, {check.actor for check in gated_checks}, include_trash
        )

        permission_by_check = {}
        for check in gated_checks:
            if is_viewer_by_user_id.get(check.actor.id, False):
                permission_by_check[check] = UserInvalidWorkspacePermissionsError(
                    check.actor, workspace, check.operation_name
                )
        return permission_by_check

    def get_permissions_object(self, actor, workspace=None, include_trash=False):
        if workspace is None:
            return None

        manager = (
            WorkspaceUser.objects_and_trash if include_trash else WorkspaceUser.objects
        )
        try:
            workspace_user = manager.get(user_id=actor.id, workspace_id=workspace.id)
        except WorkspaceUser.DoesNotExist:
            return None

        if workspace_user.permissions != WORKSPACE_USER_PERMISSION_VIEWER:
            return None

        return {
            "viewer_denied_operations": sorted(self.VIEWER_DENIED_OPERATIONS),
        }
