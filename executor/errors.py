"""Errors raised by the executor layer with messages meant for the user."""


class ApplyError(RuntimeError):
    """Raised with a user-readable message when a file cannot be applied."""
