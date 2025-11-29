"use strict";

let none_action = 'None';
let websocket = null;

document.waitingForResponse = false;

function setup()
{
    var but=document.getElementById("button-autocomplete");
    if(but.accessKeyLabel) { but.value += ' ('+but.accessKeyLabel+')'; }

    document.smoothscrolling_busy = false;
    window.onbeforeunload = function(e) { return "Are you sure you want to abort the session and close the window?"; }

    // Connect via WebSocket
    connectWebSocket();

    populateActionDropdown();
}

function displayConnectionError(message) {
    var txtdiv = document.getElementById("textframe");
    txtdiv.innerHTML += message;
    txtdiv.scrollTop = txtdiv.scrollHeight;
    var cmd_input = document.getElementById("input-cmd");
    cmd_input.disabled = true;
}

function connectWebSocket() {
    // Connect via WebSocket
    var protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    var wsUrl = protocol + '//' + window.location.host + '/tale/ws';
    
    try {
        websocket = new WebSocket(wsUrl);
        
        websocket.onopen = function(e) {
            console.log("WebSocket connection established");
        };
        
        websocket.onmessage = function(e) {
            console.log("WS message received");
            var data = JSON.parse(e.data);
            if (data.type === "connected") {
                console.log("WebSocket connected successfully");
            } else if (data.type === "text" || data.text) {
                process_text(data);

                // We'll treat anything sent as being complete
                setWaitingState(false);
                    
            } else if (data.type === "data") {
                // Handle data messages
                process_data(data);
            }
        };
        
        websocket.onerror = function(e) {
            console.error("WebSocket error:", e);
            displayConnectionError("<p class='server-error'>WebSocket connection error.<br><br>Refresh the page to restore it.</p>");
            setWaitingState(false);
        };
        
        websocket.onclose = function(e) {
            console.log("WebSocket closed:", e.code, e.reason);
            displayConnectionError("<p class='server-error'>Connection closed.<br><br>Refresh the page to restore it.</p>");
            setWaitingState(false);
        };
    } catch (e) {
        console.error("WebSocket failed to connect:", e);
        displayConnectionError("<p class='server-error'>Failed to connect to server.<br><br>Please refresh the page.</p>");
        setWaitingState(false);
    }
}

function process_data(json) {
    if (json.data) {
        var id = json.id || "default-image";
        var element = document.getElementById(id);
        if (element) {
            element.src = json.data;
        }
    }
}

function process_text(json)
{
    var txtdiv = document.getElementById("textframe");
    if(json["error"]) {
        txtdiv.innerHTML += "<p class='server-error'>Server error: "+JSON.stringify(json)+"<br>Perhaps refreshing the page might help. If it doesn't, quit or close your browser and try with a new window.</p>";
        txtdiv.scrollTop = txtdiv.scrollHeight;
        
        setWaitingState(false);
    }
    else
    {
        var special = json["special"];
        if(special) {
            if(special.indexOf("clear")>=0) {
                txtdiv.innerHTML = "";
                txtdiv.scrollTop = 0;
            }
            if(special.indexOf("noecho")>=0) {
                var inputfield = document.getElementById("input-cmd");
                inputfield.type = "password";       // may not work in all browsers...
                inputfield.style.color = "gray";
            }
        }
        if(json["text"]) {
            document.getElementById("player-location").innerHTML = json["location"];
            txtdiv.innerHTML += json["text"];
            if(!document.smoothscrolling_busy) smoothscroll(txtdiv, 0);
            if (json.hasOwnProperty("npcs")) {
                const npcs = json["npcs"];
                populateNpcDropdown(npcs);
                populateNpcImages(npcs);
                
                const npcsArray = npcs.split(',');
                let npcConcat = '';
                for (let i = 0; i < npcsArray.length; i++) {
                    const npcContainer = document.createElement('div'); // Create a container div for each NPC
                    const npcName = npcsArray[i].trim();
                    npcContainer.appendChild(document.createTextNode(npcName));
                    npcConcat += npcContainer.outerHTML;
                }
                document.getElementById('npcs-in-location').innerHTML = npcConcat;
            }
            if(json.hasOwnProperty("items")) {
                document.getElementById('items-in-location').innerHTML = json["items"];
            }
            if(json.hasOwnProperty("exits")) {
                document.getElementById('exits-in-location').innerHTML = json["exits"];
            }
            setLocationImage(json["location"].toLowerCase().replace(/ /g, '_') + '.jpg');
            
        }
        if(json.hasOwnProperty("data")) {
            id = json["id"]; // where to put the image
            data = json["data"];   // the image data
            document.getElementById(id).src = data;
        }

    }
}


