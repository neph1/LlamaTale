"use strict";

let none_action = 'None';

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
            txtdiv.innerHTML += json["text"];
            if(!document.smoothscrolling_busy) smoothscroll(txtdiv, 0);
            if (json.hasOwnProperty("npcs")) {
                let npcs = json["npcs"];
                populateNpcDropdown(npcs);
                document.getElementById('npcs-in-location').innerHTML = npcs;
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


function submit_cmd()
{
    var cmd_input = document.getElementById("input-cmd");
    var ajax = new XMLHttpRequest();
    ajax.open("POST", "input", true);
    ajax.setRequestHeader("Content-type","application/x-www-form-urlencoded; charset=UTF-8");
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
    var encoded_cmd = encodeURIComponent(cmd_input.value + npcAddress);
    console.log("Sending command: " + encoded_cmd);
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
    let npcsArray = csvString.split(',');
    // for (let i=0; i < 4; i++) {
    //     var npcImage = document.getElementById('npc-image' + i);
    //     npcImage.src = '';
    //     npcImage.classList.toggle('hidden');
    // }
    if (npcsArray.length < 4) {
        // make sure npcsArray has 4 elements
        for (let i = npcsArray.length; i < 4; i++) {
            npcsArray.push('');
        }
    }
    for (let i = 0; i < 4; i++) {
        var npcImage = document.getElementById('npc-image' + i);
        if (npcImage.src !== '' && !(npcImage.src in npcsArray)) {
            npcImage.src = '';
        }
    }
    let max_length = Math.min(4, npcsArray.length)
    for (let i = 0; i < max_length; i++) {
        let npc = npcsArray[i].trim();
        var npcImage = document.getElementById('npc-image' + i);
        if (npc === '') {
            continue;
        }
        let name = npc.toLowerCase().replace(/ /g, '_');
        // checkImageExistence(name, function(exists, imageUrl) {
        //     if (exists) {
        //         npcImage.src = imageUrl;
        //     } else {
        //         console.log('Image does not exist');
        //     }
        // });
        npcImage.src = 'static/resources/' + name + '.jpg';
        npcImage.alt=npc;
        npcImage.classList.toggle('visible');
        
        npcImage.onerror = function() {
            // Handle image not found
            console.log('Image not found for NPC: ' + npc);
            npcImage.classList.toggle('hidden');
        };
    }
    for (let i = 0; i < 4; i++) {
        var npcImage = document.getElementById('npc-image' + i);
        if (npcImage.src === '') {
            npcImage.classList.toggle('hidden');
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
