"""
Resume Analysis workflow (HIRE-AI-106).

This module contains AI application-layer orchestration ONLY. It
coordinates existing, unmodified AI framework components and engines
to fulfil `POST /api/v1/resume/analyze`. It contains:

    - no parsing logic (delegated to ResumeIntelligenceEngine)
    - no skill/experience/matching logic (delegated to their engines)
    - no database logic
    - no new AIContext, BaseEngine, AIOrchestrator, or EngineRegistry
      behavior

Per CTO architectural decision: BaseEngine and AIOrchestrator remain
generic and are never modified to auto-propagate data between engines.
Bridging ResumeIntelligenceEngine's output into
`context.data["candidate_profile"]`, and supplying
`context.data["job_requirement"]`, are explicit application-layer
responsibilities performed here — not inside the framework or inside
any engine.

Consuming engine outputs: the four engines do NOT share one output
shape, so this workflow reads each one according to its own actual
contract rather than assuming a single dict/model convention:

    - ResumeIntelligenceEngine returns `profile.model_dump()` as
      `output` (see resume_intelligence.py). Reconstructing a
      CandidateProfile from it here is not optional convenience — it
      is required, because SkillIntelligenceEngine,
      ExperienceIntelligenceEngine, and CandidateMatchingEngine each
      `isinstance()`-check `context.data["candidate_profile"]` against
      CandidateProfile in their own `validate_context` (see e.g.
      skill_intelligence.py). A plain dict would fail that check.
    - SkillIntelligenceEngine and ExperienceIntelligenceEngine also
      return `intelligence.model_dump()` as `output` (see
      skill_intelligence.py, experience_intelligence.py). Nothing
      downstream needs these as live model instances — they are
      terminal outputs consumed only by ResumeAnalysisData below — so
      they are passed through as-is and left for Pydantic to validate
      at that model boundary, rather than manually reconstructed here.
    - CandidateMatchingEngine's contract is different again: it
      returns the live CandidateMatching *instance* directly under
      `output["candidate_matching"]` (see candidate_matching.py:
      `output={"candidate_matching": matching}`), not a dumped dict.
      It is consumed as-is.

Orchestration sequence:
    1. Build a fresh AIContext for this request.
    2. Populate context.data["resume_text"].
    3. Run ResumeIntelligenceEngine directly (not through the
       orchestrator, since nothing precedes it).
    4. Reconstruct a CandidateProfile from its output (required by the
       downstream engines' own contracts — see above) and write it to
       context.data["candidate_profile"].
    5. Populate context.data["job_requirement"].
    6. Run the remaining three engines through AIOrchestrator, in
       dependency order.
    7. Aggregate each engine's output — read according to its own
       contract, not a uniform assumption — into a single
       ResumeAnalysisData for the API layer to return.
"""

from app.ai.context import AIContext
from app.ai.engines.candidate_matching import CandidateMatchingEngine
from app.ai.engines.experience_intelligence import ExperienceIntelligenceEngine
from app.ai.engines.resume_intelligence import ResumeIntelligenceEngine
from app.ai.engines.skill_intelligence import SkillIntelligenceEngine
from app.ai.orchestrator import AIOrchestrator
from app.ai.registry import EngineRegistry
from app.models.candidate import CandidateProfile
from app.models.job_requirement import JobRequirement
from app.schemas.resume_analysis import ResumeAnalysisData

# Execution order for the engines run through AIOrchestrator, after
# ResumeIntelligenceEngine has already populated candidate_profile.
# Order matters only in that all three currently depend solely on
# candidate_profile/job_requirement rather than on each other, but is
# kept explicit and fixed rather than inferred.
_DOWNSTREAM_ENGINE_NAMES: list[str] = [
    "skill_intelligence",
    "experience_intelligence",
    "candidate_matching",
]