function smoothscroll(div, previousTop)
{
    document.smoothscrolling_busy = true;
    if(div.scrollTop < div.scrollHeight) {
        div.scrollTop += 6;
        if(div.scrollTop > previousTop) {
            window.requestAnimationFrame(function(){smoothscroll(div, div.scrollTop);});
            // setTimeout(function(){smoothscroll(div, div.scrollTop);}, 10);
            return;
        }
    }
    document.smoothscrolling_busy = false;
}


// Add helper to toggle "waiting for response" UI and block input while waiting
function setWaitingState(waiting) {
    var cmd_input = document.getElementById("input-cmd");
    var autocompleteBtn = document.getElementById("button-autocomplete");
    var submitBtn = document.getElementById("button-submit"); // optional; may not exist in all layouts
    document.waitingForResponse = waiting;

    if (waiting) {
        if (cmd_input) {
            cmd_input.disabled = true;
            cmd_input.classList.add('disabled-while-waiting');
        }
        if (autocompleteBtn) autocompleteBtn.disabled = true;
        if (submitBtn) submitBtn.disabled = true;

        var indicator = document.getElementById('waiting-indicator');
        if (!indicator) {
            indicator = document.createElement('span');
            indicator.id = 'waiting-indicator';
            indicator.className = 'waiting-indicator';
            indicator.textContent = 'Waiting for server...';
            indicator.style.marginLeft = '8px';
            indicator.style.color = '#666';
            // try to append next to the input or button area
            var parent = (cmd_input && cmd_input.parentNode) ? cmd_input.parentNode : document.body;
            parent.appendChild(indicator);
        } else {
            indicator.style.display = '';
        }
    } else {
        if (cmd_input) {
            cmd_input.disabled = false;
            cmd_input.classList.remove('disabled-while-waiting');
            cmd_input.focus();
        }
        if (autocompleteBtn) autocompleteBtn.disabled = false;
        if (submitBtn) submitBtn.disabled = false;

        var indicator = document.getElementById('waiting-indicator');
        if (indicator) indicator.style.display = 'none';
    }
}


function submit_cmd()
{
    var cmd_input = document.getElementById("input-cmd");

    if (document.waitingForResponse) {
        console.log("Command ignored because waiting for server response");
        return false;
    }

    var selectedNpc = document.getElementById('npc-dropdown').value;
    var npcAddress = '';
    var selectedAction = document.getElementById('action-dropdown').value;
    if (selectedAction && selectedAction !== none_action) {
        cmd_input.value = selectedAction + ' ' + cmd_input.value;
    }
    if (selectedNpc && selectedNpc !== 'None') {
        if (cmd_input.value.includes('say')) {
            npcAddress = ' to ' + selectedNpc;
        } else {
            npcAddress = ' ' + selectedNpc;
        }
    }

    setWaitingState(true);
    send_cmd(cmd_input.value, npcAddress);
    cmd_input.value="";
    cmd_input.focus();
    cmd_input.type = "text";
    cmd_input.style.color = "black";

    return false;
}

function send_cmd(command, npcAddress) {
    var fullCommand = command + npcAddress;
    
    if (websocket && websocket.readyState === WebSocket.OPEN) {
        // Use WebSocket
        try {
            var message = JSON.stringify({ cmd: fullCommand });
            console.log("Sending command via WebSocket: " + fullCommand);
            websocket.send(message);
        } catch (e) {
            console.error("WebSocket send failed:", e);
            displayConnectionError("<p class='server-error'>Failed to send command.<br><br>Please refresh the page.</p>");
        }
    } else {
        console.error("WebSocket not connected");
        displayConnectionError("<p class='server-error'>Not connected to server.<br><br>Please refresh the page.</p>");
    }
}

function autocomplete_cmd()
{
    var cmd_input = document.getElementById("input-cmd");
    if(cmd_input.value) {
        if (websocket && websocket.readyState === WebSocket.OPEN) {
            // Use WebSocket for autocomplete
            var message = JSON.stringify({ cmd: cmd_input.value, autocomplete: 1 });
            console.log("Sending autocomplete via WebSocket");
            websocket.send(message);
        } else {
            console.error("WebSocket not connected for autocomplete");
        }
    }
    cmd_input.focus();
    return false;
}

