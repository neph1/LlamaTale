from tale.llm_utils import LlmUtil
from tale.base import Living, ParseResult

class LivingNpc(Living):
    def __init__(self, name: str, gender: str, *,
                 title: str="", descr: str="", short_descr: str="", age: int, personality: str, occupation: str=""):
        super(LivingNpc, self).__init__(name=name, gender=gender, title=title, descr=descr, short_descr=short_descr)
        self.age = age
        self.personality = personality
        self.occupation = occupation
        self.llm_util = LlmUtil()
        self.conversation = ''
        self.memory_size = 1024
        
    def init(self) -> None:
        self.aliases = {"Npc"}
        
    def notify_action(self, parsed: ParseResult, actor: Living) -> None:
        if actor is self or parsed.verb in self.verbs:
            return  # avoid reacting to ourselves, or reacting to verbs we already have a handler for
        greet = False
        targeted = False
        for alias in self.aliases:
            if alias in parsed.unparsed:
                targeted = True
        if self.name in parsed.unparsed:
                targeted = True
        if parsed.verb in ("hi", "hello") and self in parsed.who_info:
            greet = True
            targeted = True
        elif parsed.verb == "greet" and self in parsed.who_info:
            greet = True
            targeted = True
        if greet and targeted:
            self.tell_others("{Actor} says: \"Hi.\"", evoke=True)
            self.update_conversation(f"{self.title} says: \"Hi.\"")
        elif parsed.verb == "say" and targeted:
            self.update_conversation(f'{actor.title}:{parsed.unparsed}\n')
            response = self.llm_util.generate_dialogue(conversation=self.conversation, character_card = self.character_card, character_name = self.title, target = actor.title )
            self.update_conversation(f"{self.title} says: \"{response}\"")
            if len(self.conversation) > self.memory_size:
                self.conversation = self.conversation[self.memory_size+1:]

            self.tell_others(f"{self.title} says: \"{response}\"", evoke=False, max_length=True)
        elif self in parsed.who_info:
            # store actions against npc
            pass
    
    def update_conversation(self, line: str):
        self.conversation += line
        if len(self.conversation) > self.memory_size:
            self.conversation = self.conversation[len(self.conversation) - self.memory_size+1:]
    @property
    def character_card(self) -> str:
        return '[{name}; gender: {gender}; age: {age}; occupation: {occupation}; personality: {personality}; appearance: {description}; items:{items}]'.format(
                name=self.title,
                gender=self.gender,
                age=self.age,
                personality=self.personality,
                description=self.description,
                occupation=self.occupation,
                items='[]'.format(', '.join([str(i.name) for i in self.inventory])))
