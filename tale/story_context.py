
import math
from tale.util import Context, call_periodically


class StoryContext:

    def __init__(self, base_story: str = "") -> None:
        self.base_story = base_story
        self.current_section  = ""
        self.past_sections = []
        self.progress = 0.0
        self.length = 10.0
        self.speed = 1.0

    @call_periodically(10, 20)
    def increase_progress(self, ctx: Context) -> bool:
        """ increase the progress by the given amount, return True if the progress has changed past the integer value """
        print("Increasing progress")
        start_progress = math.floor(self.progress)
        self.progress += self.speed
        if self.progress >= self.length:
            self.progress = self.length
        if start_progress != math.floor(self.progress):
            ctx.driver.llm_util.advance_story_section(self)
            return True
        return False

    def set_current_section(self, section: str) -> None:
        if self.current_section:
            self.past_sections.append(self.current_section)
            print(f"Past sections: {self.past_sections}")
        self.current_section = section

    def to_context(self) -> str:
        return f"<story> Base plot: {self.base_story}; Active section: {self.current_section}</story>"
    
    def to_context_with_past(self) -> str:
        return f"<story> Base plot: {self.base_story}; Past: {' '.join(self.past_sections) if self.past_sections else 'This is the beginning of the story'}; Active section:{self.current_section}; Progress: {self.progress}/{self.length};</story>"
    
    def from_json(self, data: dict) -> 'StoryContext':
        self.base_story = data.get("base_story", "")
        self.current_section = data.get("current_section", "")
        self.past_sections = data.get("past_sections", [])
        self.progress = data.get("progress", 0.0)
        self.length = data.get("length", 10.0)
        self.speed = data.get("speed", 1.0)
        return self

    def to_json(self) -> dict:
        return {"base_story": self.base_story, 
                "current_section": self.current_section, 
                "past_sections": self.past_sections,
                "progress": self.progress,
                "length": self.length,
                "speed": self.speed}