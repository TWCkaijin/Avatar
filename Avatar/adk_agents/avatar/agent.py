import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Make sure we add Avatar directory to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
    
REPO_ROOT = PROJECT_ROOT.parent
load_dotenv(REPO_ROOT / ".env")

from app.agent import create_root_agent
root_agent = create_root_agent()
