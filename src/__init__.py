"""
MCP Legal Assistant Source Package
"""
import sys
from pathlib import Path

# Add src to path for relative imports
src_path = Path(__file__).parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))
