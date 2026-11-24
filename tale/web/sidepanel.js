"use strict";

// Right-hand side panel: location image, npc images and the clickable
// lists of present characters, visible exits and visible items.
// Clicking a name selects it (npc dropdown) or puts it in the command
// box (exits, items) without sending it.

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

// Render the present characters as clickable names; clicking one selects it in the npc dropdown
function renderNpcList(csvString) {
    const container = document.getElementById('npcs-in-location');
    container.innerHTML = '';
    const npcsArray = csvString.split(',');
    for (let i = 0; i < npcsArray.length; i++) {
        const npcName = npcsArray[i].trim();
        if (!npcName) continue;
        const npcContainer = document.createElement('div'); // Create a container div for each NPC
        const link = document.createElement('span');
        link.className = 'clickable-npc';
        link.textContent = npcName;
        link.title = 'Select ' + npcName + ' in the dropdown';
        link.onclick = function () { selectNpc(npcName); };
        npcContainer.appendChild(link);
        container.appendChild(npcContainer);
    }
}

function selectNpc(name) {
    var dropdown = document.getElementById('npc-dropdown');
    dropdown.value = name;
    if (dropdown.value !== name) { // not in the list (shouldn't happen); add it
        var option = document.createElement('option');
        option.value = name;
        option.text = name;
        dropdown.add(option);
        dropdown.value = name;
    }
    document.getElementById('input-cmd').focus();
}

// Render the visible exits as clickable "name(direction)" entries; clicking one puts the
// exit name in the command box (without sending it)
function renderExits(exits) {
    const container = document.getElementById('exits-in-location');
    container.innerHTML = '';
    if (!Array.isArray(exits)) { // backwards compatibility with a plain comma-separated string
        container.textContent = exits;
        return;
    }
    exits.forEach(function (exit, index) {
        if (index > 0) {
            container.appendChild(document.createTextNode(', '));
        }
        const link = document.createElement('span');
        link.className = 'clickable-exit';
        link.textContent = exit.direction ? exit.name + '(' + exit.direction + ')' : exit.name;
        link.title = 'Put "' + exit.name + '" in the command box';
        link.onclick = function () { fillCommand(exit.name); };
        container.appendChild(link);
    });
}

// Render the visible items as clickable names; clicking one puts the item name in the
// command box (without sending it) -- the verb (e.g. examine or take) is chosen with
// the action dropdown
function renderItemList(csvString) {
    const container = document.getElementById('items-in-location');
    container.innerHTML = '';
    if (typeof csvString !== 'string' || !csvString) {
        if (csvString) container.textContent = csvString;
        return;
    }
    const itemsArray = csvString.split(',');
    let first = true;
    for (let i = 0; i < itemsArray.length; i++) {
        const itemName = itemsArray[i].trim();
        if (!itemName) continue;
        if (!first) {
            container.appendChild(document.createTextNode(', '));
        }
        first = false;
        const link = document.createElement('span');
        link.className = 'clickable-item';
        link.textContent = itemName;
        link.title = 'Put "' + itemName + '" in the command box (choose e.g. examine or take in the action dropdown)';
        link.onclick = function () { fillCommand(itemName); };
        container.appendChild(link);
    }
}

// Put text in the command box (without sending it) and focus it
function fillCommand(text) {
    const cmd_input = document.getElementById('input-cmd');
    cmd_input.value = text;
    cmd_input.focus();
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
