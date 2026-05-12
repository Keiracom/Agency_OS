"""Cognee integration package — sole call surface is src.cognee.client."""

from src.cognee.client import add, cognify, memify, search

__all__ = ["add", "cognify", "memify", "search"]
