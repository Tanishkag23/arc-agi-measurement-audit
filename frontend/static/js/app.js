console.log('🚀 ARC APP v3.0 LOADED');

// ========== SAFE DOM GETTER ==========
// NOTE: $$() has been removed entirely. Use $() / document.getElementById().
function $(id) {
    var el = document.getElementById(id);
    if (!el) console.warn('Missing element:', id);
    return el;
}

function setText(id, text) {
    var el = document.getElementById(id);
    if (el) el.textContent = text;
}

function num(v, digits) {
    if (v === undefined || v === null || isNaN(v)) return '-';
    return Number(v).toFixed(digits === undefined ? 3 : digits);
}

// ========== INIT ==========
document.addEventListener('DOMContentLoaded', function() {
    console.log('📄 DOM ready');
    loadHealth();
    loadDashboard();
    // cacheUpload already has inline onchange="handleCacheUpload(event)" in HTML.
    // Do NOT addEventListener here or the file uploads twice.
});

// ========== HEALTH ==========
function loadHealth() {
    fetch('/api/health')
        .then(function(r){ return r.json(); })
        .then(function(d){
            console.log('✅ Health:', d);
            var bar = document.getElementById('statusBar');
            if (!bar) return;
            bar.className = 'status-bar status-ok';
            bar.innerHTML = '<span>✅ Backend connected | Cache: ' + d.cache_loaded +
                ' | Scores: ' + (d.scores_loaded ? '✅' : '❌') +
                ' | Labels: ' + (d.labels_loaded ? '✅' : '❌') + '</span>';
        })
        .catch(function(e){
            console.log('Health check failed:', e.message);
            var bar = document.getElementById('statusBar');
            if (bar) {
                bar.className = 'status-bar status-error';
                bar.innerHTML = '<span>❌ Backend error: ' + e.message + '</span>';
            }
        });
}

// ========== DASHBOARD ==========
function loadDashboard() {
    var statsEl = document.getElementById('dashStats');
    if (statsEl) statsEl.innerHTML = '<tr><td colspan="2" style="color:#888">Loading...</td></tr>';

    fetch('/api/analysis/overview')
        .then(function(r){
            if (!r.ok) throw new Error('HTTP ' + r.status);
            return r.json();
        })
        .then(function(d){
            console.log('📊 Overview:', d);
            setText('dashTasks', d.total_tasks || 0);
            setText('dashCats', d.categories || 0);
            setText('dashSolvers', d.solvers || 0);
            setText('dashCache', d.cache_predictions || 0);

            if (statsEl) {
                statsEl.innerHTML =
                    '<tr><td>Total Tasks</td><td style="font-weight:600">' + (d.total_tasks || 0) + '</td></tr>' +
                    '<tr><td>Total Runs</td><td style="font-weight:600">' + (d.total_runs || 0) + '</td></tr>' +
                    '<tr><td>Labeled Tasks</td><td style="font-weight:600">' + (d.labeled_tasks || 0) + '</td></tr>' +
                    '<tr><td>Categories</td><td style="font-weight:600">' + (d.categories || 0) + '</td></tr>' +
                    '<tr><td>Solvers</td><td style="font-weight:600">' + (d.solvers || 0) + '</td></tr>' +
                    '<tr><td>Versions</td><td style="font-weight:600">' + (d.versions || 0) + '</td></tr>';
            }
        })
        .catch(function(e){
            console.log('Dashboard failed:', e.message);
            if (statsEl) statsEl.innerHTML = '<tr><td colspan="2" style="color:#ff6b6b">Error: ' + e.message + '</td></tr>';
        });
}

