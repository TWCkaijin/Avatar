from google.adk.agents import Agent
from google.adk.agents.run_config import RunConfig
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import google_search
from dotenv import load_dotenv
from google.genai import types

load_dotenv()

root_agent = Agent(
    name="planner_agent",
    model="gemini-2.5-flash",
    description="Agent tasked with generating creative and fun dating plan suggestions",
    instruction="""
        You are a specialized AI assistant tasked with generating creative and fun plan suggestions.

        Request:
        For the upcoming weekend, specifically from **[START_DATE_YYYY-MM-DD]** to **[END_DATE_YYYY-MM-DD]**, in the location specified as **[TARGET_LOCATION_NAME_OR_CITY_STATE]** (if latitude/longitude are provided, use these: Lat: **[TARGET_LATITUDE]**, Lon: **[TARGET_LONGITUDE]**), please generate a distinct dating plan suggestions.

        Constraints and Guidelines for Suggestions:
        1.  Creativity & Fun: Plans should be engaging, memorable, and offer a good experience for a date.
        2.  Budget: All generated plans should aim for a moderate budget (conceptually "$$"), meaning they should be affordable yet offer good value, without being overly cheap or extravagant. This budget level should be *reflected in the choice of activities and venues*, but **do not** explicitly state "Budget: $$" in the `plan_description`.
        3.  Interest Alignment:
               Consider the following user interests: **[COMMA_SEPARATED_LIST_OF_INTERESTS, e.g., outdoors, arts & culture, foodie, nightlife, unique local events, live music, active/sports]**. Tailor suggestions specifically to these where possible. The plan should *embody* these interests.
               Fallback: If specific events or venues perfectly matching all listed user interests cannot be found for the specified weekend, you should create a creative and fun generic dating plan that is still appealing, suitable for the location, and adheres to the moderate budget. This plan should still sound exciting and fun, even if it's more general.
        4.  Current & Specific: Prioritize finding specific, current events, festivals, pop-ups, or unique local venues operating or happening during the specified weekend dates. If exact current events cannot be found, suggest appealing evergreen options or implement the fallback generic plan.
        5.  Location Details: For each place or event mentioned within a plan, you MUST provide its name, precise latitude, precise longitude, and a brief, helpful description.
        6.  Maximum Activities: The plan must contain a maximum of 3 distinct activities.

        RETURN PLAN in MARKDOWN FORMAT
    """,
    tools=[google_search]
)


def main() -> None:
    prompt = (
        "For the upcoming weekend from 2026-04-25 to 2026-04-26 in Taipei, Taiwan, "
        "generate one distinct dating plan with max 3 activities, tailored to interests: "
        "outdoors, foodie, live music. For each place, include name, latitude, longitude, "
        "and a short description. Return in markdown."
    )

    runner = Runner(
        agent=root_agent,
        session_service=InMemorySessionService(),
        app_name="day_trip_example",
        auto_create_session=True,
    )

    content = types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
    result_text = ""

    for event in runner.run(
        user_id="example-user",
        session_id="day-trip-session",
        new_message=content,
        run_config=RunConfig(),
    ):
        if not event.is_final_response():
            continue
        if not event.content or not event.content.parts:
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
