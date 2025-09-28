import pytest
from src.exceptions import (
    ImageServiceException,
    InvalidRequestError,
    ImageNotFoundError,
    S3Error,
    DatabaseError,
)


def test_exception_hierarchy():
    assert issubclass(InvalidRequestError, ImageServiceException)
    assert issubclass(ImageNotFoundError, ImageServiceException)
    assert issubclass(S3Error, ImageServiceException)
    assert issubclass(DatabaseError, ImageServiceException)


def test_exception_message():
    with pytest.raises(InvalidRequestError, match="Test message"):
        raise InvalidRequestError("Test message")