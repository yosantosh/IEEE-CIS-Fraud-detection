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
const previewSection = document.getElementById('preview-section');
const previewHeader = document.getElementById('preview-header');
const previewBody = document.getElementById('preview-body');
const rowCount = document.getElementById('row-count');
const predictBtn = document.getElementById('predict-btn');
const clearBtn = document.getElementById('clear-btn');
const resultsSection = document.getElementById('results-section');
const resultsBody = document.getElementById('results-body');
const loadingOverlay = document.getElementById('loading-overlay');
const apiStatus = document.getElementById('api-status');
const downloadBtn = document.getElementById('download-btn');

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
 * Parse tab-separated values from Excel/Sheets paste
 */
function parseTSV(text) {
    const lines = text.trim().split('\n');
    if (lines.length < 2) return [];

    // Parse header
    const headers = lines[0].split('\t').map(h => h.trim());

    // Parse data rows
    const data = [];
    for (let i = 1; i < lines.length; i++) {
        const values = lines[i].split('\t');
        if (values.length < 2) continue; // Skip empty or incomplete rows

        const row = {};
        headers.forEach((header, index) => {
            let value = values[index]?.trim() || '';

            // Try to parse as number
            if (value !== '' && !isNaN(value)) {
                value = parseFloat(value);
            }

            row[header] = value;
        });
        data.push(row);
    }

    return data;
}

/**
 * Update preview table with parsed data
 */
function updatePreview(data) {
    if (data.length === 0) {
        previewSection.style.display = 'none';
        predictBtn.disabled = true;
        return;
    }

    const headers = Object.keys(data[0]);
    const displayHeaders = headers.slice(0, 8); // Show first 8 columns only

    // Update header
    previewHeader.innerHTML = `
        <tr>
            ${displayHeaders.map(h => `<th>${h}</th>`).join('')}
            ${headers.length > 8 ? '<th>...</th>' : ''}
        </tr>
    `;

    // Update body (show first 5 rows)
    const displayData = data.slice(0, 5);
    previewBody.innerHTML = displayData.map(row => `
        <tr>
            ${displayHeaders.map(h => `<td>${row[h] ?? ''}</td>`).join('')}
            ${headers.length > 8 ? '<td>...</td>' : ''}
        </tr>
    `).join('');

    // Update count
    rowCount.textContent = `${data.length} rows`;

    // Show preview
    previewSection.style.display = 'block';
    predictBtn.disabled = false;
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
    previewSection.style.display = 'none';
    resultsSection.style.display = 'none';
    predictBtn.disabled = true;
}

// ============================================================================
// EVENT LISTENERS
// ============================================================================

// Paste area input
pasteArea.addEventListener('input', () => {
    const text = pasteArea.value;
    if (text.trim()) {
        parsedData = parseTSV(text);
        updatePreview(parsedData);
    } else {
        parsedData = [];
        updatePreview([]);
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

// Download button
downloadBtn.addEventListener('click', downloadCSV);

// ============================================================================
// INITIALIZATION
// ============================================================================

// Check API health on load
checkHealth();

// Periodically check health
setInterval(checkHealth, 30000);
