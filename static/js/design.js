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


function addDecision() {
    const list = document.getElementById("decision-list");

    const item = document.createElement("div");
    item.className = "architecture-item";

    item.innerHTML = `
        <label>Technology / Decision</label>
        <input
            type="text"
            name="decision_name"
            placeholder="e.g. SQLite"
        >

        <label>Reason</label>
        <textarea
            name="decision_reason"
            placeholder="Why was this selected?"
        ></textarea>

        <label>Alternative Considered</label>
        <input
            type="text"
            name="decision_alternative"
            placeholder="e.g. PostgreSQL"
        >

        <label>Trade-off</label>
        <textarea
            name="decision_tradeoff"
            placeholder="What limitations does this introduce?"
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
