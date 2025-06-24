"""Thrasio IQ Worker Service Application."""

__version__ = "1.0.0"
__author__ = "Thrasio IQ Team"
__description__ = "AI-powered data analysis worker service"

from .core import get_settings

# Initialize settings on import
settings = get_settings()

__all__ = [
    "settings"
]