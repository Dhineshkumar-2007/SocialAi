// ── Auth helpers ──────────────────────────────────────────
async function api(endpoint, options = {}) {
  const resp = await fetch(endpoint, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
  });
  const data = await resp.json();
  if (!resp.ok) throw new Error(data.error || 'Request failed');
  return data;
}

function toggleLogin() {
  const section = document.getElementById('loginSection');
  section.style.display = section.style.display === 'none' ? 'block' : 'none';
}

function showRegister() {
  document.getElementById('loginForm').style.display = 'none';
  document.getElementById('registerForm').style.display = 'block';
}

// ── Login / Register ──────────────────────────────────────
document.getElementById('loginForm')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const data = Object.fromEntries(fd);
  try {
    await api('/api/auth/login', { method: 'POST', body: JSON.stringify(data) });
    alert('Login successful');
    location.reload();
  } catch (err) {
    alert(err.message);
  }
});

document.getElementById('registerForm')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const data = Object.fromEntries(fd);
  try {
    await api('/api/auth/register', { method: 'POST', body: JSON.stringify(data) });
    alert('Registration successful. Please login.');
    location.reload();
  } catch (err) {
    alert(err.message);
  }
});

// ── Problem submission ─────────────────────────────────────
document.getElementById('problemForm')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const result = document.getElementById('analysisResult');
  result.innerHTML = '<div class="card"><p>Submitting...</p></div>';
  const fd = new FormData(e.target);

  try {
    // Submit problem
    const created = await fetch('/api/problems', { method: 'POST', body: fd })
      .then(r => r.json());
    if (created.error) {
      result.innerHTML = `<div class="card error">${created.error}</div>`;
      return;
    }

    result.innerHTML = `<div class="card"><h3>AI is analyzing...</h3><p>Problem #${created.problem_id} submitted. First run downloads model weights.</p></div>`;

    // Trigger analysis
    const data = await fetch(`/api/problems/${created.problem_id}/analyze`, { method: 'POST' })
      .then(r => r.json());
    if (data.error) {
      result.innerHTML = `<div class="card error"><h3>Analysis error</h3><pre>${JSON.stringify(data, null, 2)}</pre></div>`;
      return;
    }

    // Render results
    result.innerHTML = `
      <div class="card">
        <h2>AI Analysis — Problem #${created.problem_id}</h2>
        <p><b>Category:</b> ${data.classification.category}</p>
        <p><b>Confidence:</b> ${(data.classification.confidence * 100).toFixed(1)}%</p>
        <p><b>Priority:</b> <strong>${data.priority.level.toUpperCase()}</strong> (${data.priority.score}/100)</p>
        <p><b>Required skills:</b> ${data.skills.map(s => `<span class="pill">${s}</span>`).join(' ')}</p>
      </div>
      <div class="card">
        <h3>Evidence</h3>
        ${data.evidence.length
          ? data.evidence.map(x => `
            <div class="evidence-item">
              <p><b>${x.filename}</b></p>
              <p>Caption: <em>${x.caption}</em></p>
              <p>Status: <span class="badge badge-${x.evidence_status || 'unknown'}">${(x.evidence_status || 'unknown').toUpperCase()}</span></p>
              <p>Relevance: ${x.similarity ? (x.similarity * 100).toFixed(1) : 0}%</p>
            </div>`).join('')
          : '<p>No evidence uploaded.</p>'}
      </div>
      <div class="card">
        <h3>Duplicate Detection</h3>
        ${data.duplicates.length
          ? data.duplicates.map(x => `<p>Problem #${x.problem_id} — similarity ${(x.similarity * 100).toFixed(1)}%${x.distance_km ? ` — ${x.distance_km} km` : ''}</p>`).join('')
          : '<p>No strong duplicate found.</p>'}
      </div>
      <div class="card">
        <h3>University Matches</h3>
        ${data.matches.slice(0, 5).map((x, i) => `
          <div class="match-card">
            <h4>#${i + 1} ${x.university} — ${x.match_percent}%</h4>
            <p>${(x.explanation || []).join(' • ')}</p>
            <small>Semantic ${x.semantic_score} | Skills ${x.skill_score} | Labs ${x.lab_score}</small>
          </div>`).join('')}
      </div>
      <div class="card">
        <h3>Industry Matches</h3>
        ${data.industry_matches && data.industry_matches.length
          ? data.industry_matches.slice(0, 5).map((x, i) => `
            <div class="match-card">
              <h4>#${i + 1} ${x.industry} (${x.sector}) — ${x.match_percent}%</h4>
              <p>${(x.explanation || []).join(' • ')}</p>
            </div>`).join('')
          : '<p>No industry matches found.</p>'}
      </div>`;

  } catch (err) {
    result.innerHTML = `<div class="card error">Error: ${err.message}</div>`;
  }
});
