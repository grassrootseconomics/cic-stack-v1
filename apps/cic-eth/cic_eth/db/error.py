class TxStateChangeError(Exception):
    """Raised when an invalid state change of a queued transaction occurs
    """
    pass


class UnknownConvertError(Exception):
    """Raised when a non-existent convert to transaction subtask is requested
    """
