import os
import tempfile
from pathlib import Path
import pytest

os.environ["AVATAR_DATA_DIR"] = tempfile.mkdtemp()
os.environ["AVATAR_DB_PATH"] = str(Path(os.environ["AVATAR_DATA_DIR"]) / "test.db")

from app.agent import create_root_agent, AGENT_MODEL, AGENT_GENERATE_CONTENT_CONFIG

def test_agent_graph():
    root = create_root_agent()
    
    # Asserting root properties
    assert root.name == "AvatarCoordinator"
    assert root.model == AGENT_MODEL
    
    # Validate GenerateContentConfig
    assert root.generate_content_config == AGENT_GENERATE_CONTENT_CONFIG
    
    # Check that tools include the orchestrator sub-agents and basic tools
    # By default google_search, preload_memory are functions.
    # AgentTools wrap sub-agents.
    has_research = False
    has_maint = False
    has_composer = False
    
    for tool in root.tools:
        agent_obj = getattr(tool, 'agent', None)
        if agent_obj is not None: # It is an AgentTool wrapper
            if agent_obj.name == "ResearchSpecialist":
                has_research = True
                # Validate the orchestrator parts inherit config
                assert agent_obj.generate_content_config == AGENT_GENERATE_CONTENT_CONFIG
            elif agent_obj.name == "MemoryMaintenanceAgent":
                has_maint = True
            elif agent_obj.name == "ResponseComposer":
                has_composer = True
                
    assert has_research, "ResearchSpecialist missing from root tools"
    assert has_maint, "MemoryMaintenanceAgent missing from root tools"
    assert has_composer, "ResponseComposer missing from root tools"
