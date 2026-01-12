class RDBMSException(Exception):
    pass


class TableNotFound(RDBMSException):
    pass


class SchemaError(RDBMSException):
    pass


class ConstraintViolation(RDBMSException):
    pass


class IndexErrorRDB(RDBMSException):
    pass
