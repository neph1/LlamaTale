

class ActionResponse():

    def __init__(self, response: dict):
        response = self._sanitize_free_form_response(response)
        self.goal = response.get('goal', '')
        self.text = response.get('text', '')
        self.target = response.get('target', '')
        self.item = response.get('item', '')
        self.action = response.get('action', '')
        self.sentiment = response.get('sentiment', '')
        self.thoughts = response.get('thoughts', '')

    def _sanitize_free_form_response(self, action: dict):
        if action.get('text'):
            if isinstance(action['text'], list):
                action['text'] = action['text'][0]
        if action.get('target'):
            target_name = action['target']
            if isinstance(target_name, list):
                action['target'] = target_name[0]
            elif isinstance(target_name, dict):
                action['target'] = target_name.get('name', '')
        if action.get('item'):
            item_name = action['item']
            if isinstance(item_name, list):
                action['item'] = item_name[0]
            elif isinstance(item_name, dict):
                action['item'] = item_name.get('name', '')
        if action.get('action'):
            action_name = action['action']
            if isinstance(action_name, list):
                action['action'] = action_name[0]
            elif isinstance(action_name, dict):
                action['action'] = action_name.get('action', '')
        return action