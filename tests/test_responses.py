import json
from tale.llm.responses.FollowResponse import FollowResponse
from tale.llm.responses.ActionResponse import ActionResponse
from tale.llm.schemas import FollowSchema, ActionSchema


class TestFollowResponse:

    def test_follow_response(self):
        response = '{"response":"yes", "reason":"because"}'
        follow_response = FollowResponse(FollowSchema.model_validate(json.loads(response)))
        assert follow_response.follow == True

        response = '{"response":"no", "reason":"because"}'
        follow_response = FollowResponse(FollowSchema.model_validate(json.loads(response)))
        assert follow_response.follow == False

        response = '{"response":"Yes, I will follow you.", "reason":"because"}'
        follow_response = FollowResponse(FollowSchema.model_validate(json.loads(response)))
        assert follow_response.follow == True


class TestActionResponse:

    def test_action_response(self):
        model = ActionSchema.model_validate({
            "goal": "get the item",
            "thoughts": "I need it",
            "action": "take",
            "target": "sword",
            "text": "",
        })
        response = ActionResponse(model)
        assert response.goal == "get the item"
        assert response.thoughts == "I need it"
        assert response.action == "take"
        assert response.target == "sword"
        assert response.text == ""
