"""
Lightweight registry for AI Intelligence System engines.
"""


from app.ai.base_engine import BaseEngine
from app.ai.exceptions import EngineRegistrationException


class EngineRegistry:
    """
    Stores and looks up already-constructed BaseEngine instances by
    their string `name`.

    The registry only holds references; it never constructs or owns the
    lifecycle of an engine. Registration is explicit — an engine must be
    instantiated elsewhere (e.g. application startup) and handed to
    `register()`. The registry has no knowledge of what any particular
    engine does and remains independent of any specific workflow.
    """

    def __init__(self) -> None:
        self._engines: dict[str, BaseEngine] = {}

    def register(self, engine: BaseEngine) -> None:
        """
        Register an engine under its `name`.

        Args:
            engine: A constructed BaseEngine instance.

        Raises:
            EngineRegistrationException: If an engine is already
                registered under the same name.
        """
        if engine.name in self._engines:
            raise EngineRegistrationException(
                f"An engine named '{engine.name}' is already registered."
            )
        self._engines[engine.name] = engine

    def unregister(self, name: str) -> None:
        """
        Remove an engine from the registry by name.

        Does nothing if no engine is currently registered under `name`.
        """
        self._engines.pop(name, None)

    def get(self, name: str) -> BaseEngine:
        """
        Look up a registered engine by name.

        Args:
            name: The string identifier the engine was registered under.

        Returns:
            The registered BaseEngine instance.

        Raises:
            EngineRegistrationException: If no engine is registered
                under `name`.
        """
        try:
            return self._engines[name]
        except KeyError as exc:
            raise EngineRegistrationException(
                f"No engine named '{name}' is registered."
            ) from exc

    def is_registered(self, name: str) -> bool:
        """Return True if an engine is currently registered under `name`."""
        return name in self._engines

    def list_engines(self) -> list[str]:
        """Return the names of all currently registered engines."""
        return list(self._engines.keys())