"""Lightweight errors that routes can handle without importing ML libraries."""


class TextModelUnavailable(Exception):
    pass
