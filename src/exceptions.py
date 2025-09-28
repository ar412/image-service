class ImageServiceException(Exception):
    pass


class InvalidRequestError(ImageServiceException):
    pass


class ImageNotFoundError(ImageServiceException):
    pass


class S3Error(ImageServiceException):
    pass


class DatabaseError(ImageServiceException):
    pass