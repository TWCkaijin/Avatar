from google.adk.agents import Agent
from google.adk.tools import google_search
from google.adk.agents import Agent, SequentialAgent
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

# Note the new `output_key` and the more specific instruction.
foodie_agent = Agent(
    name="foodie_agent",
    model="gemini-2.5-flash",
    tools=[google_search],
    instruction="""You are an expert food critic. Your goal is to find the best restaurant based on a user's request.

    When you recommend a place, you must output *only* the name of the establishment and nothing else.
    For example, if the best sushi is at 'Jin Sho', you should output only: Jin Sho
    """,
    output_key="destination",  # ADK will save the agent's final response to state['destination']
    generate_content_config=SEARCH_TOOL_CONFIG,
)

# The `{destination}` placeholder is automatically filled by the ADK from the state.
transportation_agent = Agent(
    name="transportation_agent",
    model="gemini-2.5-flash",
    tools=[google_search],
    instruction="""You are a navigation assistant. Given a destination, provide clear directions.
    The user wants to go to: {destination}.

    Analyze the user's full original query to find their starting point.
    Then, provide clear directions from that starting point to {destination}.
    """,
    generate_content_config=SEARCH_TOOL_CONFIG,
)

# This agent will run foodie_agent, then transportation_agent, in that exact order.
find_and_navigate_agent = SequentialAgent(
    name="find_and_navigate_agent",
    sub_agents=[foodie_agent, transportation_agent],
    description="A workflow that first finds a location and then provides directions to it."
)

root_agent = find_and_navigate_agent


def main() -> None:
    prompt = "I am in Taipei Main Station and want a great sushi place, then give me directions to get there."
    runner = Runner(
        agent=root_agent,
        session_service=InMemorySessionService(),
        app_name="b_sequential_agent_example",
        auto_create_session=True,
    )
    content = types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
    result_text = ""

    for event in runner.run(
        user_id="example-user",
        session_id="b-sequential-session",
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