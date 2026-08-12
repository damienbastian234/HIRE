import asyncio

from app.ai.base_engine import BaseEngine
from app.ai.context import AIContext
from app.ai.orchestrator import AIOrchestrator
from app.ai.registry import EngineRegistry
from app.ai.result import ExecutionStatus, IntelligenceResult


class DemoEngine(BaseEngine):
    def __init__(self):
        super().__init__("demo_engine")

    async def execute(self, context: AIContext) -> IntelligenceResult:
        context.data["message"] = "Hello H.I.R.E."

        return IntelligenceResult(
            engine_name=self.name,
            status=ExecutionStatus.SUCCESS,
            confidence=1.0,
            output={"message": "Hello H.I.R.E."},
        )


async def main():
    registry = EngineRegistry()
    registry.register(DemoEngine())

    orchestrator = AIOrchestrator(registry)

    context = AIContext()

    workflow_result = await orchestrator.run(
        context,
        ["demo_engine"],
    )

    print(workflow_result)
    print(context.data)
    print(context.state)


asyncio.run(main())