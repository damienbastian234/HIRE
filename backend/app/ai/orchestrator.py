"""
AI Orchestrator: coordinates Intelligence System engines against a
shared AIContext.
"""


from app.ai.context import AIContext, WorkflowStatus
from app.ai.exceptions import AIException, OrchestrationException
from app.ai.registry import EngineRegistry
from app.ai.result import IntelligenceResult, WorkflowResult
from app.core.logging import get_logger

logger = get_logger(__name__)


class AIOrchestrator:
    """
    Coordinates the sequential execution of registered Intelligence
    System engines against a shared AIContext.

    The orchestrator depends only on the EngineRegistry and on
    BaseEngine's public `run()` contract. It never performs AI inference
    itself and holds no recruitment-specific knowledge — which engines
    make up a given workflow, and in what order, is decided entirely by
    the caller of `run()`, not by this class.

    Dependency direction is strictly one-way: the orchestrator depends
    on engines; engines must never import or reference this class.

    This ticket implements sequential orchestration only. Parallel
    execution is intentionally out of scope and may be introduced by a
    future ticket without requiring changes to the engine or registry
    contracts.
    """

    def __init__(self, registry: EngineRegistry) -> None:
        """
        Args:
            registry: The EngineRegistry this orchestrator looks up
                engines from when running a workflow.
        """
        self._registry = registry

    async def run(
        self, context: AIContext, engine_names: list[str]
    ) -> WorkflowResult:
        """
        Execute the named engines sequentially against the given context.

        Engines run one after another, in the order given by
        `engine_names`. Each engine reads from and may extend
        `context.data` before the next engine runs, so later engines in
        the sequence can build on earlier engines' output. The same
        `context` instance is passed to every engine, propagating state
        through the whole workflow.

        Throughout execution, `context.state` is kept up to date
        (`current_engine`, `completed_engines`, `progress`,
        `workflow_status`) so that any code holding a reference to
        `context` can observe workflow progress in real time, even
        before this method returns.

        Execution is fail-fast: if any engine raises, the workflow halts
        immediately and no further engines in `engine_names` are run.
        This keeps the framework's failure behavior simple and
        predictable; whether a specific future workflow should instead
        tolerate partial failures is a decision for that workflow's own
        design, not for this generic orchestrator.

        Args:
            context: The shared AIContext for this workflow.
            engine_names: Ordered list of registered engine names to run.
                An empty list is treated as a valid, trivially completed
                workflow rather than an error.

        Returns:
            A WorkflowResult containing this workflow's `workflow_id`
            and the per-engine IntelligenceResults, in execution order.

        Raises:
            EngineRegistrationException: If any name in `engine_names`
                has no registered engine.
            OrchestrationException: If a registered engine raises an
                exception that is not already an AIException.
            AIException: Propagated as-is if a registered engine raises
                an AIException (or subclass) itself.
        """
        if not engine_names:
            context.state.workflow_status = WorkflowStatus.COMPLETED
            context.state.progress = 1.0

            return WorkflowResult(
                workflow_id=context.workflow_id,
                results=[],
            )

        results: list[IntelligenceResult] = []
        total = len(engine_names)
        context.state.workflow_status = WorkflowStatus.RUNNING

        for engine_name in engine_names:
            engine = self._registry.get(engine_name)
            context.state.current_engine = engine_name

            try:
                result = await engine.run(context)
            except AIException:
                logger.exception(
                    "Workflow halted: engine '%s' failed.", engine_name
                )
                context.state.current_engine = None
                context.state.failed_engine = engine_name
                context.state.workflow_status = WorkflowStatus.FAILED
                raise
            except Exception as exc:
                logger.exception(
                    "Workflow halted: engine '%s' raised an unexpected error.",
                    engine_name,
                )
                context.state.current_engine = None
                context.state.failed_engine = engine_name
                context.state.workflow_status = WorkflowStatus.FAILED
                raise OrchestrationException(
                    f"Engine '{engine_name}' failed unexpectedly during "
                    f"orchestration."
                ) from exc

            results.append(result)
            context.state.completed_engines.append(engine_name)
            context.state.progress = len(context.state.completed_engines) / total

        context.state.current_engine = None
        context.state.workflow_status = WorkflowStatus.COMPLETED

        return WorkflowResult(workflow_id=context.workflow_id, results=results)