// ========== PHASE A ==========
function loadPhaseA() {
    var container = document.getElementById('phaseAContent');
    if (!container) { console.warn('Missing element: phaseAContent'); return; }
    container.innerHTML = '<p style="color:#888">Loading...</p>';

    fetch('/api/analysis/phase-a')
        .then(function(r){
            if (!r.ok) throw new Error('HTTP ' + r.status);
            return r.json();
        })
        .then(function(d){
            console.log('📉 Phase A:', d);
            var rows = d.data || [];
            if (rows.length === 0) {
                container.innerHTML = '<p style="color:#888">No Phase A data available.</p>';
                return;
            }
            var html = '<p style="color:#51cf66;margin-bottom:12px">✅ Loaded ' + rows.length + ' cross-version comparisons</p>';
            html += '<table class="data-table"><thead><tr>' +
                '<th>Solver</th><th>Metric</th><th>v1 Score</th><th>v2 Score</th><th>Drop</th><th>Verdict</th>' +
                '</tr></thead><tbody>';
            for (var i = 0; i < rows.length; i++) {
                var row = rows[i];
                var dropStyle = '';
                if (row.drop > 0.1) dropStyle = ' style="color:#ff6b6b;font-weight:600"';
                else if (row.drop < 0) dropStyle = ' style="color:#51cf66;font-weight:600"';
                var dropText = (row.drop === undefined || row.drop === null)
                    ? '-'
                    : (row.drop > 0 ? '+' : '') + num(row.drop, 3);
                html += '<tr>' +
                    '<td>' + (row.solver || '') + '</td>' +
                    '<td><code style="background:#1a2332;padding:2px 6px;border-radius:4px">' + (row.metric || '') + '</code></td>' +
                    '<td>' + num(row.v1_score, 3) + '</td>' +
                    '<td>' + num(row.v2_score, 3) + '</td>' +
                    '<td' + dropStyle + '>' + dropText + '</td>' +
                    '<td>' + verdictBadge(row.verdict) + '</td>' +
                    '</tr>';
            }
            html += '</tbody></table>';
            container.innerHTML = html;
        })
        .catch(function(e){
            console.log('Phase A failed:', e.message);
            container.innerHTML = '<p style="color:#ff6b6b">Error loading Phase A: ' + e.message + '</p>';
        });
}

// ========== PHASE B ==========
function loadPhaseB() {
    var container = document.getElementById('phaseBContent');
    if (!container) { console.warn('Missing element: phaseBContent'); return; }
    container.innerHTML = '<p style="color:#888">Loading...</p>';

    fetch('/api/analysis/phase-b')
        .then(function(r){
            if (!r.ok) throw new Error('HTTP ' + r.status);
            return r.json();
        })
        .then(function(d){
            console.log('🎯 Phase B:', d);
            var cats = d.categories || [];
            if (cats.length === 0) {
                container.innerHTML = '<p style="color:#888">No Phase B data available.</p>';
                return;
            }
            var html = '<p style="color:#51cf66;margin-bottom:12px">✅ Loaded ' + cats.length + ' categories</p>';
            html += '<table class="data-table"><thead><tr>' +
                '<th>Category</th><th>Tasks</th><th>Avg Exact</th><th>Avg Cell</th><th>Avg Object</th><th>Avg Edit</th>' +
                '</tr></thead><tbody>';
            for (var i = 0; i < cats.length; i++) {
                var cat = cats[i];
                html += '<tr>' +
                    '<td><strong>' + (cat.name || '') + '</strong></td>' +
                    '<td>' + (cat.task_count || 0) + '</td>' +
                    '<td>' + num(cat.avg_exact, 3) + '</td>' +
                    '<td>' + num(cat.avg_cell, 3) + '</td>' +
                    '<td>' + num(cat.avg_object, 3) + '</td>' +
                    '<td>' + num(cat.avg_edit, 3) + '</td>' +
                    '</tr>';
            }
            html += '</tbody></table>';

            var rankings = d.rankings || [];
            if (rankings.length > 0) {
                html += '<h3 style="margin-top:24px">Solver Rankings by Category</h3>';
                html += '<table class="data-table"><thead><tr>' +
                    '<th>Category</th><th>Best Solver</th><th>Score</th><th>Worst Solver</th><th>Score</th>' +
                    '</tr></thead><tbody>';
                for (var j = 0; j < rankings.length; j++) {
                    var rk = rankings[j];
                    html += '<tr>' +
                        '<td>' + (rk.category || '') + '</td>' +
                        '<td style="color:#51cf66;font-weight:600">' + (rk.best_solver || '') + '</td>' +
                        '<td style="color:#51cf66">' + num(rk.best_score, 3) + '</td>' +
                        '<td style="color:#ff6b6b;font-weight:600">' + (rk.worst_solver || '') + '</td>' +
                        '<td style="color:#ff6b6b">' + num(rk.worst_score, 3) + '</td>' +
                        '</tr>';
                }
                html += '</tbody></table>';
            }
            container.innerHTML = html;
        })
        .catch(function(e){
            console.log('Phase B failed:', e.message);
            container.innerHTML = '<p style="color:#ff6b6b">Error loading Phase B: ' + e.message + '</p>';
        });
}

