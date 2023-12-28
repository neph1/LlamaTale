"use strict";

let no_action = '- - -';

function setup()
{
    if(/Edge\//.test(navigator.userAgent))
    {
        // Edge has problems with the eventsoure polyfill :(
        alert("You seem to be using Microsoft Edge.\n\nUnfortunately, Edge doesn't support the EventSource API.\n"+
        "We use a polyfill (substitute code) but Edge has a problem with updating the text output anyway.\n\n" +
        "You are strongly advised to use a browser that does support the required feature, such as FIREFOX or CHROME or SAFARI.\n\n" +
        "(or even Internet Explorer 11, where the polyfill works fine. Somehow only Edge has this problem)");
    }

    var but=document.getElementById("button-autocomplete");
    if(but.accessKeyLabel) { but.value += ' ('+but.accessKeyLabel+')'; }

    document.smoothscrolling_busy = false;
    window.onbeforeunload = function(e) { return "Are you sure you want to abort the session and close the window?"; }

    // use eventsource (server-side events) to update the text, rather than manual ajax polling
    var esource = new EventSource("eventsource");
    esource.addEventListener("text", function(e) {
        console.log("ES text event");
        process_text(JSON.parse(e.data));
        return false;
    }, false);
    esource.addEventListener("message", function(e) {
        console.log("ES unclassified message - ignored");
        return false;
    }, false);

    esource.addEventListener("error", function(e) {
        console.error("ES error:", e, e.target.readyState);
        var txtdiv = document.getElementById("textframe");
        if(e.target.readyState == EventSource.CLOSED) {
            txtdiv.innerHTML += "<p class='server-error'>Connection closed.<br><br>Refresh the page to restore it. If that doesn't work, quit or close your browser and try with a new window.</p>";
        } else {
            txtdiv.innerHTML += "<p class='server-error'>Connection error.<br><br>Perhaps refreshing the page fixes it. If it doesn't, quit or close your browser and try with a new window.</p>";
        }
        txtdiv.scrollTop = txtdiv.scrollHeight;
        var cmd_input = document.getElementById("input-cmd");
        cmd_input.disabled=true;
        //   esource.close();       // close the eventsource, so that it won't reconnect
    }, false);

    populateActionDropdown();

}

function process_text(json)
{
    var txtdiv = document.getElementById("textframe");
    if(json["error"]) {
        txtdiv.innerHTML += "<p class='server-error'>Server error: "+JSON.stringify(json)+"<br>Perhaps refreshing the page might help. If it doesn't, quit or close your browser and try with a new window.</p>";
        txtdiv.scrollTop = txtdiv.scrollHeight;
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
            if (json.hasOwnProperty("npcs")) {
                populateNpcDropdown(json["npcs"]);
            }
            if (json.hasOwnProperty("location_image")) {
                set_location_image(json["location_image"]);
            }
            //set_location_image(json["location"]);
            // document.getElementById("player-turns").innerHTML = json["turns"];
            txtdiv.innerHTML += json["text"];
            if(!document.smoothscrolling_busy) smoothscroll(txtdiv, 0);
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


function submit_cmd()
{
    var cmd_input = document.getElementById("input-cmd");
    var ajax = new XMLHttpRequest();
    ajax.open("POST", "input", true);
    ajax.setRequestHeader("Content-type","application/x-www-form-urlencoded; charset=UTF-8");
    var selectedNpc = document.getElementById('npc-dropdown').value;
    var npcAddress = '';
    var selectedAction = document.getElementById('action-dropdown').value;
    if (selectedAction && selectedAction !== no_action) {
        cmd_input.value = selectedAction + ' ' + cmd_input.value;
    }
    if (selectedNpc && selectedNpc !== 'None') {
        if ('say' in cmd_input.value) {
            npcAddress = ' to ' + selectedNpc.replace(/ /g, '_');
        } else {
            npcAddress = ' ' + selectedNpc.replace(/ /g, '_');
        }
    }
    var encoded_cmd = encodeURIComponent(cmd_input.value + npcAddress);
    
    ajax.send("cmd=" + encoded_cmd);
    cmd_input.value="";
    cmd_input.focus();
    cmd_input.type = "text";
    cmd_input.style.color = "black";
    return false;
}

function autocomplete_cmd()
{
    var cmd_input = document.getElementById("input-cmd");
    if(cmd_input.value) {
        var ajax = new XMLHttpRequest();
        ajax.open("POST", "input", true);
        ajax.setRequestHeader("Content-type","application/x-www-form-urlencoded");
        ajax.send("cmd=" + encodeURIComponent(cmd_input.value)+"&autocomplete=1");
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

function set_location_image(location_image) {
    var locationImage = document.getElementById('location-image');
    locationImage.src = 'resources/' + location_image;
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
    // Split the comma-separated string into an array
    var optionsArray = csvString.split(',');

    // Get the dropdown element
    var dropdown = document.getElementById('npc-dropdown');
    let lastSelected = dropdown.value;
    dropdown.innerHTML = '';
    // Loop through the options array and add each option to the dropdown
    var option = document.createElement('option');
    option.value = 'None';
    option.text = 'None';
    dropdown.add(option);
    optionsArray.forEach(function (optionValue) {
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
    var actions = [no_action, 'say', 'give', 'take', 'use', 'attack', 'look', 'examine', 'open', 'close', 'loot', 'wear', 'wield'];
    actions.forEach(function (action) {
        var option = document.createElement('option');
        option.value = action;
        option.text = action;
        dropdown.add(option);
        if (lastSelected && option.value === lastSelected) {
            option.selected = true;
        } else if (option.value === no_action) {
            option.selected = true;
        }
    });

}
