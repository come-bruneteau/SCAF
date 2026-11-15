"""Simple in-process pub/sub. Plugins never need to read raw UDP."""

from collections import defaultdict
from collections.abc import Callable
from core.models.aircraft_state import AircraftState

StateHandler = Callable[[AircraftState], None]

class Dispatcher:
    def __init__(self) -> None:
        self._handlers: dict[str, list[StateHandler]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: StateHandler) -> None:
        if handler not in self._handlers[event_type]:
            self._handlers[event_type].append(handler)

    def publish(self, event_type: str, state: AircraftState) -> None:
        for handler in tuple(self._handlers.get(event_type, [])):
            handler(state)
