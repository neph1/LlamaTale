

class FollowResponse:

    def __init__(self, response: dict):
        yes_responses = ['yes', 'y', 'true', 'True']
        self.follow = any(r in response.get('response', 'no').lower() for r in yes_responses) # type: bool
        self.reason = response.get('reason', '') # type: str