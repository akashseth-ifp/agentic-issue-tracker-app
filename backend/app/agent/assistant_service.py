import json
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.agent.tools import TOOLS, execute_tool

MAX_ITERATIONS = 10

BASE_SYSTEM_PROMPT = """
You are a dedicated assistant for an issue tracking system. Your sole purpose is to help users
query, create, and update issues in this tracker. You are NOT a general-purpose AI assistant.

STRICT DOMAIN BOUNDARY:
If the user's request is unrelated to issue tracking (e.g. coding help, general knowledge,
weather, jokes, or anything outside this product), do NOT call any tool. Respond with:
  "I can only help with the issue tracker. Try: 'Show open issues', 'Create a bug for X',
   or 'Close all in-progress issues'."
Never apologise excessively — one short sentence of redirection is enough.

WORKFLOW RULES:
- For bulk operations, ALWAYS call count_issues first to understand scope, then bulk_update_status.
- For any question about counts or totals, ALWAYS use count_issues — never use list_issues just to count.
- list_issues returns at most 20 results. If has_more is true, tell the user how many were returned
  and invite them to ask for the next page. Do NOT paginate automatically.

Always be specific in your final response: mention counts, IDs, or titles of affected issues.
"""


async def run_agent(instruction: str, db: AsyncSession, cursor: str | None = None) -> dict:
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    system_prompt = BASE_SYSTEM_PROMPT
    if cursor:
        system_prompt += (
            f"\n\nPending cursor: {cursor}. "
            "If the user is asking for the next page of results, pass this as the `cursor` parameter to list_issues."
        )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": instruction},
    ]
    mutations_made = False
    next_cursor = None

    for _ in range(MAX_ITERATIONS):
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )

        message = response.choices[0].message
        finish_reason = response.choices[0].finish_reason

        if finish_reason == "stop" or not message.tool_calls:
            return {
                "response": message.content or "Done.",
                "mutations_made": mutations_made,
                "next_cursor": next_cursor,
            }

        messages.append(message)

        for tool_call in message.tool_calls:
            result = await execute_tool(
                tool_call.function.name,
                json.loads(tool_call.function.arguments),
                db,
            )
            if result.get("is_mutation"):
                mutations_made = True
            if result.get("next_cursor"):
                next_cursor = result["next_cursor"]
            elif tool_call.function.name == "list_issues":
                next_cursor = None
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result),
            })

    return {
        "response": "I was unable to complete the request within the allowed steps. Please try rephrasing.",
        "mutations_made": mutations_made,
        "next_cursor": None,
    }
