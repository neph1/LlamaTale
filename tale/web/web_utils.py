import os
import shutil


dialogue_splitter = ' &lt;:&gt; '

web_resources_path = '../../tale/web' # the game is run from the stories directory
resource_folder = 'resources'
static_folder = 'static/resources'

def create_chat_container(text: str) -> str:
    name, content = _split_text(text)
    if name is None:
        return text
    image_name = name.lower().replace(' ', '_')
    image_file = _find_image(image_name)
    html = '<div class="chat-container">\n'
    html += '<div class="user-name" content="%s"></div>\n' % name
    html += '<img class="user-image" src="%s/%s" alt="%s"/>\n' % (static_folder, image_file or '', name)
    html += '<div class="text-field" type="text">%s</div>\n' % content
    html += '</div>\n'
    return html

def create_location_container(text: str) -> str:
    name, content = _split_text(text)
    if name is None:
        return text
    image_name = name.lower().replace(' ', '_')
    image_file = _find_image(image_name)
    html = '<div class="location-container">\n'
    html += '<div class="text-field" type="text">%s</div>\n' % content
    html += '<div class="location-name" content="%s"></div>\n' % name
    html += '<img class="location-image" src="static/resources/%s" alt="%s"/>\n' % (image_file, name)
    html += '</div>\n'
    return html

def create_examine_container(text: str) -> str:
    separated = text.split(dialogue_splitter)
    if len(separated) != 2:
        separated = text.split(' <:> ')
    if len(separated) != 2:
        return text
    name = separated[0]
    content = separated[1]
    image_file = separated[0].lower().replace(' ', '_') + '.jpg'
    html = '<div class="examine-container">\n'
    html += '<div class="text-field" type="text">%s</div>\n' % content
    html += '<div class="examine-name" content="%s"></div>\n' % name
    html += '<img class="examine-image" src="static/resources/%s" alt="%s"/>\n' % (image_file, name)
    html += '</div>\n'
    return html

def _split_text(text: str) -> list:
    separated = text.split(dialogue_splitter)
    if len(separated) != 2:
        separated = text.split(' <:> ')
    if len(separated) != 2:
        return None, text
    name = separated[0]
    content = separated[1]
    return name, content

def _find_image(image_name: str) -> str:
    if _check_file_exists(image_name + '.gif'):
        return image_name + '.gif'
    elif _check_file_exists(image_name + '.png'):
        return image_name + '.png'
    elif _check_file_exists(image_name + '.jpg'):
        return image_name + '.jpg'
    return ''

def copy_web_resources(gamepath: str):
    # copy the resources folder to the resources folder in the web folder
    shutil.copytree(os.path.join(gamepath, "resources"), os.path.join(web_resources_path, resource_folder), dirs_exist_ok=True)
    
def clear_resources():
    resource_path = os.path.join(web_resources_path, resource_folder)
    if not os.path.exists(resource_path):
        raise FileNotFoundError("Resource folder doesn't exist.")
    
    for item in os.listdir(resource_path):
        item_path = os.path.join(resource_path, item)
        
        if os.path.isfile(item_path):
            os.remove(item_path)

def copy_single_image(gamepath: str, image_name: str):
    shutil.copy(os.path.join(gamepath, "resources", image_name), os.path.join(web_resources_path, resource_folder))

def _check_file_exists(filename: str) -> bool:
    return os.path.exists(os.path.join(web_resources_path, "resources", filename))