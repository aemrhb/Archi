const API_BASE = "http://localhost:8000";

// --- STATE ---
let state = {
    hoaiLoaded: false,
    contractText: "",
    extractedData: null,
    reasoningLog: [],
    selectedModel: "mistral",
    chatHistory: [],
    auditReport: ""
};

// --- DOM ELEMENTS ---
const elements = {
    hoaiDrop: document.getElementById('hoaiDrop'),
    contractDrop: document.getElementById('contractDrop'),
    hoaiFile: document.getElementById('hoaiFile'),
    contractFile: document.getElementById('contractFile'),
    log: document.getElementById('reasoningLog'),
    status: document.getElementById('appStatus'),
    extractionView: document.getElementById('extractionView'),
    extractedData: document.getElementById('extractedData'),
    reportView: document.getElementById('reportView'),
    reportBody: document.getElementById('reportBody'),
    editModal: document.getElementById('editModal'),
    difficultyInput: document.getElementById('difficultyInput'),
    modelSelect: document.getElementById('modelSelect'),
    chatWidget: document.getElementById('chatWidget'),
    chatMessages: document.getElementById('chatMessages'),
    chatInput: document.getElementById('chatInput'),
    sendChatBtn: document.getElementById('sendChatBtn'),
    toggleChat: document.getElementById('toggleChat')
};

// --- LOGGING ---
function addLog(message, type = 'process') {
    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;
    
    // Handle DeepSeek <think> blocks
    let formattedMessage = message;
    if (message.includes('<think>')) {
        formattedMessage = message.replace('<think>', '<div class="think-block"><small>Reasoning...</small><br>')
                                  .replace('</think>', '</div>');
    }

    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    entry.innerHTML = `<span style="opacity:0.5">[${time}]</span> ${formattedMessage}`;
    elements.log.appendChild(entry);
    elements.log.scrollTop = elements.log.scrollHeight;
}

// --- API WRAPPERS ---
async function uploadFile(endpoint, file) {
    const formData = new FormData();
    formData.append('file', file);
    const response = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        body: formData
    });
    const result = await response.json();
    if (!response.ok) {
        throw new Error(result.detail || `Upload failed with status ${response.status}`);
    }
    return result;
}

// --- EVENT HANDLERS ---
elements.hoaiDrop.onclick = () => elements.hoaiFile.click();
elements.contractDrop.onclick = () => elements.contractFile.click();

elements.hoaiFile.onchange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    addLog(`Phase 1: Ingesting HOAI Reference: ${file.name}...`);
    elements.status.innerText = "Indexing HOAI...";
    
    try {
        const result = await uploadFile('/upload/hoai', file);
        state.hoaiLoaded = true;
        if (result.breakdown) {
            addLog(`Success: Smart-chunked into ${result.chunks} chunks (${result.breakdown.tables} tables, ${result.breakdown.sections} sections, ${result.breakdown.text} text).`, 'success');
        } else {
            addLog(`Success: Indexed ${result.chunks || result.pages} chunks into Vector Store.`, 'success');
        }
        elements.status.innerText = "HOAI Ready";
    } catch (err) {
        addLog(`Error: ${err.message}`, 'system');
    }
};

elements.contractFile.onchange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    addLog(`Phase 1: Ingesting Contract: ${file.name}...`);
    elements.status.innerText = "Extracting Text...";

    try {
        const result = await uploadFile('/upload/contract', file);
        state.contractText = result.text;
        addLog(`Success: Extracted ${result.text.length} characters from contract.`, 'success');
        
        // Trigger Phase 2 automatically
        runSemanticExtraction();
    } catch (err) {
        addLog(`Error: ${err.message}`, 'system');
    }
};

