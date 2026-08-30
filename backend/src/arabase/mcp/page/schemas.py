from __future__ import annotations

from pydantic import BaseModel, Field


class ListPageViewsInput(BaseModel):
    table_id: int = Field(..., description="The ID of the table to list page views of.")


class GetPageViewInput(BaseModel):
    view_id: int = Field(..., description="The ID of the page view to read.")
    include_rows: bool = Field(
        True,
        description=(
            "Include a small sample of the view's rows so you can see the real "
            "shape of the data before writing code against it."
        ),
    )


class CreatePageViewInput(BaseModel):
    table_id: int = Field(
        ..., description="The ID of the table the page view belongs to."
    )
    name: str = Field(..., description="The name of the view, shown in the sidebar.")
    html: str | None = Field(
        None,
        description=(
            "The page's HTML document. Call get_page_view on an existing page "
            "first if you have not read the runtime contract yet — the page runs "
            "sandboxed with no network access, which changes how you write it."
        ),
    )
    protected_field_ids: list[int] = Field(
        default_factory=list,
        description=(
            "Stable IDs of protected fields the artifact intends to expose. "
            "Supplying any ID creates a pending draft that requires human approval."
        ),
    )
    audience: str = Field(
        "authenticated",
        description="Approval audience: authenticated or public.",
    )


class UpdatePageViewInput(BaseModel):
    view_id: int = Field(..., description="The ID of the page view to update.")
    html: str | None = Field(
        None,
        description=(
            "The full replacement HTML document. Omit to leave the page as it is. "
            "This overwrites, it does not patch; the previous version is kept as a "
            "revision so it can be restored."
        ),
    )
    name: str | None = Field(None, description="A new name for the view.")
    allow_external_resources: bool | None = Field(
        None,
        description=(
            "Allow the page to load scripts, styles and fonts from the CDN "
            "allowlist. Off by default. Turning it on widens what the page can "
            "reach, so ask the user before setting it."
        ),
    )
    row_limit: int | None = Field(
        None,
        description=(
            "How many rows to hand the page, 1-1000. Values above the maximum "
            "are clamped rather than rejected."
        ),
    )
    protected_field_ids: list[int] = Field(
        default_factory=list,
        description=(
            "Stable IDs of protected fields the replacement artifact intends to expose. "
            "Supplying any ID creates a pending draft that requires human approval."
        ),
    )
    audience: str = Field(
        "authenticated",
        description="Approval audience: authenticated or public.",
    )


class ListPageViewRevisionsInput(BaseModel):
    view_id: int = Field(..., description="The ID of the page view.")


class RestorePageViewRevisionInput(BaseModel):
    view_id: int = Field(..., description="The ID of the page view.")
    revision_id: int = Field(
        ..., description="The ID of the revision to restore, from list_page_revisions."
    )
    protected_field_ids: list[int] = Field(
        default_factory=list,
        description="Protected field IDs to expose in the restored artifact.",
    )
    audience: str = Field(
        "authenticated",
        description="Approval audience: authenticated or public.",
    )
