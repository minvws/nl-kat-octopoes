"""Connector errors."""

import functools

import pydantic


class ValidationError(Exception):
    """Validation error."""

    pass


def exception_handler(func):
    """Wrap function in exception handler."""

    @functools.wraps(func)
    def inner_function(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except pydantic.error_wrappers.ValidationError as exc:
            raise ValidationError("Not able to parse response from external service.") from exc

    return inner_function
