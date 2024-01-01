
function handleFile(event) {
    const fileInput = event.target;
    const file = fileInput.files[0];

    if (file) {
        const fileType = getFileType(file);
        console.log('file: ', file);
        if (fileType === 'json') {
            // Handle text-based JSON file
            readTextFile(file);
        } else if (fileType === 'image') {
            // Handle image with embedded JSON
            readImageFile(file);
        } else {
            alert('Unsupported file type. Please upload a JSON file.');
            // Clear the file input
            fileInput.value = '';
        }
    }
}

function getFileType(file) {
    const fileName = file.name.toLowerCase();
    if (fileName.endsWith('.json')) {
        return 'json';
    //} else if (fileName.endsWith('.png') || fileName.endsWith('.jpg') || fileName.endsWith('.jpeg')) {
    //    return 'image';
    } else {
        return 'unsupported';
    }
}

function readTextFile(file) {
    const reader = new FileReader();
    reader.onload = function (event) {
        const fileContent = event.target.result;
        console.log('Text-based JSON content:', fileContent);
        loadCharacter(fileContent);
    };
    reader.readAsText(file);
}

function readImageFile(file) {
    const reader = new FileReader();

    reader.onload = function (event) {
        const imageDataUrl = event.target.result;
        const image = new Image();
        image.onload = function () {
            // Access the 'chara' metadata from the image
            const encodedChar = image.chara;
            // Decode base64 to plain text (JSON)
            const decodedJson = atob(encodedChar);
            // Parse the JSON
            try {
                const parsedJson = JSON.parse(decodedJson);
                loadCharacter(decodedJson);
                // Now you can use parsedJson for further processing
                console.log('Parsed JSON from image:', parsedJson);
            } catch (error) {
                console.error('Error parsing JSON:', error);
            }
        };

        // Set the image source (data URL)
        image.src = imageDataUrl;
    };

    // Read the file as a data URL
    reader.readAsDataURL(file);
}

function loadCharacter(data) {
    var ajax = new XMLHttpRequest();
    ajax.open("POST", "input", true);
    ajax.setRequestHeader("Content-type","application/x-www-form-urlencoded; charset=UTF-8");
    const encodedJson = encodeHtmlEntities(data);
    var cmd_input = '!load_character_from_data ' + encodedJson.replace(/\r?\n|\r/g, '');
    
    var encoded_cmd = encodeURIComponent(cmd_input);
    console.log('encoded_cmd:', encoded_cmd);
    ajax.send("cmd=" + encoded_cmd);
}

function encodeHtmlEntities(str) {
    return str.replace(/[\u00A0-\u9999<>\&]/gim, function(i) {
        return '&#' + i.charCodeAt(0) + ';';
    });
}