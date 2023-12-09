
from tale.image_gen.base_gen import ImageGeneratorBase


image_token = '<:>'

def pad_text_for_npc(text: str, npc_name: str) -> str:
    """Pad text for NPC output."""
    return npc_name +' <:> ' + text

def generate_image(prompt: str, save_path: str, image_name: str, image_generator: ImageGeneratorBase) -> bool:
    """Generate an image from text."""
    image_data = image_generator.generate_image(prompt, save_path, image_name)
    if image_data is None:
        return False
    image_generator.save_image(image_data, image_name)
    return True