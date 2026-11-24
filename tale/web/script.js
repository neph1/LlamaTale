"use strict";

// Core of the web UI: global state, page setup, the WebSocket connection and
// processing of server messages. The command bar lives in commands.js, the
// right-hand side panel in sidepanel.js.

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
                renderNpcList(npcs);
            }
            if(json.hasOwnProperty("items")) {
                renderItemList(json["items"]);
            }
            if(json.hasOwnProperty("exits")) {
                renderExits(json["exits"]);
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
