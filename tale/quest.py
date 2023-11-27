
from enum import IntEnum


class QuestStatus(IntEnum):
    NOT_STARTED = 0
    NOT_COMPLETED = 1
    COMPLETED = 2
    FAILED = 3

    def __str__(self):
        return self.name.lower()
    

class QuestType(IntEnum):
    GIVE = 0
    TALK = 1
    KILL = 2

    def __str__(self):
        return self.name.lower()


class Quest():
    """ A quest can either be initiated by a character, or from a note or book."""

    def __init__(self, name: str, type: QuestType, target: str, reason: str = '', giver: str = '', reward: str = ''):
        self.name = name 
        self.type = type
        self.reason = reason 
        self.giver = giver
        self.target = target
        self.reward = reward
        self.__status = QuestStatus.NOT_STARTED

    def set_status(self, status: QuestStatus):
        self.__status = status

    def check_completion(self, result: dict):
        if self.type == QuestType.GIVE and result.get("item", None) and self.target == result["item"]:
            self.complete()
            return True
        if self.type == QuestType.TALK and self.target == result["npc"] and self.status == QuestStatus.NOT_COMPLETED:
            self.complete()
            return True
        if self.status == QuestStatus.NOT_STARTED:
            self.start()
        return False

    def is_completed(self):
        return self.__status == QuestStatus.COMPLETED
    
    @property
    def status(self) -> QuestStatus:
        return self.__status
    
    def complete(self):
        self.__status = QuestStatus.COMPLETED

    def start(self):
        self.__status = QuestStatus.NOT_COMPLETED

    def __str__(self):
        return "Quest: %s, type:%s, %s, reason:%s, %s, %s" % (self.name, self.type, self.target, self.reason, self.giver, self.reward)