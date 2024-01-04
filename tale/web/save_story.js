
function showSaveDialog() {
    document.getElementById('dialogOverlay').style.display = 'flex';
}

function closeSaveDialog() {
    document.getElementById('dialogOverlay').style.display = 'none';
}

function saveStory() {
    const filenameInput = document.getElementById('filenameInput');
    const filename = filenameInput.value.trim().replace(/ /g, '_');

    // Close the dialog
    closeSaveDialog();
    var ajax = new XMLHttpRequest();
    ajax.open("POST", "input", true);
    ajax.setRequestHeader("Content-type","application/x-www-form-urlencoded; charset=UTF-8");
    var encoded_cmd = encodeURIComponent('save_story ' + filename);
    console.log("Saving story: " + encoded_cmd);
    ajax.send("cmd=" + encoded_cmd);
}
