"""User-facing error types and safe messages."""


class DataProblem(ValueError):
    """Raised when an input table cannot support the declared analysis."""


def friendly_message(exc: Exception) -> str:
    if isinstance(exc, DataProblem):
        return str(exc)
    if isinstance(exc, ValueError):
        return str(exc)
    return "TagSignal could not complete the analysis. Check the data contract and try again."

