class NotInitializedError(Exception):
    pass


class AlreadyInitializedError(Exception):
    pass


class PleaseCommitFirstError(Exception):
    """Raised when there exists uncommitted changes in the code while trying to build out the package."""
    pass