async function runSemanticExtraction() {
    addLog("Phase 2: Semantic Extraction starting... (this typically takes 15-45s)", 'process');
    elements.status.innerText = "LLM Reasoning...";

    try {
        addLog(`Sending request to backend using model: ${state.selectedModel}...`, 'system');
        const response = await fetch(`${API_BASE}/extract-parameters`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                text: state.contractText,
                model: state.selectedModel
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        addLog("Backend returned extraction results.", 'success');
        
        if (result.status === 'success') {
            state.extractedData = result.data;
            addLog(`LLM Analysis: ${result.data.reasoning}`, 'ai');
            renderExtraction(result.data);
            elements.extractionView.classList.remove('hidden');
            elements.status.innerText = "Awaiting Confirmation";
        } else {
            addLog(`Partial extraction or JSON error. Check Reasoning Log.`, 'warning');
            addLog(`Raw LLM Output: ${result.raw_output || result.error}`, 'system');
            elements.status.innerText = "Extraction Issue";
        }
    } catch (err) {
        addLog(`Extraction Error: ${err.message}`, 'system');
    }
}

function renderExtraction(data) {
    const feeDisplay = data.contract_fee ? `${data.contract_fee.toLocaleString()} EUR` : '<span style="color:#ef4444">Not detected</span>';
    elements.extractedData.innerHTML = `
        <div class="data-grid">
            <div class="data-item">
                <label>Chargeable Costs</label>
                <div class="value">${data.costs.toLocaleString()} EUR</div>
            </div>
            <div class="data-item">
                <label>Agreed Fee (Contract)</label>
                <div class="value">${feeDisplay}</div>
            </div>
            <div class="data-item">
                <label>Service Phases</label>
                <div class="value">${data.service_phases.join(', ')}</div>
            </div>
            <div class="data-item">
                <label>Qualitative Clues</label>
                <ul class="clue-list">
                    ${data.complexity_clues.map(c => `<li>${c}</li>`).join('')}
                </ul>
            </div>
        </div>
    `;
}

// --- CONFIRMATION & AUDIT ---
document.getElementById('editDataBtn').onclick = () => {
    elements.difficultyInput.value = state.extractedData.complexity_clues.join('\n');
    elements.editModal.classList.remove('hidden');
};

document.getElementById('closeModal').onclick = () => elements.editModal.classList.add('hidden');

document.getElementById('saveDifficulty').onclick = () => {
    const lines = elements.difficultyInput.value.split('\n').filter(l => l.trim());
    state.extractedData.complexity_clues = lines;
    renderExtraction(state.extractedData);
    elements.editModal.classList.add('hidden');
    addLog("User refined technical difficulty parameters.", 'system');
};

document.getElementById('confirmDataBtn').onclick = async () => {
    if (!state.hoaiLoaded) {
        alert("Please upload the HOAI reference first.");
        return;
    }

    addLog(`Phase 4: HOAI RAG Audit starting with ${state.selectedModel}...`, 'process');
    elements.status.innerText = "Querying HOAI DB...";
    elements.extractionView.classList.add('hidden');

    try {
        const auditData = {
            ...state.extractedData,
            model: state.selectedModel
        };
        const response = await fetch(`${API_BASE}/audit`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(auditData)
        });
        const result = await response.json();
        
        // Log RAG Snippets
        if (result.referenced_texts && result.referenced_context) {
            addLog(`Retrieved ${result.referenced_texts.length} relevant HOAI snippets:`, 'process');
            result.referenced_texts.forEach((text, i) => {
                const meta = result.referenced_context[i];
                const snippet = text.length > 300 ? text.substring(0, 300) + "..." : text;
                addLog(`[RAG SNIPPET] {Source: ${meta.source}, Page: ${meta.page}} "${snippet}"`, 'ai');
            });
        }

        addLog("Phase 5: Comparison and Report Generation complete.", 'success');
        state.auditReport = result.audit_report;
        elements.reportBody.innerText = result.audit_report;
        elements.reportView.classList.remove('hidden');
        elements.status.innerText = "Audit Finished";
        
        elements.reportView.scrollIntoView({ behavior: 'smooth' });
    } catch (err) {
        addLog(`Audit Error: ${err.message}`, 'system');
    }
};

