"""End-to-end integration tests for the complete workflow."""

import os
from pathlib import Path

import pytest

from dataforge.graph.workflow import create_graph
from dataforge.core.state import GraphState

__all__ = ["TestEndToEndWorkflow"]