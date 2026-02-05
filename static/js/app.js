/**
 * IEEE-CIS Fraud Detection - Frontend JavaScript
 * Handles Excel/Sheets paste parsing and batch predictions
 */

// ============================================================================
// STATE
// ============================================================================

let parsedData = [];
let predictions = [];

// ============================================================================
// DOM ELEMENTS
// ============================================================================

const pasteArea = document.getElementById('paste-area');
const pasteWrapper = document.getElementById('paste-wrapper');
const previewSection = document.getElementById('preview-section');
const previewHeader = document.getElementById('preview-header');
const previewBody = document.getElementById('preview-body');
const rowCount = document.getElementById('row-count');
const predictBtn = document.getElementById('predict-btn');
const clearBtn = document.getElementById('clear-btn');
const editBtn = document.getElementById('edit-btn');
const resultsSection = document.getElementById('results-section');
const resultsBody = document.getElementById('results-body');
const loadingOverlay = document.getElementById('loading-overlay');
const apiStatus = document.getElementById('api-status');
const downloadBtn = document.getElementById('download-btn');
const fileInput = document.getElementById('file-upload');
const uploadBtn = document.getElementById('upload-btn');

// Stats elements
const totalCount = document.getElementById('total-count');
const fraudCount = document.getElementById('fraud-count');
const safeCount = document.getElementById('safe-count');
const fraudRate = document.getElementById('fraud-rate');

// ============================================================================
// API FUNCTIONS
// ============================================================================

/**
 * Check API health status
 */
async function checkHealth() {
    try {
        const response = await fetch('/health');
        const data = await response.json();

        if (data.status === 'healthy' && data.model_loaded) {
            apiStatus.classList.add('online');
            apiStatus.classList.remove('offline');
            apiStatus.querySelector('.status-text').textContent = 'Model Ready';
        } else {
            apiStatus.classList.remove('online');
            apiStatus.classList.add('offline');
            apiStatus.querySelector('.status-text').textContent = 'Model Loading...';
        }
    } catch (error) {
        apiStatus.classList.remove('online');
        apiStatus.classList.add('offline');
        apiStatus.querySelector('.status-text').textContent = 'API Offline';
    }
}

/**
 * Send batch prediction request
 */
async function predictBatch(transactions) {
    const response = await fetch('/predict', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ transactions }),
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Prediction failed');
    }

    return await response.json();
}

// ============================================================================
// PARSING FUNCTIONS
// ============================================================================

/**
 * Parse delimited text (auto-detect delimiter: tab, comma, semicolon, pipe)
 */
