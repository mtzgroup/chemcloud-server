class BaseChemCloudError(Exception):
    """Base class for all ChemCloud errors."""


class ResultNotFoundError(BaseChemCloudError):
    """Raised when a result is not found in the database."""

    def __init__(self, result_id: str):
        super().__init__(f"Result id '{result_id}', not found.")
