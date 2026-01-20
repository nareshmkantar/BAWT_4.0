/**
 * BAWT - Reusable UI Components
 */

const Components = {
    createKPICard(data) {
        const { icon, value, label, change, changeType, accent } = data;
        return `
      <div class="kpi-card ${accent ? 'accent' : ''}">
        <div class="kpi-icon">${icon}</div>
        <div class="kpi-value">${value}</div>
        <div class="kpi-label">${label}</div>
        ${change ? `<div class="kpi-change ${changeType}"><span>${changeType === 'positive' ? '↑' : '↓'}</span><span>${change}</span></div>` : ''}
      </div>
    `;
    },

    getStatusBadge(status) {
        const map = { 'On Track': 'success', 'At Risk': 'warning', 'Under Budget': 'primary', 'Over Budget': 'error', 'Completed': 'success', 'Draft': 'primary', 'Applied': 'success', 'Approved': 'success', 'Archived': 'warning' };
        return map[status] || 'primary';
    },

    createTable(data) {
        const { columns, rows, actions } = data;
        let html = `<div class="table-container"><table class="table"><thead><tr>`;
        columns.forEach(col => html += `<th>${col}</th>`);
        if (actions) html += '<th>Actions</th>';
        html += `</tr></thead><tbody>`;
        rows.forEach(row => {
            html += `<tr data-id="${row.id}">`;
            columns.forEach(col => {
                const key = col.toLowerCase().replace(/\s/g, '');
                let val = row[key] || row[col] || '-';
                if (key === 'status') html += `<td><span class="badge badge-${this.getStatusBadge(val)}">${val}</span></td>`;
                else if (typeof val === 'number' && val > 1000) html += `<td>$${val.toLocaleString()}</td>`;
                else html += `<td>${val}</td>`;
            });
            if (actions) {
                html += `<td><div class="flex gap-2">`;
                actions.forEach(a => html += `<button class="btn btn-ghost btn-sm" data-action="${a.action}" title="${a.label}">${a.icon}</button>`);
                html += `</div></td>`;
            }
            html += `</tr>`;
        });
        return html + `</tbody></table></div>`;
    },

    createChartPlaceholder(title, height = '300px') {
        return `<div class="chart-placeholder" style="height:${height}"><div class="chart-placeholder-icon">📊</div><div class="text-muted">${title}</div><div class="text-secondary mt-4" style="font-size:var(--font-size-sm)">[PLACEHOLDER: Chart.js / D3.js]</div></div>`;
    },

    createQuickActions(actions) {
        return `<div class="quick-actions">${actions.map(a => `<div class="quick-action-card" data-page="${a.page}"><div class="quick-action-icon">${a.icon}</div><div class="quick-action-title">${a.title}</div><div class="quick-action-desc">${a.description}</div></div>`).join('')}</div>`;
    },

    showToast(message, type = 'info') {
        let c = document.querySelector('.toast-container');
        if (!c) { c = document.createElement('div'); c.className = 'toast-container'; document.body.appendChild(c); }
        const icons = { success: '✓', error: '✕', warning: '⚠', info: 'ℹ' };
        const t = document.createElement('div');
        t.className = `toast ${type}`;
        t.innerHTML = `<span class="toast-icon">${icons[type]}</span><span>${message}</span>`;
        c.appendChild(t);
        setTimeout(() => { t.style.animation = 'slideIn 0.3s ease reverse'; setTimeout(() => t.remove(), 300); }, 4000);
    },

    createSpinner(size = 24) { return `<div class="spinner" style="width:${size}px;height:${size}px"></div>`; },

    createInput(data) {
        const { id, label, type = 'text', placeholder, value = '', required } = data;
        return `<div class="form-group"><label class="form-label" for="${id}">${label}${required ? ' *' : ''}</label><input type="${type}" id="${id}" class="form-input" placeholder="${placeholder || ''}" value="${value}" ${required ? 'required' : ''}></div>`;
    },

    createSelect(data) {
        const { id, label, options, value = '', required } = data;
        return `<div class="form-group"><label class="form-label" for="${id}">${label}${required ? ' *' : ''}</label><select id="${id}" class="form-input form-select" ${required ? 'required' : ''}><option value="">Select...</option>${options.map(o => `<option value="${o.value}" ${o.value === value ? 'selected' : ''}>${o.label}</option>`).join('')}</select></div>`;
    },

    createSlider(data) {
        const { id, label, min = 0, max = 100, value = 50, unit = '%' } = data;
        return `<div class="form-group"><div class="flex-between mb-2"><label class="form-label" for="${id}">${label}</label><span class="text-secondary" id="${id}-value">${value}${unit}</span></div><input type="range" id="${id}" class="range-slider" min="${min}" max="${max}" value="${value}" oninput="document.getElementById('${id}-value').textContent=this.value+'${unit}'"></div>`;
    },

    createCard(data) {
        const { title, subtitle, content, actions } = data;
        let html = `<div class="card">`;
        if (title) {
            html += `<div class="card-header"><div><h3 class="card-title">${title}</h3>${subtitle ? `<p class="card-subtitle">${subtitle}</p>` : ''}</div>`;
            if (actions) html += `<div class="flex gap-2">${actions.map(a => `<button class="btn ${a.primary ? 'btn-primary' : 'btn-secondary'} btn-sm">${a.icon || ''} ${a.label}</button>`).join('')}</div>`;
            html += `</div>`;
        }
        return html + `<div class="card-content">${content}</div></div>`;
    },

    // ==========================================
    // MODAL SYSTEM
    // ==========================================

    activeModal: null,

    // Show a modal with custom content
    showModal(config) {
        const { title, content, buttons = [], size = 'medium', onClose } = config;

        // Remove any existing modal
        this.closeModal();

        const sizeClass = size === 'large' ? 'modal-lg' : size === 'small' ? 'modal-sm' : '';

        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal ${sizeClass}">
                <div class="modal-header">
                    <h3 class="modal-title">${title}</h3>
                    <button class="modal-close" id="modal-close-btn">&times;</button>
                </div>
                <div class="modal-body">
                    ${content}
                </div>
                ${buttons.length > 0 ? `
                <div class="modal-footer">
                    ${buttons.map(btn => `
                        <button class="btn ${btn.primary ? 'btn-primary' : 'btn-secondary'}" id="${btn.id || ''}" ${btn.disabled ? 'disabled' : ''}>
                            ${btn.label}
                        </button>
                    `).join('')}
                </div>` : ''}
            </div>
        `;

        document.body.appendChild(modal);
        this.activeModal = { element: modal, onClose };

        // Close on overlay click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) this.closeModal();
        });

        // Close button
        modal.querySelector('#modal-close-btn').addEventListener('click', () => this.closeModal());

        // Animate in
        requestAnimationFrame(() => modal.classList.add('active'));

        return modal;
    },

    closeModal() {
        if (this.activeModal) {
            const { element, onClose } = this.activeModal;
            element.classList.remove('active');
            setTimeout(() => {
                element.remove();
                if (onClose) onClose();
            }, 200);
            this.activeModal = null;
        }
    },

    // Confirmation dialog
    showConfirmModal(message, onConfirm, options = {}) {
        const { title = 'Confirm', confirmText = 'Confirm', cancelText = 'Cancel', danger = false } = options;

        const modal = this.showModal({
            title,
            content: `<p style="margin:0">${message}</p>`,
            size: 'small',
            buttons: [
                { label: cancelText, id: 'modal-cancel' },
                { label: confirmText, id: 'modal-confirm', primary: !danger }
            ]
        });

        modal.querySelector('#modal-cancel').addEventListener('click', () => this.closeModal());
        modal.querySelector('#modal-confirm').addEventListener('click', () => {
            this.closeModal();
            if (onConfirm) onConfirm();
        });

        if (danger) {
            modal.querySelector('#modal-confirm').classList.add('btn-danger');
        }
    },

    // Input prompt modal
    showPromptModal(config) {
        const { title, label, placeholder = '', value = '', onSubmit } = config;

        const modal = this.showModal({
            title,
            content: `
                <div class="form-group">
                    <label class="form-label">${label}</label>
                    <input type="text" class="form-input" id="modal-input" placeholder="${placeholder}" value="${value}">
                </div>
            `,
            size: 'small',
            buttons: [
                { label: 'Cancel', id: 'modal-cancel' },
                { label: 'Save', id: 'modal-submit', primary: true }
            ]
        });

        const input = modal.querySelector('#modal-input');
        input.focus();
        input.select();

        modal.querySelector('#modal-cancel').addEventListener('click', () => this.closeModal());
        modal.querySelector('#modal-submit').addEventListener('click', () => {
            const newValue = input.value.trim();
            if (newValue) {
                this.closeModal();
                if (onSubmit) onSubmit(newValue);
            }
        });

        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') modal.querySelector('#modal-submit').click();
        });
    },

    // Add Scenario Modal
    showAddScenarioModal(onAdd) {
        this.showPromptModal({
            title: 'Add New Scenario',
            label: 'Scenario Name',
            placeholder: 'e.g., Q1 2025 Plan',
            onSubmit: (name) => {
                if (onAdd) onAdd(name);
                this.showToast(`Scenario "${name}" created`, 'success');
            }
        });
    },

    // Share Modal
    showShareModal(item) {
        const shareUrl = `${window.location.origin}/share/${item.id || 'result'}`;

        this.showModal({
            title: 'Share Result',
            content: `
                <div class="share-content">
                    <p class="text-muted mb-3">Share "${item.name || 'Result'}" with your team:</p>
                    <div class="form-group">
                        <label class="form-label">Share Link</label>
                        <div class="input-with-button">
                            <input type="text" class="form-input" id="share-url" value="${shareUrl}" readonly>
                            <button class="btn btn-secondary" id="copy-link-btn">📋 Copy</button>
                        </div>
                    </div>
                    <div class="share-options mt-4">
                        <label class="form-label">Share via Email</label>
                        <div class="form-group">
                            <input type="email" class="form-input" id="share-email" placeholder="colleague@company.com">
                        </div>
                    </div>
                </div>
            `,
            size: 'medium',
            buttons: [
                { label: 'Close', id: 'modal-close' },
                { label: 'Send Email', id: 'modal-send', primary: true }
            ]
        });

        document.getElementById('copy-link-btn')?.addEventListener('click', () => {
            navigator.clipboard.writeText(shareUrl);
            this.showToast('Link copied to clipboard!', 'success');
        });

        document.getElementById('modal-close')?.addEventListener('click', () => this.closeModal());
        document.getElementById('modal-send')?.addEventListener('click', () => {
            const email = document.getElementById('share-email').value;
            if (email) {
                this.closeModal();
                this.showToast(`Shared with ${email}`, 'success');
            } else {
                this.showToast('Please enter an email', 'error');
            }
        });
    },

    // Import Data Modal with Progress and Validation
    showImportModal(onImport, options = {}) {
        const { dataType = 'auto', expectedFile = '' } = options;

        this.showModal({
            title: 'Import Data',
            content: `
                <div class="import-content">
                    <div class="form-group mb-4">
                        <label class="form-label">Data Type</label>
                        <select class="form-input form-select" id="import-data-type">
                            <option value="auto" ${dataType === 'auto' ? 'selected' : ''}>Auto-detect</option>
                            <option value="controls" ${dataType === 'controls' ? 'selected' : ''}>Controls & Settings</option>
                            <option value="curves" ${dataType === 'curves' ? 'selected' : ''}>Response Curves</option>
                            <option value="spend" ${dataType === 'spend' ? 'selected' : ''}>Weekly Spend / Budget</option>
                            <option value="constraints" ${dataType === 'constraints' ? 'selected' : ''}>Constraints</option>
                            <option value="cpms" ${dataType === 'cpms' ? 'selected' : ''}>CPMs</option>
                            <option value="weights" ${dataType === 'weights' ? 'selected' : ''}>Curve Weights</option>
                        </select>
                    </div>
                    ${expectedFile ? `<div class="text-muted mb-3" style="font-size: var(--font-size-sm);">Expected file: <strong>${expectedFile}</strong></div>` : ''}
                    <div class="upload-zone" id="upload-zone">
                        <div class="upload-icon">📁</div>
                        <div class="upload-text">Drag & drop files here or click to browse</div>
                        <div class="upload-hint">Supports CSV, Excel (.xlsx), JSON</div>
                        <input type="file" id="file-input" accept=".csv,.xlsx,.json" hidden>
                    </div>
                    <div class="selected-file hidden" id="selected-file">
                        <span class="file-icon">📄</span>
                        <span class="file-name" id="file-name"></span>
                        <button class="btn btn-ghost btn-sm" id="remove-file">✕</button>
                    </div>
                    <div class="import-progress hidden" id="import-progress">
                        <div class="progress-bar-container">
                            <div class="progress-bar" id="progress-bar" style="width: 0%"></div>
                        </div>
                        <div class="progress-text" id="progress-text">Processing...</div>
                    </div>
                    <div class="import-validation hidden" id="import-validation">
                        <div class="validation-header">
                            <span class="validation-icon" id="validation-icon">✓</span>
                            <span class="validation-title" id="validation-title">Validation Complete</span>
                        </div>
                        <div class="validation-details" id="validation-details"></div>
                    </div>
                </div>
            `,
            size: 'medium',
            buttons: [
                { label: 'Cancel', id: 'modal-cancel' },
                { label: 'Import', id: 'modal-import', primary: true, disabled: true }
            ]
        });

        const uploadZone = document.getElementById('upload-zone');
        const fileInput = document.getElementById('file-input');
        const selectedFile = document.getElementById('selected-file');
        const fileName = document.getElementById('file-name');
        const importBtn = document.getElementById('modal-import');
        const progressDiv = document.getElementById('import-progress');
        const validationDiv = document.getElementById('import-validation');

        let file = null;

        uploadZone?.addEventListener('click', () => fileInput?.click());

        // Drag and drop support
        uploadZone?.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadZone.classList.add('drag-over');
        });
        uploadZone?.addEventListener('dragleave', () => uploadZone.classList.remove('drag-over'));
        uploadZone?.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadZone.classList.remove('drag-over');
            if (e.dataTransfer.files.length > 0) {
                file = e.dataTransfer.files[0];
                this.handleFileSelected(file, fileName, uploadZone, selectedFile, importBtn);
            }
        });

        fileInput?.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                file = e.target.files[0];
                this.handleFileSelected(file, fileName, uploadZone, selectedFile, importBtn);
            }
        });

        document.getElementById('remove-file')?.addEventListener('click', () => {
            file = null;
            uploadZone.classList.remove('hidden');
            selectedFile.classList.add('hidden');
            validationDiv.classList.add('hidden');
            importBtn.disabled = true;
        });

        document.getElementById('modal-cancel')?.addEventListener('click', () => this.closeModal());

        importBtn?.addEventListener('click', async () => {
            if (file && onImport) {
                const dataTypeValue = document.getElementById('import-data-type').value;

                // Show progress
                selectedFile.classList.add('hidden');
                progressDiv.classList.remove('hidden');
                importBtn.disabled = true;

                // Simulate progress
                let progress = 0;
                const progressBar = document.getElementById('progress-bar');
                const progressText = document.getElementById('progress-text');

                const progressInterval = setInterval(() => {
                    progress += 10;
                    if (progressBar) progressBar.style.width = `${Math.min(progress, 90)}%`;
                    if (progress >= 30 && progressText) progressText.textContent = 'Validating data...';
                    if (progress >= 60 && progressText) progressText.textContent = 'Processing records...';
                    if (progress >= 90) clearInterval(progressInterval);
                }, 200);

                // Process file
                try {
                    await onImport(file, dataTypeValue);
                    clearInterval(progressInterval);
                    if (progressBar) progressBar.style.width = '100%';
                    if (progressText) progressText.textContent = 'Complete!';

                    setTimeout(() => {
                        this.closeModal();
                        this.showToast(`Successfully imported ${file.name}`, 'success');
                    }, 500);
                } catch (error) {
                    clearInterval(progressInterval);
                    progressDiv.classList.add('hidden');
                    validationDiv.classList.remove('hidden');
                    document.getElementById('validation-icon').textContent = '✕';
                    document.getElementById('validation-icon').style.color = 'var(--color-danger)';
                    document.getElementById('validation-title').textContent = 'Import Failed';
                    document.getElementById('validation-details').innerHTML = `<div class="text-danger">${error.message || 'Unknown error'}</div>`;
                }
            }
        });
    },

    handleFileSelected(file, fileNameEl, uploadZone, selectedFile, importBtn) {
        fileNameEl.textContent = file.name;
        uploadZone.classList.add('hidden');
        selectedFile.classList.remove('hidden');
        importBtn.disabled = false;
    },

    // Create New Item Modal
    showCreateModal(type, onCreate) {
        this.showModal({
            title: `Create New ${type}`,
            content: `
                <div class="form-group">
                    <label class="form-label">Name</label>
                    <input type="text" class="form-input" id="create-name" placeholder="Enter name...">
                </div>
                <div class="form-group">
                    <label class="form-label">Description</label>
                    <textarea class="form-input" id="create-desc" rows="3" placeholder="Optional description..."></textarea>
                </div>
                <div class="form-group">
                    <label class="form-label">Type</label>
                    <select class="form-input form-select" id="create-type">
                        <option value="model">Model</option>
                        <option value="curve">Response Curve</option>
                        <option value="template">Template</option>
                    </select>
                </div>
            `,
            buttons: [
                { label: 'Cancel', id: 'modal-cancel' },
                { label: 'Create', id: 'modal-create', primary: true }
            ]
        });

        document.getElementById('modal-cancel')?.addEventListener('click', () => this.closeModal());
        document.getElementById('modal-create')?.addEventListener('click', () => {
            const name = document.getElementById('create-name').value.trim();
            const desc = document.getElementById('create-desc').value.trim();
            const itemType = document.getElementById('create-type').value;

            if (name) {
                this.closeModal();
                if (onCreate) onCreate({ name, description: desc, type: itemType });
                this.showToast(`${type} "${name}" created`, 'success');
            } else {
                this.showToast('Please enter a name', 'error');
            }
        });
    }
};

window.Components = Components;