// ========== TASKS ==========
var allTasks = [];

function loadTasks() {
    var container = document.getElementById('tasksContent');
    if (!container) { console.warn('Missing element: tasksContent'); return; }
    container.innerHTML = '<p style="color:#888">Loading...</p>';

    fetch('/api/tasks?limit=5000')
        .then(function(r){
            if (!r.ok) throw new Error('HTTP ' + r.status);
            return r.json();
        })
        .then(function(d){
            console.log('📋 Tasks:', d);
            allTasks = d.tasks || [];
            renderTasks();
        })
        .catch(function(e){
            console.log('Tasks failed:', e.message);
            container.innerHTML = '<p style="color:#ff6b6b">Error loading tasks: ' + e.message + '</p>';
        });
}

function renderTasks() {
    var container = document.getElementById('tasksContent');
    if (!container) return;

    var filterEl = document.getElementById('taskFilter');
    var filter = filterEl ? filterEl.value.toLowerCase().trim() : '';

    var filtered = allTasks;
    if (filter) {
        filtered = allTasks.filter(function(t){
            return ((t.task_id || '').toLowerCase().indexOf(filter) !== -1) ||
                   ((t.category || '').toLowerCase().indexOf(filter) !== -1) ||
                   ((t.solver  || '').toLowerCase().indexOf(filter) !== -1);
        });
    }

    if (allTasks.length === 0) {
        container.innerHTML = '<p style="color:#888">No tasks loaded. Upload data in the Upload tab.</p>';
        return;
    }
    if (filtered.length === 0) {
        container.innerHTML = '<p style="color:#888">No tasks match your filter.</p>';
        return;
    }

    var limit = Math.min(filtered.length, 100);
    var html = '<p style="margin-bottom:12px;color:#888">Showing ' + limit + ' of ' + filtered.length +
               ' matched (' + allTasks.length + ' total)</p>';
    html += '<table class="data-table"><thead><tr>' +
        '<th>Task ID</th><th>Solver</th><th>Version</th><th>Exact</th><th>Cell</th><th>Object</th><th>Edit</th><th>Category</th>' +
        '</tr></thead><tbody>';

    for (var i = 0; i < limit; i++) {
        var t = filtered[i];
        html += '<tr>' +
            '<td><code style="background:#1a2332;padding:2px 6px;border-radius:4px">' + (t.task_id || '') + '</code></td>' +
            '<td>' + (t.solver || '') + '</td>' +
            '<td>' + (t.version || '') + '</td>' +
            '<td>' + num(t.exact_score, 2) + '</td>' +
            '<td>' + num(t.cell_score, 2) + '</td>' +
            '<td>' + num(t.object_score, 2) + '</td>' +
            '<td>' + num(t.edit_score, 2) + '</td>' +
            '<td>' + (t.category || '-') + '</td>' +
            '</tr>';
    }
    if (filtered.length > limit) {
        html += '<tr><td colspan="8" style="text-align:center;color:#888">... and ' +
                (filtered.length - limit) + ' more rows (refine the filter)</td></tr>';
    }
    html += '</tbody></table>';
    container.innerHTML = html;
}

function filterTasks() {
    renderTasks();
}

// ========== LIVE SOLVER ==========

// Writes into #solverResultBody and reveals the #solverOutput card.
function showSolverResult(html) {
    var card = document.getElementById('solverOutput');
    var body = document.getElementById('solverResultBody');
    if (body) body.innerHTML = html;
    if (card) card.style.display = 'block';
}

function hideSolverResult() {
    var card = document.getElementById('solverOutput');
    var body = document.getElementById('solverResultBody');
    if (body) body.innerHTML = '';
    if (card) card.style.display = 'none';
}

function loadDemoTask() {
    var demo = {
        "task_id": "demo_symmetry",
        "train": [
            {"input": [[0,0,0],[0,1,0],[0,0,0]], "output": [[1,1,1],[1,0,1],[1,1,1]]},
            {"input": [[2,2],[2,2]], "output": [[0,0],[0,0]]}
        ],
        "test": [{"input": [[5,5,5],[5,5,5],[5,5,5]]}]
    };
    var ta = document.getElementById('taskInput');
    if (ta) ta.value = JSON.stringify(demo, null, 2);
    hideSolverResult();
    console.log('Demo task loaded');
}

