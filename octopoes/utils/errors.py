"""Error utilities."""

import functools

import pydantic


class ValidationError(Exception):
    """Represents validation errors."""

    ...


def validation_handler(func):
    """Wrap function to handle pydantic validation errors."""

    @functools.wraps(func)
    def inner_function(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except pydantic.error_wrappers.ValidationError as exc:
            raise ValidationError("Not able to parse response from external service.") from exc

    return inner_function
