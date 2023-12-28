import os
import shutil


dialogue_splitter = ' &lt;:&gt; '

web_resources_path = '../../tale/web' # the game is run from the stories directory
resource_folder = 'resources'

def create_chat_container(text: str) -> str:
    separated = text.split(dialogue_splitter)
    if len(separated) != 2:
        separated = text.split(' <:> ')
    if len(separated) != 2:
        return text
    name = separated[0]
    content = separated[1]
    image_file = separated[0].lower().replace(' ', '_') + '.jpg'
    html = '<div class="chat-container">\n'
    html += '<div class="user-name" content="%s"></div>\n' % name
    html += '<img class="user-image" src="static/resources/%s" alt="%s"/>\n' % (image_file, name)
    html += '<div class="text-field" type="text">%s</div>\n' % content
    html += '</div>\n'
    return html

def create_location_container(text: str) -> str:
    separated = text.split(dialogue_splitter)
    if len(separated) != 2:
        separated = text.split(' <:> ')
    if len(separated) != 2:
        return text
    name = separated[0]
    content = separated[1]
    image_file = separated[0].lower().replace(' ', '_') + '.jpg'
    html = '<div class="location-container">\n'
    html += '<div class="text-field" type="text">%s</div>\n' % content
    html += '<div class="location-name" content="%s"></div>\n' % name
    html += '<img class="location-image" src="static/resources/%s" alt="%s"/>\n' % (image_file, name)
    html += '</div>\n'
    return html

def copy_web_resources(gamepath: str):
    # copy the resources folder to the resources folder in the web folder
    shutil.copytree(os.path.join(gamepath, "resources"), os.path.join(web_resources_path, resource_folder), dirs_exist_ok=True)
    
def clear_resources():
    # clear the resources folder from the web folder
    files = os.listdir(os.path.join(web_resources_path, resource_folder))
    for file in files:
        os.remove(os.path.join(web_resources_path, resource_folder, file))

def copy_single_image(gamepath: str, image_name: str):
    # copy a single image to the resources folder in the web folder
    shutil.copy(os.path.join(gamepath, "resources", image_name), os.path.join(web_resources_path, resource_folder))