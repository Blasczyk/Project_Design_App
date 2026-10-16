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

function addComponent(){
    const list = document.getElementById("component-list");

    const item = document.createElement("div");

    item.className = "architecture-item";
    
    item.innerHTML = `
        <label> Component Name</label>
        <input
            type = "text"
            name="component_name"
            placeholder=e.g. SQLite Database"
            >
        <label>Responsibility</label>
        <textarea
            name="component_responsibility"
            placeholder="What does this component do?"
        ></textarea>

        <button type="button" class="remove-item">
            Remove
        </button>
        `;

    item.querySelector(".remove-item").addEventListener(
        "click",
        () => item.remove()
    );
    list.appendChild(item);
}

function addTechnology(){
    const list = document.getElementById("technology-list");

    const item = document.createElement("div");
    item.className = "technology-item";

    item.innerHTML = `
        <input
            type="text"
            name="technology_name"
            placeholder="Technology name"
            required
        >

        <textarea
            name="technology_reason"
            placeholder="Reason for choosing"
        ></textarea>

        <textarea
            name="technology_alternative"
            placeholder="Alternatives considered"
        ></textarea>

        <textarea
            name="technology_tradeoff"
            placeholder="Tradeoffs"
        ></textarea>

        <button type="button" class="remove-technology">
            Remove
        </button>
    `;

    item.querySelector(".remove-technology")
        .addEventListener("click", () => item.remove());

    list.appendChild(item);
}