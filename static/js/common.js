
function addBullet(listID, inputName) {
    const list = document.getElementById(listID);

    const item = document.createElement("div");
    item.className = "bullet-item";

    // New requirements do not have database IDs yet
    const id = document.createElement("input");
    id.type = "hidden";
    id.name = `${inputName}_id`;
    id.value = "";

    // Requirement description
    const text = document.createElement("input");
    text.type = "text";
    text.name = inputName;
    text.placeholder = "Enter requirement";

    // Remove requirement from form
    const remove = document.createElement("button");
    remove.type = "button";
    remove.textContent = "Remove";
    remove.addEventListener("click", () => item.remove());

    item.appendChild(id);
    item.appendChild(text);
    item.appendChild(remove);

    list.appendChild(item);
}
