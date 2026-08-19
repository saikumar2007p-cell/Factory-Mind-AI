import asyncio
import traceback
from backend.app.database import get_session_maker
from backend.app.routers.diagnostics import explain_machine_state, DiagnosticExplainRequest

async def main():
    try:
        sm = get_session_maker()
        async with sm() as session:
            res = await explain_machine_state(DiagnosticExplainRequest(machine_id=1), session)
            print("Success:", res)
    except Exception as e:
        print("Traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