// --- INITIALIZATION ---
async function initModels() {
    try {
        const response = await fetch(`${API_BASE}/models`);
        const models = await response.json();
        
        elements.modelSelect.innerHTML = models.map(m => 
            `<option value="${m}" ${m.includes('qwen3.5') ? 'selected' : (m.includes('mistral') && !models.some(x => x.includes('qwen3.5')) ? 'selected' : '')}>${m}</option>`
        ).join('');
        
        state.selectedModel = elements.modelSelect.value;
        addLog(`Available models loaded. Default: ${state.selectedModel}`, 'system');

        // Check HOAI status
        const hoaiStatusResponse = await fetch(`${API_BASE}/status/hoai`);
        const hoaiStatus = await hoaiStatusResponse.json();
        if (hoaiStatus.status === 'success' && hoaiStatus.count > 0) {
            state.hoaiLoaded = true;
            elements.status.innerText = "HOAI Ready";
            addLog(`Found existing HOAI reference database with ${hoaiStatus.count} pages. Upload optional.`, 'success');
            
            // Visual feedback on the drop area
            const hoaiContent = elements.hoaiDrop.querySelector('.content');
            if (hoaiContent) {
                hoaiContent.innerHTML = `
                    <span class="icon">✅</span>
                    <p>HOAI Ready (Offline)</p>
                    <span style="font-size:0.7em; opacity:0.7">${hoaiStatus.count} pages indexed</span>
                `;
                elements.hoaiDrop.style.borderColor = "rgba(34, 197, 94, 0.5)";
            }
        }
    } catch (err) {
        addLog("Failed to fetch models or HOAI status from backend.", "system");
    }
}

elements.modelSelect.onchange = (e) => {
    state.selectedModel = e.target.value;
    addLog(`Switched to model: ${state.selectedModel}`, 'system');
};

// --- CHAT LOGIC ---
function addChatMessage(message, role) {
    const entry = document.createElement('div');
    entry.className = `message ${role}`;
    entry.textContent = message;
    elements.chatMessages.appendChild(entry);
    elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
}

async function sendChatMessage() {
    const message = elements.chatInput.value.trim();
    if (!message) return;

    addChatMessage(message, 'user');
    elements.chatInput.value = '';
    elements.sendChatBtn.disabled = true;
    elements.sendChatBtn.textContent = '...';
    
    // Add to history
    state.chatHistory.push({ role: 'user', content: message });

    try {
        const response = await fetch(`${API_BASE}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: message,
                contract_text: state.contractText,
                audit_report: state.auditReport,
                history: state.chatHistory,
                model: state.selectedModel
            })
        });

        const result = await response.json();
        if (result.status === 'success') {
            let botResponse = result.response;
            
            // Check for report updates
            const updateMatch = botResponse.match(/\[UPDATE_REPORT\]([\s\S]*?)\[\/UPDATE_REPORT\]/);
            if (updateMatch) {
                const newReport = updateMatch[1].trim();
                state.auditReport = newReport;
                elements.reportBody.innerText = newReport;
                addLog("Chatbot updated the Discrepancy Report.", 'success');
                // Remove the tag from the message displayed in chat
                botResponse = botResponse.replace(/\[UPDATE_REPORT\][\s\S]*?\[\/UPDATE_REPORT\]/, "(Audit Report has been updated below)").trim();
            }

            addChatMessage(botResponse, 'assistant');
            state.chatHistory.push({ role: 'assistant', content: botResponse });
        }
    } catch (err) {
        addChatMessage(`Error: ${err.message}`, 'assistant');
    } finally {
        elements.sendChatBtn.disabled = false;
        elements.sendChatBtn.textContent = 'Send';
    }
}

elements.sendChatBtn.onclick = sendChatMessage;
elements.chatInput.onkeypress = (e) => {
    if (e.key === 'Enter') sendChatMessage();
};

elements.toggleChat.onclick = () => {
    elements.chatWidget.classList.toggle('minimized');
    elements.toggleChat.textContent = elements.chatWidget.classList.contains('minimized') ? '+' : '×';
};

initModels();
addLog("Ready for document ingestion.", 'system');
