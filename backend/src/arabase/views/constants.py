"""Limits for the HTML page view.

They live in their own module because the model, the view type's validation, the
MCP tools and the tests all need the same numbers, and importing
``arabase.views.models`` from a tool module would drag Django's app registry in
earlier than it needs to be.
"""

# Postgres does not enforce a length on ``text``, so the cap is applied in
# ``HtmlPageViewType.prepare_values``. 512 KB is far more than a hand-written
# page needs and still small enough that a runaway model cannot fill the table.
MAX_HTML_LENGTH = 512 * 1024

# How many rows are handed to the page. A page is a rendering surface, not an
# export: without a ceiling, opening a page view on a 100k-row table serialises
# the whole table into a postMessage payload and locks up the viewer's browser.
DEFAULT_ROW_LIMIT = 200
MAX_ROW_LIMIT = 1000

# Revisions kept per page. Authoring happens through an AI over MCP, so a single
# bad tool call can overwrite an afternoon's work; this is the undo.
MAX_REVISIONS = 20