function clearTask() {
    var ta = document.getElementById('taskInput');
    if (ta) ta.value = '';
    hideSolverResult();
    console.log('Task cleared');
}

function setSolveBtnBusy(busy) {
    var btn = document.getElementById('solveBtn');
    if (!btn) return;
    btn.disabled = !!busy;
    btn.textContent = busy ? '⏳ Solving...' : '▶️ Solve Task';
}

function solveTask(allStrategies) {
    var inputEl = document.getElementById('taskInput');
    if (!inputEl) {
        showSolverResult('<p style="color:#ff6b6b">Internal error: textarea #taskInput not found</p>');
        return;
    }

    var raw = inputEl.value;
    if (!raw || !raw.trim()) {
        showSolverResult('<p style="color:#ff6b6b">⚠️ Please paste a task JSON first</p>');
        return;
    }

    var body;
    try {
        body = JSON.parse(raw);
    } catch (e) {
        showSolverResult('<p style="color:#ff6b6b">❌ Invalid JSON: ' + e.message + '</p>');
        return;
    }

    if (allStrategies) body.all_strategies = true;

    setSolveBtnBusy(true);
    showSolverResult('<p style="color:#888">Loading...</p>');

    fetch('/api/solve', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(body)
    })
    .then(function(r){
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
    })
    .then(function(d){
        console.log('🧪 Solver:', d);
        setSolveBtnBusy(false);

        var html = '';
        if (d.cache_hit) {
            html += '<div style="background:#064e3b;padding:12px 16px;border-radius:8px;margin-bottom:16px">' +
                '<strong style="color:#51cf66">⚡ Cache Hit</strong> — found in NVIDIA training data' +
                (d.solver ? ' (<code style="background:#1a2332;padding:2px 6px;border-radius:4px">' +
                    d.solver + ' ' + (d.version || '') + '</code>)' : '') +
                '</div>';
        } else {
            html += '<p style="color:#888;margin-bottom:16px">No cache hit — ran rule-based strategies' +
                (d.solver ? ' (' + d.solver + ')' : '') + '.</p>';
        }

        var preds = d.predictions || [];
        if (preds.length > 0) {
            html += '<table class="data-table"><thead><tr>' +
                '<th>Strategy</th><th>Exact</th><th>Cell</th><th>Object</th><th>Edit</th><th>Preview</th>' +
                '</tr></thead><tbody>';
            for (var i = 0; i < preds.length; i++) {
                var p = preds[i];
                var exactStyle = p.exact_score >= 1 ? ' style="color:#51cf66;font-weight:600"' : '';
                html += '<tr>' +
                    '<td><strong>' + (p.strategy || '') + '</strong></td>' +
                    '<td' + exactStyle + '>' + num(p.exact_score, 2) + '</td>' +
                    '<td>' + num(p.cell_score, 2) + '</td>' +
                    '<td>' + num(p.object_score, 2) + '</td>' +
                    '<td>' + num(p.edit_score, 2) + '</td>' +
                    '<td>' + renderMiniGrid(p.pred) + '</td>' +
                    '</tr>';
            }
            html += '</tbody></table>';
        } else {
            html += '<p style="color:#888">No predictions generated.</p>';
        }
        showSolverResult(html);
    })
    .catch(function(e){
        console.log('Solver failed:', e.message);
        setSolveBtnBusy(false);
        showSolverResult('<p style="color:#ff6b6b">❌ Error: ' + e.message + '</p>');
    });
}

// Referenced by index.html: onclick="solveAllStrategies()"
function solveAllStrategies() {
    console.log('Running all strategies');
    solveTask(true);
}

function renderMiniGrid(grid) {
    if (!grid || !grid.length) return '-';
    var colors = ['#111','#0074d9','#2ecc40','#ff4136','#ffdc00','#aaa','#f012be','#ff851b','#7fdbff','#870c25'];
    var html = '<div style="display:inline-block;border:2px solid #334155;border-radius:4px;overflow:hidden">';
    for (var r = 0; r < grid.length; r++) {
        var row = grid[r] || [];
        var size = Math.max(10, Math.min(20, 160 / Math.max(row.length, 1)));
        html += '<div style="display:flex">';
        for (var c = 0; c < row.length; c++) {
            var color = colors[row[c]] || '#333';
            html += '<div style="width:' + size + 'px;height:' + size + 'px;background:' + color +
                    ';border:0.5px solid #222"></div>';
        }
        html += '</div>';
    }
    html += '</div>';
    return html;
}

