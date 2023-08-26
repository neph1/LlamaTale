from tale import mud_context
from tale.base import Living, Location, ParseResult
from tale.errors import TaleError
from tale.player import Player
from tale.story import StoryBase

class LivingNpc(Living):
    """An NPC with extra fields to define personality and help LLM generate dialogue"""

    def __init__(self, name: str, gender: str, *,
                 title: str="", descr: str="", short_descr: str="", age: int, personality: str, occupation: str="", race: str=""):
        super(LivingNpc, self).__init__(name=name, gender=gender, title=title, descr=descr, short_descr=short_descr, race=race)
        self.age = age
        self.personality = personality
        self.occupation = occupation
        self.conversation = ''
        self.memory_size = 1024
        self.sentiments = {}
        
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
            self.do_say(parsed.unparsed, actor)
        elif self in parsed.who_info:
            # store actions against npc
            pass

    def do_say(self, what_happened: str, actor: Living) -> None:
        self.update_conversation(f'{actor.title}:{what_happened}\n')
        max_length = False if isinstance(actor, Player) else True
        
        response, item_result, sentiment = mud_context.driver.llm_util.generate_dialogue(
            conversation=self.conversation, 
            character_card = self.character_card, 
            character_name = self.title, 
            target = actor.title,
            target_description = actor.short_description,
            sentiment = self.sentiments.get(actor.title, ''),
            location_description=self.location.look(exclude_living=self),
            max_length=max_length)
            
        self.update_conversation(f"{self.title} says: \"{response}\"")
        if len(self.conversation) > self.memory_size:
            self.conversation = self.conversation[self.memory_size+1:]
        
        self.tell_others(f"{self.title} says: \"{response}\"", evoke=False, max_length=True)
        if item_result:
            self.handle_item_result(item_result, actor)
        
        if sentiment:
            self.sentiments[actor.title] = sentiment
    
    def handle_item_result(self, result: str, actor: Living):
        
        if result["from"] == self.title:
            item = self.search_item(result["item"])
            if not item:
                raise TaleError("item not found on actor %s " % item)
            #self.remove(item, self)
            if result["to"]:
                
                if result["to"] == actor.name or result["to"] == actor.title:
                    item.move(actor, self)
                    #actor.insert(item, None)
                elif result["to"] in ["user", "you", "player"] and isinstance(actor, Player):
                    item.move(actor, self)
                    #actor.insert(item, None)
                actor.tell("%s gives you %s." % (self.subjective, item.title), evoke=False)
                self.tell_others("{Actor} gives %s to %s" % (item.title, actor.title), evoke=False)
            else:
                item.move(self.location, self)
                #self.location.insert(item, self)
                self.tell_others("{Actor} drops %s on the floor" % (item.title), evoke=False)
                    
        
    def update_conversation(self, line: str):
        self.conversation += line
        if len(self.conversation) > self.memory_size:
            self.conversation = self.conversation[len(self.conversation) - self.memory_size+1:]
            
    @property
    def character_card(self) -> str:
        items = []
        for i in self.inventory:
            items.append(str(i.name))
        return '[{name}; gender: {gender}; age: {age}; occupation: {occupation}; personality: {personality}; appearance: {description}; items:{items}]'.format(
                name=self.title,
                gender=self.gender,
                age=self.age,
                personality=self.personality,
                description=self.description,
                occupation=self.occupation,
                items=','.join(items))

class DynamicStory(StoryBase):

    def add_location(self, location: Location, zone: str = '') -> None:
        pass
