const API = {
    async request(url, options = {}) {
        const response = await fetch(url, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        });
        return response.json();
    },
    
    get(url) {
        return this.request(url);
    },
    
    post(url, data) {
        return this.request(url, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },
    
    delete(url) {
        return this.request(url, { method: 'DELETE' });
    }
};

function showMessage(message, type = 'info') {
    const div = document.createElement('div');
    div.className = `message message-${type}`;
    div.textContent = message;
    document.body.appendChild(div);
    setTimeout(() => div.remove(), 3000);
}

function formatDate(dateString) {
    return new Date(dateString).toLocaleString();
}

async function logout() {
    await API.post('/auth/logout', {});
    window.location.href = '/';
}
