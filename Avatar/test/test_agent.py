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
    has_orch = False
    has_maint = False
    
    for tool in root.tools:
        agent_obj = getattr(tool, 'agent', None)
        if agent_obj is not None: # It is an AgentTool wrapper
            if agent_obj.name == "ConversationOrchestrator":
                has_orch = True
                # Validate the orchestrator inherits config
                assert agent_obj.generate_content_config == AGENT_GENERATE_CONTENT_CONFIG
            elif agent_obj.name == "MemoryMaintenanceAgent":
                has_maint = True
                
    assert has_orch, "ConversationOrchestrator missing from root tools"
    assert has_maint, "MemoryMaintenanceAgent missing from root tools"
