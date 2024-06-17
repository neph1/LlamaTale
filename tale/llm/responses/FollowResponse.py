

class FollowResponse:

    

    def __init__(self, response: dict):
        yes_responses = ['yes', 'y', 'true', 'True']
        self.follow = any(response.get('follow', 'no') == r for r in yes_responses) # type: bool
        self.reason = response.get('reason', '') # type: str