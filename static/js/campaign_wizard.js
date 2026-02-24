const wizardState = {
    currentStep: 1,
    provider: null,
    list: null,
    template: null,
    subject: '',
    htmlBody: '',
    textBody: '',
    campaignName: ''
};

function showStep(step) {
    document.querySelectorAll('.wizard-panel').forEach(el => el.style.display = 'none');
    document.getElementById(`step-${step}`).style.display = 'block';
    
    document.querySelectorAll('.wizard-step').forEach(el => el.classList.remove('active'));
    document.querySelector(`.wizard-step[data-step="${step}"]`).classList.add('active');
    
    for (let i = 1; i < step; i++) {
        document.querySelector(`.wizard-step[data-step="${i}"]`).classList.add('completed');
    }
    
    wizardState.currentStep = step;
    
    document.getElementById('prev-btn').style.display = step === 1 ? 'none' : 'inline-flex';
    document.getElementById('next-btn').textContent = step === 5 ? 'Send Campaign' : 'Next';
    
    if (step === 1) loadProviders();
    if (step === 2) loadLists();
    if (step === 3) loadTemplates();
    if (step === 4) showReview();
}

async function loadProviders() {
    const response = await fetch('/providers/list');
    const providers = await response.json();
    
    const container = document.getElementById('provider-list');
    container.innerHTML = providers.map(p => `
        <div class="selection-card" data-id="${p.id}" onclick="selectProvider(${p.id})">
            <div class="selection-card-title">${p.type}</div>
            <div class="selection-card-meta">${p.sender_email}</div>
            <div style="margin-top: 8px;">
                ${p.is_verified ? '<span class="badge badge-success">Verified</span>' : '<span class="badge badge-warning">Unverified</span>'}
            </div>
        </div>
    `).join('');
}

function selectProvider(id) {
    fetch('/providers/list').then(r => r.json()).then(providers => {
        wizardState.provider = providers.find(p => p.id === id);
        document.querySelectorAll('#provider-list .selection-card').forEach(c => c.classList.remove('selected'));
        document.querySelector(`#provider-list .selection-card[data-id="${id}"]`).classList.add('selected');
    });
}

async function loadLists() {
    const response = await fetch('/lists/list');
    const lists = await response.json();
    
    const container = document.getElementById('list-selection');
    container.innerHTML = lists.map(l => `
        <div class="selection-card" data-id="${l.id}" onclick="selectList(${l.id})">
            <div class="selection-card-title">${l.name}</div>
            <div class="selection-card-meta">${l.recipient_count} recipients</div>
        </div>
    `).join('');
}

function selectList(id) {
    fetch('/lists/list').then(r => r.json()).then(lists => {
        wizardState.list = lists.find(l => l.id === id);
        document.querySelectorAll('#list-selection .selection-card').forEach(c => c.classList.remove('selected'));
        document.querySelector(`#list-selection .selection-card[data-id="${id}"]`).classList.add('selected');
    });
}

async function loadTemplates() {
    const response = await fetch('/templates/list');
    const templates = await response.json();
    
    const container = document.getElementById('template-selection');
    container.innerHTML = templates.map(t => `
        <div class="selection-card" data-id="${t.id}" onclick="selectTemplate(${t.id})">
            <div class="selection-card-title">${t.name}</div>
            <div class="selection-card-meta">${t.subject}</div>
        </div>
    `).join('');
}

async function selectTemplate(id) {
    const response = await fetch(`/templates/${id}`);
    const template = await response.json();
    
    wizardState.template = template;
    wizardState.subject = template.subject;
    wizardState.htmlBody = template.html_body;
    wizardState.textBody = template.text_body;
    
    document.querySelectorAll('#template-selection .selection-card').forEach(c => c.classList.remove('selected'));
    document.querySelector(`#template-selection .selection-card[data-id="${id}"]`).classList.add('selected');
}

async function showReview() {
    const response = await fetch('/campaigns/wizard/validate', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            provider_id: wizardState.provider?.id,
            list_id: wizardState.list?.id,
            template_id: wizardState.template?.id,
            subject: wizardState.subject,
            html_body: wizardState.htmlBody,
            text_body: wizardState.textBody
        })
    });
    
    const validation = await response.json();
    
    document.getElementById('campaign-review').innerHTML = `
        <div class="review-section">
            <h3>Provider</h3>
            <p>${wizardState.provider?.sender_email} (${wizardState.provider?.type})</p>
        </div>
        <div class="review-section">
            <h3>Recipients</h3>
            <p>${wizardState.list?.name} - ${wizardState.list?.recipient_count} recipients</p>
        </div>
        <div class="review-section">
            <h3>Template</h3>
            <p>${wizardState.template?.name}</p>
        </div>
        <div class="review-section">
            <h3>Subject</h3>
            <p>${wizardState.subject}</p>
        </div>
    `;
    
    let validationHTML = '';
    
    if (validation.errors && validation.errors.length > 0) {
        validationHTML += '<div class="alert alert-error"><strong>Errors:</strong><br>' + 
            validation.errors.join('<br>') + '</div>';
    }
    
    if (validation.warnings && validation.warnings.length > 0) {
        validationHTML += '<div class="alert alert-warning"><strong>Warnings:</strong><br>' + 
            validation.warnings.join('<br>') + '</div>';
    }
    
    if (validation.valid) {
        validationHTML += '<div class="alert alert-success">Campaign ready to send</div>';
    }
    
    document.getElementById('validation-results').innerHTML = validationHTML;
}

document.getElementById('next-btn').addEventListener('click', () => {
    if (wizardState.currentStep < 5) {
        if (wizardState.currentStep === 1 && !wizardState.provider) {
            alert('Please select a provider');
            return;
        }
        if (wizardState.currentStep === 2 && !wizardState.list) {
            alert('Please select a list');
            return;
        }
        if (wizardState.currentStep === 3 && !wizardState.template) {
            alert('Please select a template');
            return;
        }
        showStep(wizardState.currentStep + 1);
    } else {
        sendCampaign();
    }
});

document.getElementById('prev-btn').addEventListener('click', () => {
    if (wizardState.currentStep > 1) {
        showStep(wizardState.currentStep - 1);
    }
});

async function sendCampaign() {
    wizardState.campaignName = document.getElementById('campaign-name').value;
    
    if (!wizardState.campaignName) {
        alert('Please enter a campaign name');
        return;
    }
    
    const response = await fetch('/campaigns/create', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            name: wizardState.campaignName,
            provider_id: wizardState.provider.id,
            list_id: wizardState.list.id,
            template_id: wizardState.template?.id,
            subject: wizardState.subject,
            html_body: wizardState.htmlBody,
            text_body: wizardState.textBody
        })
    });
    
    const result = await response.json();
    
    if (result.success) {
        const sendResponse = await fetch(`/campaigns/${result.id}/send`, {method: 'POST'});
        const sendResult = await sendResponse.json();
        
        if (sendResult.success) {
            document.getElementById('send-progress').innerHTML = `
                <div class="alert alert-success">Campaign sent successfully!</div>
            `;
            setTimeout(() => {
                window.location.href = '/campaigns';
            }, 2000);
        } else {
            document.getElementById('send-progress').innerHTML = `
                <div class="alert alert-error">${sendResult.error}</div>
            `;
        }
    } else {
        document.getElementById('send-progress').innerHTML = `
            <div class="alert alert-error">${result.error}</div>
        `;
    }
}

showStep(1);
