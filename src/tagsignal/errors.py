"""User-facing error types and safe messages."""


class DataProblem(ValueError):
    """Raised when an input table cannot support the declared analysis."""


MEMORY_MESSAGE = (
    "There is not enough memory on this computer for this file or step. Close other programs, keep only the columns "
    "you need, or split the observations into batches."
)


def friendly_message(exc: Exception) -> str:
    if isinstance(exc, DataProblem):
        return str(exc)
    if isinstance(exc, MemoryError):
        return MEMORY_MESSAGE
    if isinstance(exc, ValueError):
        return str(exc)
    return "Tag Signal could not complete the analysis. Check the data contract and try again."

