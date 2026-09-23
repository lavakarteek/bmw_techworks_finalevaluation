"""Sphinx configuration for the BMW vehicle alert documentation."""

from pathlib import Path
import sys


project = "BMW Vehicle Alert"
author = "BMW Vehicle Alert contributors"
release = "0.1.0"

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

extensions = ["sphinx.ext.autodoc", "sphinx.ext.napoleon", "sphinx.ext.viewcode"]
templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "alabaster"
