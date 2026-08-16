class HtmlPageTooLarge(Exception):
    """Raised when the submitted page HTML is over the size cap."""


class HtmlPageViewDoesNotExist(Exception):
    """Raised when the requested HTML page view does not exist."""


class HtmlPageViewRevisionDoesNotExist(Exception):
    """Raised when the requested revision does not belong to the page."""
