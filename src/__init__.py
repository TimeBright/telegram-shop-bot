"""
Main package initialization for the Telegram bot application.
Contains review handler and shop modules.
"""

from . import review_handler
from . import shop

__all__ = ['review_handler', 'shop']