def _build_registry() -> EngineRegistry:
    """
    Build a fresh EngineRegistry populated with the four existing
    engines.

    A new registry is constructed on every call rather than cached as
    module-level shared state. EngineRegistry carries no documented
    singleton contract in the framework itself — every existing test
    (see test_candidate_matching.py, test_ai_framework.py) constructs
    its own fresh `EngineRegistry()` per case — so this workflow
    introduces no shared state beyond what the framework already
    provides. Engines are cheap, stateless algorithm holders (the only
    instance attribute BaseEngine defines is `name`), so building four
    of them per call has no meaningful cost.
    """
    registry = EngineRegistry()
    registry.register(ResumeIntelligenceEngine())
    registry.register(SkillIntelligenceEngine())
    registry.register(ExperienceIntelligenceEngine())
    registry.register(CandidateMatchingEngine())
    return registry


async def run_resume_analysis(
    resume_text: str,
    job_requirement: JobRequirement,
    *,
    registry: EngineRegistry | None = None,
) -> ResumeAnalysisData:
    """
    Run the full resume analysis pipeline and return the aggregated
    result.

    Args:
        resume_text: Raw resume text to analyze.
        job_requirement: Job posting to match the parsed candidate
            against.
        registry: Optional EngineRegistry to use instead of building a
            fresh default one. Exists so tests can inject a registry
            with a substitute/failing engine to exercise error
            propagation, without this workflow containing any
            test-specific branching.

    Returns:
        A ResumeAnalysisData bundling the CandidateProfile and every
        downstream engine's output.

    Raises:
        AIException: Propagated as-is from whichever engine (or the
            orchestrator) raised it. This function performs no
            exception translation of its own, per the existing AI
            exception framework.
    """
    active_registry = registry if registry is not None else _build_registry()
    context = AIContext(workflow_name="resume_analysis")

    # Step 1-3: resume intelligence has no upstream dependency, so it
    # is run directly rather than through the orchestrator.
    context.data["resume_text"] = resume_text
    resume_engine = active_registry.get("resume_intelligence")
    resume_result = await resume_engine.run(context)

    # Step 4: explicit application-layer bridge — NOT framework
    # behavior. Required because downstream engines' validate_context
    # isinstance-checks candidate_profile against CandidateProfile
    # (see module docstring); resume_result.output is a plain dict
    # (profile.model_dump()), so this reconstruction is mandated by
    # the downstream engines' own existing contracts, not an
    # unnecessary conversion introduced here.
    candidate_profile = CandidateProfile(**resume_result.output)
    context.data["candidate_profile"] = candidate_profile

    # Step 5: application-layer bridge for the matching engine's input.
    context.data["job_requirement"] = job_requirement

    # Step 6: remaining engines share a dependency shape (candidate_profile
    # [+ job_requirement for matching]) and run through the unmodified
    # AIOrchestrator, in the given order.
    orchestrator = AIOrchestrator(active_registry)
    workflow_result = await orchestrator.run(context, _DOWNSTREAM_ENGINE_NAMES)

    results_by_engine = {
        result.engine_name: result for result in workflow_result.results
    }

    # SkillIntelligenceEngine / ExperienceIntelligenceEngine: their
    # `output` is already each model's `.model_dump()`. These are
    # terminal outputs — nothing downstream isinstance-checks them —
    # so they're passed through unchanged; ResumeAnalysisData's typed
    # fields validate/coerce them into SkillIntelligence /
    # ExperienceIntelligence when the response model is constructed
    # below. No manual reconstruction here.
    skill_intelligence_output = results_by_engine["skill_intelligence"].output
    experience_intelligence_output = results_by_engine[
        "experience_intelligence"
    ].output

    # CandidateMatchingEngine: its contract returns the live
    # CandidateMatching instance directly under
    # output["candidate_matching"] (not a dumped dict — see module
    # docstring), so it's used exactly as returned.
    candidate_matching_output = results_by_engine["candidate_matching"].output[
        "candidate_matching"
    ]

    # Step 7: aggregate for the API layer. Pydantic validates each
    # field against ResumeAnalysisData's declared types on
    # construction, so dict-shaped outputs above are coerced into
    # their models here rather than by manual reconstruction earlier.
    return ResumeAnalysisData(
        candidate_profile=candidate_profile,
        skill_intelligence=skill_intelligence_output,
        experience_intelligence=experience_intelligence_output,
        candidate_matching=candidate_matching_output,
    )