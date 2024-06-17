

import json
from tale.llm.responses.FollowResponse import FollowResponse


class TestFollowResponse:

    def test_follow_response(self):
        response = '{"response":"yes", "reason":"because"}'
        follow_response = FollowResponse(json.loads(response))
        assert follow_response.follow == True

        response = '{"response":"no", "reason":"because"}'
        follow_response = FollowResponse(json.loads(response))
        assert follow_response.follow == False

        response = '{"response":"Yes, I will follow you.", "reason":"because"}'
        follow_response = FollowResponse(json.loads(response))
        assert follow_response.follow == True