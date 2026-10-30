from tale.llm.schemas import FollowSchema


class FollowResponse:

    def __init__(self, model: FollowSchema):
        yes_responses = ['yes', 'y', 'true']
        self.follow = any(r in model.response.lower() for r in yes_responses)
        self.reason = model.reason
