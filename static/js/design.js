function addBullet(listID, inputName){
    const list = document.getElementById(listID);

    const item = document.createElement("div");
    item.className = "bullet-item";

    item.innerHTML = `
        <span>•</span>
        <input
            type="text"
            name="${inputName}"
            placeholder="Enter requirement"
        >
    `;

    list.appendChild(item);
}