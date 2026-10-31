"use strict";

// Command bar: sending commands to the server via the WebSocket (see script.js),
// and the action dropdown that prefixes the command.

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
