from tale.llm.schemas import ActionSchema


class ActionResponse():

    def __init__(self, model: ActionSchema):
        self.goal = model.goal
        self.text = model.text
        self.target = model.target
        self.item = model.item
        self.action = model.action
        self.sentiment = ''
        self.thoughts = model.thoughts