// ========== UPLOAD ==========
function setUploadStatus(id, msg, isError) {
    var el = document.getElementById(id);
    if (!el) return;
    el.innerHTML = '<p style="color:' + (isError ? '#ff6b6b' : '#51cf66') +
                   ';font-size:0.85rem;margin-top:8px">' + msg + '</p>';
}

function handleCacheUpload(event) {
    var input = event && event.target ? event.target : document.getElementById('cacheUpload');
    if (!input || !input.files || !input.files[0]) return;
    var file = input.files[0];

    setUploadStatus('cacheUploadStatus', 'Loading...', false);

    var reader = new FileReader();
    reader.onload = function(e) {
        var data;
        try {
            data = JSON.parse(e.target.result);
        } catch (err) {
            setUploadStatus('cacheUploadStatus', '❌ Invalid JSON: ' + err.message, true);
            return;
        }
        fetch('/api/upload/cache', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        })
        .then(function(r){
            if (!r.ok) throw new Error('HTTP ' + r.status);
            return r.json();
        })
        .then(function(d){
            console.log('Cache uploaded:', d);
            setUploadStatus('cacheUploadStatus', '✅ Cache uploaded: ' + (d.count || 0) + ' predictions', false);
            loadHealth();
            loadDashboard();
        })
        .catch(function(err){
            console.log('Cache upload failed:', err.message);
            setUploadStatus('cacheUploadStatus', '❌ Upload failed: ' + err.message, true);
        });
    };
    reader.onerror = function() {
        setUploadStatus('cacheUploadStatus', '❌ Could not read file', true);
    };
    reader.readAsText(file);
}

// Referenced by index.html: onchange="uploadFile(this, 'scores')" and 'labels'
function uploadFile(inputEl, kind) {
    if (!inputEl || !inputEl.files || !inputEl.files[0]) return;
    var statusId = kind + 'UploadStatus';
    var file = inputEl.files[0];

    setUploadStatus(statusId, 'Loading...', false);

    var fd = new FormData();
    fd.append('file', file);

    fetch('/api/upload/' + kind, { method: 'POST', body: fd })
        .then(function(r){
            if (!r.ok) throw new Error('HTTP ' + r.status);
            return r.json();
        })
        .then(function(d){
            console.log(kind + ' uploaded:', d);
            setUploadStatus(statusId, '✅ ' + kind + ' uploaded: ' + (d.count || d.rows || 'ok'), false);
            loadHealth();
            loadDashboard();
        })
        .catch(function(e){
            console.log(kind + ' upload failed:', e.message);
            setUploadStatus(statusId, '❌ Upload failed: ' + e.message, true);
        });
}

// ========== TABS ==========
function showTab(id) {
    console.log('Tab clicked:', id);

    var tabs = document.querySelectorAll('.tab');
    var sections = document.querySelectorAll('.section');
    var i;

    for (i = 0; i < sections.length; i++) sections[i].classList.remove('active');
    for (i = 0; i < tabs.length; i++) tabs[i].classList.remove('active');

    for (i = 0; i < tabs.length; i++) {
        var oc = tabs[i].getAttribute('onclick') || '';
        if (oc.indexOf("'" + id + "'") !== -1) {
            tabs[i].classList.add('active');
            break;
        }
    }

    var section = document.getElementById(id);
    if (section) section.classList.add('active');

    if (id === 'dashboard') loadDashboard();
    if (id === 'phaseA') loadPhaseA();
    if (id === 'phaseB') loadPhaseB();
    if (id === 'tasks') loadTasks();
}

// Colour-coded CLIFF / GAIN / NEUTRAL badge for the Phase A table.
function verdictBadge(v) {
    if (!v) return '-';
    var colour = v === 'CLIFF' ? '#ff6b6b' : (v === 'GAIN' ? '#51cf66' : '#888');
    return '<span style="color:' + colour + ';font-weight:600">' + v + '</span>';
}