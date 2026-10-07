/* TaskFlow's small, dependency-free browser client. */

const state = {
    filter: "all",
    search: "",
    sort: "priority",
};

const elements = {
    taskList: document.querySelector("#task-list"),
    loading: document.querySelector("#loading-state"),
    empty: document.querySelector("#empty-state"),
    emptyTitle: document.querySelector("#empty-title"),
    emptyCopy: document.querySelector("#empty-copy"),
    taskCount: document.querySelector("#task-count-label"),
    search: document.querySelector("#search-input"),
    sort: document.querySelector("#sort-select"),
    modal: document.querySelector("#task-modal"),
    modalTitle: document.querySelector("#modal-title"),
    form: document.querySelector("#task-form"),
    taskId: document.querySelector("#task-id"),
    title: document.querySelector("#task-title"),
    description: document.querySelector("#task-description"),
    dueDate: document.querySelector("#task-due-date"),
    priority: document.querySelector("#task-priority"),
    formError: document.querySelector("#form-error"),
    saveButton: document.querySelector("#save-task-button"),
    toast: document.querySelector("#toast"),
};

let searchTimer;
let toastTimer;

async function requestJson(url, options = {}) {
    const response = await fetch(url, {
        headers: { "Content-Type": "application/json", ...(options.headers || {}) },
        ...options,
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
        throw new Error(data.error || "Something went wrong.");
    }
    return data;
}

async function loadTasks() {
    elements.loading.classList.remove("hidden");
    elements.empty.classList.add("hidden");
    try {
        const params = new URLSearchParams({
            filter: state.filter,
            search: state.search,
            sort: state.sort,
        });
        const data = await requestJson("/api/tasks?" + params.toString());
        renderTasks(data.tasks);
    } catch (error) {
        showToast(error.message, true);
    } finally {
        elements.loading.classList.add("hidden");
    }
}

async function loadStats() {
    try {
        const stats = await requestJson("/api/stats");
        document.querySelector("#stat-total").textContent = stats.total;
        document.querySelector("#stat-pending").textContent = stats.pending;
        document.querySelector("#stat-completed").textContent = stats.completed;
        document.querySelector("#stat-due-today").textContent = stats.due_today;
    } catch (error) {
        showToast(error.message, true);
    }
}

async function refresh() {
    await Promise.all([loadTasks(), loadStats()]);
}

function renderTasks(tasks) {
    elements.taskList.replaceChildren();
    const noun = tasks.length === 1 ? "task" : "tasks";
    elements.taskCount.textContent = tasks.length + " " + noun + " in this view.";

    if (!tasks.length) {
        elements.emptyTitle.textContent = state.search ? "No matching tasks" : "No tasks here yet";
        elements.emptyCopy.textContent = state.search
            ? "Try a different search or clear the current filters."
            : "Add your first task and turn your intentions into progress.";
        elements.empty.classList.remove("hidden");
        return;
    }

    tasks.forEach((task, index) => {
        const card = createTaskCard(task);
        card.style.animationDelay = Math.min(index * 35, 250) + "ms";
        elements.taskList.append(card);
    });
}

function createTaskCard(task) {
    const card = document.createElement("article");
    card.className = "task-card" + (task.completed ? " completed" : "");

    const check = document.createElement("button");
    check.className = "check-button";
    check.type = "button";
    check.setAttribute("aria-label", task.completed ? "Mark task pending" : "Mark task complete");
    check.addEventListener("click", () => toggleTask(task));

    const content = document.createElement("div");
    content.className = "task-content";

    const title = document.createElement("h3");
    title.className = "task-title";
    title.textContent = task.title;
    content.append(title);

    if (task.description) {
        const description = document.createElement("p");
        description.className = "task-description";
        description.textContent = task.description;
        content.append(description);
    }

    const meta = document.createElement("div");
    meta.className = "task-meta";
    const priority = document.createElement("span");
    priority.className = "priority-pill priority-" + task.priority;
    priority.textContent = task.priority;
    meta.append(priority);

    if (task.due_date) {
        const due = document.createElement("span");
        due.className = "due-date" + (isOverdue(task) ? " overdue" : "");
        due.textContent = "◷ " + formatDate(task.due_date);
        meta.append(due);
    }
    content.append(meta);

    const actions = document.createElement("div");
    actions.className = "task-actions";
    const edit = actionButton("✎", "Edit task", "icon-button");
    edit.addEventListener("click", () => openModal(task));
    const remove = actionButton("⌫", "Delete task", "icon-button delete-button");
    remove.addEventListener("click", () => removeTask(task));
    actions.append(edit, remove);

    card.append(check, content, actions);
    return card;
}

function actionButton(label, ariaLabel, className) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = className;
    button.textContent = label;
    button.setAttribute("aria-label", ariaLabel);
    return button;
}

