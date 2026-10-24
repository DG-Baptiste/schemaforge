"""Domain errors exposed by SchemaForge."""


class SchemaForgeError(Exception):
    """Base error for user-facing failures."""


class ModelAPIError(SchemaForgeError):
    """The model service returned an invalid or unsuccessful response."""


class ExtractionError(SchemaForgeError):
    """No valid extraction was produced after all attempts."""
