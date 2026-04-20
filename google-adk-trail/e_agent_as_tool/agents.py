from google.adk.tools import google_search
from google.adk.tools.agent_tool import AgentTool
from google.adk.agents import LlmAgent
from google.adk.agents.run_config import RunConfig
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from dotenv import load_dotenv
from google.genai import types
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

SEARCH_TOOL_CONFIG = types.GenerateContentConfig.model_validate(
    {"tool_config": {"include_server_side_tool_invocations": True}}
)


# --- 1. Define the Specialist "Tool" Agents ---
# These are the expert agents that our main agent will use as tools.

location_scout_agent = LlmAgent(
    name="LocationScoutAgent",
    model="gemini-2.5-flash",
    tools=[google_search],
    description="Finds a specific type of location (like a museum, restaurant, or park) based on a user's request in or around Sunnyvale, CA. Returns only the name of the location.",
    instruction="""
    You are a location scout. Based on the user's request (e.g., 'an art museum', 'a cheap but good taco place'), find the best matching place and output ONLY its name.
    Example Request: "a museum about technology"
    Example Output: "The Computer History Museum"
    """,
    generate_content_config=SEARCH_TOOL_CONFIG,
)

logistics_validator_agent = LlmAgent(
    name="LogisticsValidatorAgent",
    model="gemini-2.5-flash",
    tools=[google_search],
    description="Calculates the travel time between two locations or finds the operating hours for a single location.",
    instruction="""
    You are a logistics validator. Your task is to provide key logistical information.
    - If the request has two locations, calculate the driving travel time between them and output only the time (e.g., '15 minutes').
    - If the request has one location, find its typical operating hours for a weekday and output only the hours (e.g., '9:00 AM - 5:00 PM').
    """,
    generate_content_config=SEARCH_TOOL_CONFIG,
)

# --- 2. Define the Main "Architect" Agent ---
# This agent orchestrates the tool agents to build a plan conversationally.

trip_architect_agent = LlmAgent(
    name="TripArchitectAgent",
    model="gemini-2.5-flash",
    instruction="""
    You are an Autonomous Trip Architect. Your goal is to take a single user request and build a complete, logistically-sound itinerary in one go, without asking for feedback. You must make intelligent decisions and corrections on the user's behalf.

    Follow this exact internal process:
    1.  **Deconstruct Request:** Analyze the user's query to identify the required components (e.g., 'one museum', 'one restaurant').
    2.  **Find Primary Activity:** Use the `LocationScoutAgent` tool to find the main activity mentioned in the query.
    3.  **Find a Meal Location:** Use the `LocationScoutAgent` tool to find a restaurant that fits the query.
    4.  **CRITICAL VALIDATION:** Use the `LogisticsValidatorAgent` tool to check the travel time between the activity and the restaurant.
    5.  **AUTONOMOUS SELF-CORRECTION:**
        - **IF** the travel time is acceptable (under 20 minutes), proceed.
        - **ELSE (if travel time is too long):** You MUST discard the restaurant you found. Then, use the `LocationScoutAgent` tool AGAIN with a new, more specific query to find a restaurant that is explicitly *near* the primary activity.
    6.  **FINALIZE AND PRESENT:** Once you have a pair of locations with a good travel time, create a final, summarized plan. Include the names of both locations and the estimated travel time between them. Present this as your final answer.
    """,
    # --- This is the key part of the pattern ---
    tools=[
        AgentTool(agent=location_scout_agent),
        AgentTool(agent=logistics_validator_agent),
    ],
)

# --- 3. Set the Root Agent ---
root_agent = trip_architect_agent
print("🤖 Trip Architect Agent, with agents as tools, is ready.")


def main() -> None:
    prompt = "Plan one museum and one nearby restaurant in Taipei, and include estimated travel time between them."
    runner = Runner(
        agent=root_agent,
        session_service=InMemorySessionService(),
        app_name="e_agent_as_tool_example",
        auto_create_session=True,
    )
    content = types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
    result_text = ""

    for event in runner.run(
        user_id="example-user",
        session_id="e-agent-tool-session",
        new_message=content,
        run_config=RunConfig(),
    ):
        if not event.is_final_response() or not event.content or not event.content.parts:
            continue
        for part in event.content.parts:
            text = getattr(part, "text", None)
            if isinstance(text, str) and text.strip():
                result_text = text.strip()

    if not result_text:
        raise RuntimeError("No response text returned from agent")

    print(result_text)


if __name__ == "__main__":
    main()
