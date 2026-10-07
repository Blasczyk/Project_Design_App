function addBullet(listID, inputName) {
    const list = document.getElementById(listID);

    const item = document.createElement("div");
    item.className = "bullet-item";

    item.innerHTML = `
        <span>•</span>
        <input
            type="text"
            name="${inputName}"
            placeholder="Enter item"
        >
        <button
            type="button"
            onclick="this.closest('.bullet-item').remove()"
        >
            Remove
        </button>
    `;

    list.appendChild(item);
}