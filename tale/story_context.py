import math
from typing import List, Optional

from tale.scenario import Beat, BeatStatus, validate_beats
from tale.util import Context, call_periodically


class StoryContext:
    """Story progression state: a base plot plus a list of beats.

    A story either has authored beats (loaded from the story config) or
    accumulates generated ones as time progresses; there is no third path.
    """

    def __init__(self, base_story: str = "") -> None:
        self.base_story = base_story
        self.beats = []  # type: List[Beat]
        self.authored = False  # True when the beats come from the story config, False when generated on the fly
        self.progress = 0.0
        self.length = 10.0
        self.speed = 1.0

    # -- beats ---------------------------------------------------------------

    def set_beats(self, beats: List[Beat]) -> None:
        """Install authored beats. Unless statuses were authored explicitly,
        the first beat starts ACTIVE and the rest LOCKED."""
        validate_beats(beats)
        self.beats = list(beats)
        self.authored = True
        if self.beats and all(beat.status == BeatStatus.LOCKED for beat in self.beats):
            self.beats[0].status = BeatStatus.ACTIVE

    def active_beat(self) -> Optional[Beat]:
        for beat in self.beats:
            if beat.status == BeatStatus.ACTIVE:
                return beat
        return None

    def completed_beats(self) -> List[Beat]:
        return [beat for beat in self.beats if beat.status == BeatStatus.COMPLETED]

    def advance_to_next_beat(self) -> Optional[Beat]:
        """Complete the ACTIVE beat and activate the next LOCKED one.
        Returns the new ACTIVE beat, or None if there is no locked beat."""
        nxt = next((beat for beat in self.beats if beat.status == BeatStatus.LOCKED), None)
        if nxt is None:
            return None
        active = self.active_beat()
        if active is not None:
            active.status = BeatStatus.COMPLETED
        nxt.status = BeatStatus.ACTIVE
        return nxt

    def add_beat(self, description: str) -> Beat:
        """Generated stories: complete the ACTIVE beat and append a new ACTIVE
        beat with a generated id "beat-{n}". Returns the new beat."""
        active = self.active_beat()
        if active is not None:
            if active.description:
                active.status = BeatStatus.COMPLETED
            else:
                self.beats.remove(active)
        beat = Beat(id="beat-%d" % len(self.beats), description=description, status=BeatStatus.ACTIVE)
        self.beats.append(beat)
        return beat

    # -- progression ---------------------------------------------------------

    @call_periodically(10, 20)
    def increase_progress(self, ctx: Context) -> bool:
        """ increase the progress by the given amount, return True if a beat boundary was crossed """
        print("Increasing progress")
        start_progress = self.progress
        self.progress += self.speed
        if self.progress >= self.length:
            self.progress = self.length
        if self._beat_boundary_crossed(start_progress):
            ctx.driver.llm_util.advance_story_section(self)
            return True
        return False

    def _beat_boundary_crossed(self, start_progress: float) -> bool:
        """Authored beats span length/len(beats) progress each; generated
        stories advance one beat per integer progress crossing."""
        if self.authored and self.beats:
            span = self.length / len(self.beats)
            return math.floor(self.progress / span) > math.floor(start_progress / span)
        return math.floor(start_progress) != math.floor(self.progress)

    # -- rendering -----------------------------------------------------------

    def to_context(self) -> str:
        active = self.active_beat()
        return f"<story> Base plot: {self.base_story}; Active beat: {active.description if active else ''}</story>"

    def to_context_with_past(self) -> str:
        active = self.active_beat()
        past = ' '.join(beat.description for beat in self.completed_beats()) or 'This is the beginning of the story'
        return f"<story> Base plot: {self.base_story}; Past: {past}; Active beat: {active.description if active else ''}; Progress: {self.progress}/{self.length};</story>"

    # -- serialization ---------------------------------------------------------

    def from_json(self, data: dict) -> 'StoryContext':
        self.base_story = data.get("base_story", "")
        self.progress = data.get("progress", 0.0)
        self.length = data.get("length", 10.0)
        self.speed = data.get("speed", 1.0)
        if "beats" in data:
            self.beats = [Beat.from_json(beat) for beat in data["beats"]]
        else:
            # legacy save migration: current_section/past_sections become beats
            past_sections = data.get("past_sections", [])
            current_section = data.get("current_section", "")
            self.beats = [Beat(id="beat-%d" % i, description=section, status=BeatStatus.COMPLETED)
                          for i, section in enumerate(past_sections)]
            self.beats.append(Beat(id="beat-%d" % len(past_sections), description=current_section, status=BeatStatus.ACTIVE))
        return self

    def to_json(self) -> dict:
        return {"base_story": self.base_story,
                "beats": [beat.to_json() for beat in self.beats],
                "progress": self.progress,
                "length": self.length,
                "speed": self.speed}
