class ImproperlyConfigured(Exception):
    """
    Framework is somehow improperly configured
    """

    pass


class OutOfScopeException(Exception):
    """
    Used by BaseCase methods when setUp() is skipped
    """


class TimeLimitExceededException(Exception):
    pass
