
import os

def pad_text_for_avatar(text: str, npc_name: str) -> str:
    """Pad text for NPC output."""
    return npc_name + ' <:> ' + text if npc_name else text

def check_file_exists_in_resources(file_name) -> str:
    file_path = os.path.join(os.path.dirname('../../tale/web/resources/'), file_name + '.jpg')
    if os.path.exists(file_path):
        return file_name
    return None