function quit_clicked()
{
    if(confirm("Quitting like this will abort your game.\nYou will lose your progress. Are you sure?")) {
        window.onbeforeunload = null;
        document.location="quit";
        return true;
    }
    return false;
}

function setLocationImage(location_image) {
    var locationImage = document.getElementById('location-image');
    if (location_image !== null) {
        locationImage.style.visibility = "visible";
        locationImage.src = 'static/resources/' + location_image;
    } else {
        locationImage.src = 'static/unknown_location.jpg';
        locationImage.style.visibility = "hidden";
    }
}

function imageError() {
    console.log('Image not found. Hiding the image element.');
    document.getElementById('location-image').style.visibility = 'hidden';
}

function updateImage() {
    var input = document.getElementById('imageInput');
    var image = document.getElementById('userImage');

    var file = input.files[0];

    if (file) {
        var reader = new FileReader();

        reader.onload = function (e) {
            image.src = e.target.result;
        };

        reader.readAsDataURL(file);
    }
}

function populateNpcDropdown(csvString) {
    var npcsArray = csvString.split(',');

    var dropdown = document.getElementById('npc-dropdown');
    let lastSelected = dropdown.value;
    dropdown.innerHTML = '';
    
    var option = document.createElement('option');
    option.value = none_action;
    option.text = none_action;
    dropdown.add(option);
    npcsArray.forEach(function (optionValue) {
        var option = document.createElement('option');
        let npc = optionValue.trim();
        option.value = npc;
        option.text = npc;
        dropdown.add(option);
        if (lastSelected && option.value === lastSelected) {
            option.selected = true;
        }
    });
}

function populateActionDropdown() {
    // Get the dropdown element
    var dropdown = document.getElementById('action-dropdown');
    let lastSelected = dropdown.value;
    dropdown.innerHTML = '';
    // Loop through the options array and add each option to the dropdown
    var actions = [none_action, 'say', 'give', 'take', 'use', 'attack', 'look', 'examine', 'open', 'close', 'loot', 'wear', 'wield', 'remove', 'drop', 'inventory', 'help'];
    actions.forEach(function (action) {
        var option = document.createElement('option');
        option.value = action;
        option.text = action;
        dropdown.add(option);
        if (lastSelected && option.value === lastSelected) {
            option.selected = true;
        } else if (option.value === none_action) {
            option.selected = true;
        }
    });

}

function populateNpcImages(csvString) {
    let npcsArray = csvString.split(','); // names of npcs, separated by commas
    if (npcsArray.length < 4) {
        for (let i = npcsArray.length; i < 4; i++) {
            npcsArray.push('');
        }
    }

    for (let i = 0; i < 4; i++) {
        npcsArray[i] = npcsArray[i].toLowerCase().replace(/ /g, '_');
    }

    for (let i = 0; i < 4; i++) {
        let name = npcsArray[i];
        var npcImage = document.getElementById('npc-image' + i);

        if (!npcImage) continue; // Ensure the element exists

        if (name === '') {
            npcImage.src = '';
            npcImage.alt = '';
            npcImage.classList.remove('visible');
            npcImage.classList.add('invisible');
            npcImage.classList.add('hidden');
        } else {
            npcImage.src = 'static/resources/' + name + '.jpg';
            npcImage.alt = name;
            npcImage.classList.add('visible');
            npcImage.classList.remove('invisible');
            npcImage.classList.remove('hidden');
        }
    }
}

function checkImageExistence(imageName, callback) {
    const image = new Image();

    // Array of possible image formats to check
    const formats = ['jpg'];

    // Recursive function to try each format
    function tryFormat(index) {
        if (index >= formats.length) {
            // No more formats to try, image does not exist
            callback(false);
            return;
        }

        // Set the source to the current format
        image.src = 'static/resources/' + `${imageName}.${formats[index]}`;

        // Check for the onload event
        image.onload = function() {
            // Image exists, callback with true
            console.log('Image found for NPC: ' + imageName + ' at ' + this.src);
            callback(true, this.src);
        };

        // Check for the onerror event
        image.onerror = function() {
            // Image does not exist in the current format, try the next format
            tryFormat(index + 1);
        };
    }

    // Start checking with the first format
    tryFormat(0);
}
