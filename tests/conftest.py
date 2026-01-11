"""
Pytest configuration file.
Ensures the src module can be imported from tests.
"""

import sys
from pathlib import Path

# Add the project root directory to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