function parseDelimitedText(text) {
    const lines = text.trim().split(/\r?\n/);
    if (lines.length < 2) return [];

    // Auto-detect delimiter by checking first line
    const firstLine = lines[0];
    let delimiter = '\t'; // Default to tab

    // Count occurrences of common delimiters
    const delimiters = ['\t', ',', ';', '|'];
    let maxCount = 0;

    for (const d of delimiters) {
        const count = (firstLine.match(new RegExp(d === '|' ? '\\|' : d, 'g')) || []).length;
        if (count > maxCount) {
            maxCount = count;
            delimiter = d;
        }
    }

    // If no delimiter found, try space
    if (maxCount === 0) {
        delimiter = /\s+/;
    }

    // Parse header
    const headers = typeof delimiter === 'string'
        ? firstLine.split(delimiter).map(h => h.trim().replace(/^["']|["']$/g, ''))
        : firstLine.split(delimiter).map(h => h.trim().replace(/^["']|["']$/g, ''));

    if (headers.length < 2) return [];

    // Parse data rows
    const data = [];
    for (let i = 1; i < lines.length; i++) {
        const line = lines[i].trim();
        if (!line) continue; // Skip empty lines

        const values = typeof delimiter === 'string'
            ? line.split(delimiter)
            : line.split(delimiter);

        if (values.length < 2) continue; // Skip incomplete rows

        const row = {};
        headers.forEach((header, index) => {
            let value = (values[index] || '').trim().replace(/^["']|["']$/g, '');

            // Try to parse as number
            if (value !== '' && !isNaN(value) && value !== '') {
                const num = parseFloat(value);
                value = isNaN(num) ? value : num;
            }

            row[header] = value;
        });

        // Only add row if it has at least some data
        if (Object.values(row).some(v => v !== '' && v !== null && v !== undefined)) {
            data.push(row);
        }
    }

    return data;
}

/**
 * Handle file selection
 */
async function handleFileSelect(event) {
    const file = event.target.files[0];
    if (!file) return;

    showLoading(true);

    try {
        const data = await parseFile(file);
        if (!data || data.length === 0) {
            throw new Error('No data found in file');
        }
        parsedData = data;
        showTablePreview(parsedData);
    } catch (error) {
        alert('File parsing failed: ' + error.message);
        console.error(error);
    } finally {
        showLoading(false);
        // Reset input so same file can be selected again
        event.target.value = '';
    }
}

/**
 * Parse uploaded file
 */
function parseFile(file) {
    return new Promise((resolve, reject) => {
        const extension = file.name.split('.').pop().toLowerCase();

        if (extension === 'json') {
            const reader = new FileReader();
            reader.onload = (e) => {
                try {
                    const json = JSON.parse(e.target.result);
                    // Ensure it's an array
                    const result = Array.isArray(json) ? json : [json];
                    resolve(result);
                } catch (err) {
                    reject(new Error('Invalid JSON file'));
                }
            };
            reader.onerror = () => reject(new Error('Error reading file'));
            reader.readAsText(file);
        }
        else if (extension === 'csv') {
            if (typeof Papa === 'undefined') {
                reject(new Error('CSV parser not loaded'));
                return;
            }
            Papa.parse(file, {
                header: true,
                dynamicTyping: true,
                skipEmptyLines: true,
                complete: (results) => {
                    if (results.errors.length > 0 && !results.data.length) {
                        reject(new Error('CSV parsing error'));
                    } else {
                        resolve(results.data);
                    }
                },
                error: (err) => reject(new Error('CSV parsing error: ' + err.message))
            });
        }
        else if (['xlsx', 'xls'].includes(extension)) {
            if (typeof XLSX === 'undefined') {
                reject(new Error('Excel parser not loaded'));
                return;
            }
            const reader = new FileReader();
            reader.onload = (e) => {
                try {
                    const data = new Uint8Array(e.target.result);
                    const workbook = XLSX.read(data, { type: 'array' });
                    const firstSheetName = workbook.SheetNames[0];
                    const worksheet = workbook.Sheets[firstSheetName];
                    const json = XLSX.utils.sheet_to_json(worksheet);
                    resolve(json);
                } catch (err) {
                    reject(new Error('Excel parsing error: ' + err.message));
                }
            };
            reader.onerror = () => reject(new Error('Error reading file'));
            reader.readAsArrayBuffer(file);
        }
        else if (['tsv', 'txt'].includes(extension)) {
            // Handle TSV and TXT files using our delimiter parser
            const reader = new FileReader();
            reader.onload = (e) => {
                try {
                    const data = parseDelimitedText(e.target.result);
                    if (data.length === 0) {
                        reject(new Error('No valid data found in file'));
                    } else {
                        resolve(data);
                    }
                } catch (err) {
                    reject(new Error('Text file parsing error: ' + err.message));
                }
            };
            reader.onerror = () => reject(new Error('Error reading file'));
            reader.readAsText(file);
        }
        else {
            reject(new Error('Unsupported file format. Please use CSV, TSV, TXT, Excel, or JSON.'));
        }
    });
}

/**
 * Show table preview - hides paste area, shows formatted table
 */
function showTablePreview(data) {
    if (data.length === 0) {
        hideTablePreview();
        return;
    }

    const headers = Object.keys(data[0]);

    // Update header - show ALL columns (scrollable)
    previewHeader.innerHTML = `
        <tr>
            ${headers.map(h => `<th>${h}</th>`).join('')}
        </tr>
    `;

    // Update body (show first 10 rows for better preview)
    const displayData = data.slice(0, 10);
    previewBody.innerHTML = displayData.map(row => `
        <tr>
            ${headers.map(h => `<td>${row[h] ?? ''}</td>`).join('')}
        </tr>
    `).join('');

    // Update count
    rowCount.textContent = `${data.length} rows`;

    // IMMEDIATELY hide paste area and show table
    pasteWrapper.classList.add('hidden');
    previewSection.style.display = 'block';
    previewSection.classList.add('visible');

    predictBtn.disabled = false;
}

/**
 * Hide table preview and show paste area
 */
function hideTablePreview() {
    previewSection.classList.remove('visible');
    previewSection.style.display = 'none';
    pasteWrapper.classList.remove('hidden');

    predictBtn.disabled = true;
}

// ============================================================================
// RESULTS FUNCTIONS
// ============================================================================

/**
 * Display prediction results
 */
function displayResults(response) {
    predictions = response.predictions;

    // Update stats
    totalCount.textContent = response.total;
    fraudCount.textContent = response.fraud_count;
    safeCount.textContent = response.total - response.fraud_count;
    fraudRate.textContent = `${response.fraud_rate}%`;

    // Update table - Only show TransactionID and isFraud
    resultsBody.innerHTML = predictions.map(p => `
        <tr>
            <td>${p.TransactionID}</td>
            <td>
                <span class="fraud-tag ${p.isFraud === 1 ? 'fraud' : 'safe'}">
                    ${p.isFraud === 1 ? '⚠️ Fraud' : '✓ Safe'}
                </span>
            </td>
        </tr>
    `).join('');

    // Show results section
    resultsSection.style.display = 'block';

    // Scroll to results
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

/**
 * Download results as CSV
 */
function downloadCSV() {
    if (predictions.length === 0) return;

    const csv = [
        'TransactionID,isFraud',
        ...predictions.map(p => `${p.TransactionID},${p.isFraud}`)
    ].join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'fraud_predictions.csv';
    a.click();
    URL.revokeObjectURL(url);
}

// ============================================================================
// UI FUNCTIONS
// ============================================================================

function showLoading(show) {
    loadingOverlay.style.display = show ? 'flex' : 'none';
}

function clearInput() {
    pasteArea.value = '';
    parsedData = [];
    hideTablePreview();
    resultsSection.style.display = 'none';
}

function switchToEditMode() {
    // Hide preview, show paste area with data still there
    previewSection.classList.remove('visible');

    setTimeout(() => {
        pasteWrapper.classList.remove('hidden');
        pasteArea.focus();
    }, 150);
}

// ============================================================================
// EVENT LISTENERS
// ============================================================================

// Paste area input
pasteArea.addEventListener('input', () => {
    const text = pasteArea.value;
    if (text.trim()) {
        parsedData = parseDelimitedText(text);
        if (parsedData.length > 0) {
            showTablePreview(parsedData);
        } else {
            // If parsing failed, show an error
            console.warn('Could not parse pasted data. Ensure it has headers and at least one data row.');
        }
    } else {
        parsedData = [];
        hideTablePreview();
    }
});

// Predict button
predictBtn.addEventListener('click', async () => {
    if (parsedData.length === 0) return;

    showLoading(true);

    try {
        const response = await predictBatch(parsedData);
        displayResults(response);
    } catch (error) {
        alert('Prediction failed: ' + error.message);
        console.error('Prediction error:', error);
    } finally {
        showLoading(false);
    }
});

// Clear button
clearBtn.addEventListener('click', clearInput);

// Edit button (switch back to edit mode)
if (editBtn) {
    editBtn.addEventListener('click', switchToEditMode);
}

// Download button
downloadBtn.addEventListener('click', downloadCSV);

// File Upload
if (uploadBtn && fileInput) {
    uploadBtn.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', handleFileSelect);
}

// ============================================================================
// INITIALIZATION
// ============================================================================

// Check API health on load
checkHealth();

// Periodically check health
setInterval(checkHealth, 30000);
