function showAddProvider() {
    document.getElementById('add-provider-modal').style.display = 'flex';
}

function closeModal() {
    document.getElementById('add-provider-modal').style.display = 'none';
}

async function updateProviderForm() {
    const type = document.getElementById('provider-type').value;
    const container = document.getElementById('dynamic-fields');
    
    if (!type) {
        container.innerHTML = '';
        return;
    }
    
    const response = await fetch('/providers/schemas');
    const schemas = await response.json();
    const schema = schemas[type];
    
    if (!schema) return;
    
    let html = '';
    
    if (schema.oauth) {
        html = '<div class="alert alert-info">This provider uses OAuth. You will be redirected to authorize access.</div>';
    } else {
        schema.fields.forEach(field => {
            html += `
                <div class="form-group">
                    <label class="form-label">${field.label}</label>
                    <input 
                        type="${field.type}" 
                        id="field-${field.name}" 
                        class="form-input" 
                        placeholder="${field.label}"
                        ${field.required ? 'required' : ''}
                        value="${field.default || ''}"
                    >
                </div>
            `;
        });
    }
    
    container.innerHTML = html;
}

async function saveProvider() {
    const type = document.getElementById('provider-type').value;
    const senderEmail = document.getElementById('sender-email').value;
    
    if (!type || !senderEmail) {
        alert('Please fill in all required fields');
        return;
    }
    
    const response = await fetch('/providers/schemas');
    const schemas = await response.json();
    const schema = schemas[type];
    
    const credentials = {};
    
    if (!schema.oauth) {
        schema.fields.forEach(field => {
            const input = document.getElementById(`field-${field.name}`);
            if (input) {
                credentials[field.name] = input.value;
            }
        });
    }
    
    const result = await fetch('/providers/add', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            provider_type: type,
            sender_email: senderEmail,
            credentials: credentials
        })
    });
    
    const data = await result.json();
    
    if (data.success) {
        location.reload();
    } else {
        alert(data.error || 'Failed to add provider');
    }
}

async function verifyProvider(id) {
    const result = await fetch(`/providers/${id}/verify`, {method: 'POST'});
    const data = await result.json();
    
    if (data.success) {
        alert('Provider verified successfully');
        location.reload();
    } else {
        alert(data.error || 'Verification failed');
    }
}

async function deleteProvider(id) {
    if (!confirm('Are you sure you want to delete this provider?')) return;
    
    const result = await fetch(`/providers/${id}`, {method: 'DELETE'});
    const data = await result.json();
    
    if (data.success) {
        location.reload();
    } else {
        alert(data.error || 'Failed to delete provider');
    }
}
