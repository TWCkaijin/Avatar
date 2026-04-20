from google.adk.tools import google_search
from google.adk.agents import Agent, ParallelAgent, SequentialAgent
from google.adk.agents.run_config import RunConfig
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from dotenv import load_dotenv
from google.genai import types
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
print(PROJECT_ROOT)
load_dotenv(PROJECT_ROOT / ".env")
MODEL="gemini-2.5-flash"

# Specialist Agent 1
museum_finder_agent = Agent(
    name="museum_finder_agent", model=MODEL, tools=[google_search],
    instruction="You are a museum expert. Find the best museum based on the user's query. Output only the museum's name.",
    output_key="museum_result",
)

# Specialist Agent 2
concert_finder_agent = Agent(
    name="concert_finder_agent", model=MODEL, tools=[google_search],
    instruction="You are an events guide. Find a concert based on the user's query. Output only the concert name and artist.",
    output_key="concert_result",
)

# We can reuse our foodie_agent for the third parallel task!
# Just need to give it a new output_key for this workflow.
# restaurant_finder_agent = foodie_agent.copy(update={"output_key": "restaurant_result"})
restaurant_finder_agent = Agent(
    name="restaurant_finder_agent",
    model=MODEL,
    tools=[google_search],
    instruction="""You are an expert food critic. Your goal is to find the best restaurant based on a user's request.

    When you recommend a place, you must output *only* the name of the establishment.
    For example, if the best sushi is at 'Jin Sho', you should output only: Jin Sho
    """,
    output_key="restaurant_result",  # Set the correct output key for this workflow
)


# ✨ The ParallelAgent runs all three specialists at once ✨
parallel_research_agent = ParallelAgent(
    name="parallel_research_agent",
    sub_agents=[museum_finder_agent, concert_finder_agent, restaurant_finder_agent]
)

# Agent to synthesize the parallel results
synthesis_agent = Agent(
    name="synthesis_agent", model=MODEL,
    instruction="""You are a helpful assistant. Combine the following research results into a clear, bulleted list for the user.
    - Museum: {museum_result}
    - Concert: {concert_result}
    - Restaurant: {restaurant_result}
    """
)

# ✨ The SequentialAgent runs the parallel search, then the synthesis ✨
parallel_planner_agent = SequentialAgent(
    name="parallel_planner_agent",
    sub_agents=[parallel_research_agent, synthesis_agent],
    description="A workflow that finds multiple things in parallel and then summarizes the results."
)

root_agent = parallel_planner_agent


def main() -> None:
    prompt = "Plan a fun day in Taipei with one museum, one live concert idea, and one dinner recommendation."
    runner = Runner(
        agent=root_agent,
        session_service=InMemorySessionService(),
        app_name="c_parallel_agent_example",
        auto_create_session=True,
    )
    content = types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
    result_text = ""

    for event in runner.run(
        user_id="example-user",
        session_id="c-parallel-session",
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