function isOverdue(task) {
    if (task.completed || !task.due_date) return false;
    const today = new Date();
    const current = new Date(today.getFullYear(), today.getMonth(), today.getDate());
    return new Date(task.due_date + "T00:00:00") < current;
}

function formatDate(value) {
    const date = new Date(value + "T00:00:00");
    return date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

async function toggleTask(task) {
    try {
        await requestJson("/api/tasks/" + task.id, {
            method: "PATCH",
            body: JSON.stringify({ completed: !task.completed }),
        });
        showToast(task.completed ? "Task moved back to pending." : "Task completed.");
        await refresh();
    } catch (error) {
        showToast(error.message, true);
    }
}

async function removeTask(task) {
    if (!window.confirm("Delete “" + task.title + "”?")) return;
    try {
        await requestJson("/api/tasks/" + task.id, { method: "DELETE" });
        showToast("Task deleted.");
        await refresh();
    } catch (error) {
        showToast(error.message, true);
    }
}

function openModal(task = null) {
    elements.form.reset();
    elements.formError.classList.add("hidden");
    elements.taskId.value = task ? task.id : "";
    elements.modalTitle.textContent = task ? "Edit task" : "Create a task";
    elements.saveButton.textContent = task ? "Save changes" : "Save task";
    if (task) {
        elements.title.value = task.title;
        elements.description.value = task.description || "";
        elements.dueDate.value = task.due_date || "";
        elements.priority.value = task.priority;
    }
    elements.modal.classList.remove("hidden");
    elements.title.focus();
}

function closeModal() {
    elements.modal.classList.add("hidden");
}

async function saveTask(event) {
    event.preventDefault();
    elements.formError.classList.add("hidden");
    elements.saveButton.disabled = true;
    const payload = {
        title: elements.title.value,
        description: elements.description.value,
        due_date: elements.dueDate.value || null,
        priority: elements.priority.value,
    };
    const id = elements.taskId.value;
    try {
        await requestJson(id ? "/api/tasks/" + id : "/api/tasks", {
            method: id ? "PATCH" : "POST",
            body: JSON.stringify(payload),
        });
        closeModal();
        showToast(id ? "Task updated." : "Task created.");
        await refresh();
    } catch (error) {
        elements.formError.textContent = error.message;
        elements.formError.classList.remove("hidden");
    } finally {
        elements.saveButton.disabled = false;
    }
}

function showToast(message, isError = false) {
    window.clearTimeout(toastTimer);
    elements.toast.textContent = message;
    elements.toast.classList.toggle("error", isError);
    elements.toast.classList.remove("hidden");
    toastTimer = window.setTimeout(() => elements.toast.classList.add("hidden"), 3200);
}

document.querySelector("#new-task-button").addEventListener("click", () => openModal());
document.querySelector("#empty-add-button").addEventListener("click", () => openModal());
document.querySelector("#close-modal-button").addEventListener("click", closeModal);
document.querySelector("#cancel-modal-button").addEventListener("click", closeModal);
elements.form.addEventListener("submit", saveTask);
elements.sort.addEventListener("change", () => {
    state.sort = elements.sort.value;
    loadTasks();
});
elements.search.addEventListener("input", () => {
    window.clearTimeout(searchTimer);
    searchTimer = window.setTimeout(() => {
        state.search = elements.search.value.trim();
        loadTasks();
    }, 220);
});
document.querySelectorAll(".filter-tab").forEach((button) => {
    button.addEventListener("click", () => {
        state.filter = button.dataset.filter;
        document.querySelectorAll(".filter-tab").forEach((tab) => {
            const active = tab === button;
            tab.classList.toggle("active", active);
            tab.setAttribute("aria-selected", active ? "true" : "false");
        });
        loadTasks();
    });
});
elements.modal.addEventListener("click", (event) => {
    if (event.target === elements.modal) closeModal();
});
document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !elements.modal.classList.contains("hidden")) closeModal();
});

refresh();
