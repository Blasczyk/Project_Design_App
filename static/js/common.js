function addBullet(listID, inputName){
    const list = document.getElementById(listID);

    const item = document.createElement("div");
    item.className = "bullet-item";

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.name =  `${inputName}_completed`;

    const text = document.createElement("input");
    text.type = "text";
    text.name = inputName;
    text.placeholder = "Enter item";

    item.appendChild(checkbox);
    item.appendChild(text);

    list.appendChild(item);
    
}