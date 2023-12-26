
from tale.image_gen.base_gen import ImageGeneratorBase


image_token = '<:>'

def pad_text_for_avatar(text: str, npc_name: str) -> str:
    """Pad text for NPC output."""
    return npc_name +' <:> ' + text
