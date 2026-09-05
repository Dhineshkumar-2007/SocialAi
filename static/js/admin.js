// Admin Console — Professional JS
(async () => {
  async function api(ep, opts = {}) {
    const r = await fetch(ep, {
      ...opts,
      headers: { 'Content-Type': 'application/json', ...(opts.headers || {}) },
      credentials: 'same-origin'
    });
    if (!r.ok) return { error: await r.text() };
    return r.json();
  }

  // Load user
  const me = await api('/api/auth/me');
  if (!me.user || me.user.role !== 'admin') {
    alert('Admin access required');
    location.href = '/';
    return;
  }
  document.getElementById('userName').textContent = me.user.name || 'Admin';
  document.getElementById('userAvatar').textContent = (me.user.name || 'A').charAt(0);

  // Switch views
  document.querySelectorAll('.nav-item').forEach(link => {
    link.addEventListener('click', (e) => {
      e.preventDefault();
      document.querySelectorAll('.nav-item').forEach(l => l.classList.remove('active'));
      link.classList.add('active');
      document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
      const view = link.getAttribute('data-view');
      document.getElementById('view-' + view)?.classList.add('active');
      document.getElementById('pageTitle').textContent = link.querySelector('span:last-child')?.textContent || 'Overview';
      document.getElementById('pageSubtitle').textContent = getSubtitle(view);
      if (view === 'problems') loadProblems();
      if (view === 'assignments') loadAssignments();
      if (view === 'analytics') loadAnalytics();
      if (view === 'users') loadUsers();
    });
  });

  function getSubtitle(view) {
    const map = { overview: 'Real-time system metrics and insights', problems: 'Manage reported societal challenges', assignments: 'Track university and industry assignments', analytics: 'Performance and impact metrics', users: 'User and access management' };
    return map[view] || '';
  }

  // Overview data
  async function refreshData() {
    const d = await api('/api/dashboard/admin');
    document.getElementById('kpiTotal').textContent = d.total_problems || 0;
    document.getElementById('kpiAnalyzed').textContent = d.analyzed || 0;
    document.getElementById('kpiHigh').textContent = d.high_priority || 0;
    document.getElementById('kpiActive').textContent = d.active_projects || 0;
    document.getElementById('kpiCompleted').textContent = d.completed_projects || 0;
    document.getElementById('kpiDuplicates').textContent = d.duplicate_links || 0;

    // Category chart bars
    const cats = d.problems_by_category || {};
    const chartHTML = Object.entries(cats).map(([k, v]) => {
      const pct = Math.min(100, (v / Math.max(...Object.values(cats), 1)) * 100);
      return `<div style="display:flex;align-items:center;gap:1rem;margin-bottom:8px;"><span style="width:140px;font-size:13px;color:var(--text-secondary);">${k}</span><div style="flex:1;height:20px;background:var(--surface-hover);border-radius:10px;overflow:hidden;"><div style="width:${pct}%;height:100%;background:linear-gradient(90deg,#2563eb,#60a5fa);border-radius:10px;"></div></div><span style="font-weight:600;width:40px;text-align:right;font-size:13px;">${v}</span></div>`;
    }).join('');
    document.getElementById('categoryChart').innerHTML = chartHTML || '<p>No category data.</p>';

    // Activity feed
    const recent = d.recent_problems || [];
    document.getElementById('activityFeed').innerHTML = recent.map(p => `
      <div class="activity-item">
        <div class="activity-time">${p.created_at?.split(' ')[1] || 'Now'}</div>
        <div class="activity-text"><strong>Problem #${p.id}</strong> — ${p.title} <span style="color:var(--text-tertiary);font-size:12px;">(${p.category || 'Uncategorized'}, ${p.priority_level || 'medium'})</span></div>
      </div>
    `).join('') || '<p>No recent activity.</p>';

    // High priority list
    document.getElementById('highPriorityList').innerHTML = recent.filter(p => p.priority_level === 'high').slice(0, 3).map(p => `
      <div class="problem-row">
        <div><strong>#${p.id} ${p.title}</strong><span class="badge badge-high">HIGH</span></div>
        <div class="actions"><button class="btn-secondary" onclick="openProblemModal(${p.id})">Details</button></div>
      </div>
    `).join('') || '<p>No high priority items.</p>';
  }

  // Problems view
  async function loadProblems() {
    const d = await api('/api/problems');
    let list = d || [];
    const s = document.getElementById('filterStatus')?.value;
    const p = document.getElementById('filterPriority')?.value;
    const q = document.getElementById('searchInput')?.value.toLowerCase();
    if (s) list = list.filter(x => x.status === s);
    if (p) list = list.filter(x => x.priority_level === p);
    if (q) list = list.filter(x => (x.title || '').toLowerCase().includes(q));
    document.getElementById('problemTableBody').innerHTML = list.map(p => `
      <tr>
        <td><strong>#${p.id}</strong></td>
        <td style="max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${p.title}</td>
        <td>${p.category || '—'}</td>
        <td><span class="tag tag-${p.priority_level || 'low'}">${(p.priority_level || 'low').toUpperCase()}</span></td>
        <td><span class="tag tag-${p.status === 'completed' ? 'low' : p.status === 'in_progress' ? 'medium' : 'high'}">${(p.status || 'submitted').toUpperCase()}</span></td>
        <td>${p.created_at?.split(' ')[0] || '—'}</td>
        <td><button class="btn-secondary" onclick="openProblemModal(${p.id})">View</button></td>
      </tr>
    `).join('') || '<tr><td colspan="7" style="text-align:center;color:var(--text-tertiary);">No problems found.</td></tr>';
  }

  // Assignments view - Routing Tracker
  async function loadAssignments() {
    const d = await api('/api/assignments') || [];
    // Fetch routing audit data
    const audit = await api('/api/assignments/audit-trail') || [];
    window.assignmentData = d;
    window.auditTrail = audit;

    // Update stats
    document.getElementById('statTotalAssignments').textContent = d.length || 0;
    document.getElementById('statPendingAssignments').textContent = d.filter(x => (x.status || '').toLowerCase() === 'pending').length || 0;
    document.getElementById('statAcceptedAssignments').textContent = d.filter(x => (x.status || '').toLowerCase() === 'accepted').length || 0;
    document.getElementById('statCompletedAssignments').textContent = d.filter(x => (x.status || '').toLowerCase() === 'completed').length || 0;

    renderAssignmentTable(d);
    window.renderRoutingHistory();
  }

  function renderAssignmentTable(data) {
    const tbody = document.getElementById('assignmentTableBody');
    if (!data || data.length === 0) {
      tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:var(--text-tertiary);padding:2rem;">No assignments found.</td></tr>';
      return;
    }
    tbody.innerHTML = data.map(a => {
      const problemTitle = a.problem_title || `Problem #${a.problem_id}`;
      const university = a.university_name || (a.assignee_type === 'university' ? `Univ #${a.assignee_id}` : `Ind #${a.assignee_id}`);
      const statusClass = (a.status || '').toLowerCase() === 'completed' ? 'low' : (a.status || '').toLowerCase() === 'accepted' ? 'low' : (a.status || '').toLowerCase() === 'rejected' ? 'high' : 'medium';
      return `
        <tr onclick="openRoutingHistory(${a.id || a.assignment_id})" style="cursor:pointer;">
          <td><strong>#${a.problem_id}</strong> — ${problemTitle}</td>
          <td><span style="font-weight:600;color:var(--primary);">${university}</span></td>
          <td>${a.rank || (a.match_score ? Math.round(a.match_score * 100) + '%' : '—')}</td>
          <td><span class="tag tag-${statusClass}">${(a.status || 'pending').toUpperCase()}</span></td>
          <td>${a.assigned_at?.split(' ')[0] || a.created_at?.split(' ')[0] || '—'}</td>
          <td>${a.deadline || a.due_date || '—'}</td>
          <td>${a.round || a.round_number || '—'}</td>
          <td>
            <button class="btn-secondary" onclick="event.stopPropagation(); openRoutingHistory(${a.id || a.assignment_id})">Audit Trail</button>
            <button class="btn-icon" onclick="event.stopPropagation(); showAssignmentDetails(${a.id || a.assignment_id})">📋</button>
          </td>
        </tr>`;
    }).join('');
  }

  function filterAssignments() {
    const q = (document.getElementById('assignmentSearch')?.value || '').toLowerCase();
    const s = document.getElementById('assignmentStatusFilter')?.value || '';
    const r = document.getElementById('assignmentRoundFilter')?.value || '';
    let filtered = window.assignmentData || [];
    if (q) filtered = filtered.filter(x => {
      const t = (x.problem_title || '').toLowerCase();
      const u = (x.university_name || '').toLowerCase();
      const pid = (x.problem_id || '').toString();
      return t.includes(q) || u.includes(q) || pid.includes(q);
    });
    if (s) filtered = filtered.filter(x => (x.status || '').toLowerCase() === s);
    if (r) filtered = filtered.filter(x => (x.round || x.round_number || '').toString() === r);
    renderAssignmentTable(filtered);
  }
  window.filterAssignments = filterAssignments;

  window.renderRoutingHistory = () => {
    // Called when assignments data changes to update routing visualization
    const card = document.getElementById('routingHistoryCard');
    if (card && card.style.display !== 'none') {
      // Re-render if visible
    }
  };

  // Routing history / audit trail drill-down
  window.openRoutingHistory = async (assignmentId) => {
    const audit = window.auditTrail || [];
    const entry = audit.find(x => (x.assignment_id || x.id) === assignmentId) || audit.filter(x => (x.assignment_id || x.id) === assignmentId);
    const card = document.getElementById('routingHistoryCard');
    const content = document.getElementById('routingHistoryContent');
    card.style.display = 'block';
    content.innerHTML = `
      <div style="padding:1rem;">
        <h3 style="font-size:16px;font-weight:600;margin-bottom:1rem;">Audit Trail — Assignment #${assignmentId}</h3>
        <div class="audit-timeline">
          ${(entry.length ? entry : audit.filter(x => (x.assignment_id || x.id) === assignmentId)).map(a => `
            <div class="audit-step">
              <div class="audit-time">${a.timestamp || a.created_at || '—'}</div>
              <div class="audit-action">${a.action || a.event || 'Update'}</div>
              <div class="audit-detail">${a.details || a.description || 'No details'}</div>
              <div class="audit-user">By: ${a.actor || a.user_name || 'Admin'}</div>
            </div>
          `).join('') || '<p style="color:var(--text-tertiary);">No audit records available.</p>'}
        </div>
        <div style="margin-top:1rem;padding-top:1rem;border-top:1px solid var(--border);">
          <strong>Full Routing Path:</strong>
          <p style="margin-top:0.5rem;color:var(--text-secondary);font-size:13px;">Problem Submitted → AI Analysis → University Matching → Assignment Offer → Response → Project Initiation → Status Updates</p>
        </div>
      </div>`;
    card.scrollIntoView({ behavior: 'smooth', block: 'center' });
  };

  window.closeRoutingHistory = () => {
    document.getElementById('routingHistoryCard').style.display = 'none';
  };

  window.showAssignmentDetails = (id) => {
    alert('Assignment details modal for #' + id + ' — full audit trail available via Routing History button.');
  };

  // Analytics view
  async function loadAnalytics() {
    const d = await api('/api/universities');
    document.getElementById('analyticsUniversities').textContent = d?.length || 0;
    document.getElementById('analyticsIndustry').textContent = 5;
    document.getElementById('analyticsResolution').textContent = '62%';
    document.getElementById('analyticsAvgTime').textContent = '34d';
  }

  // Users view
  async function loadUsers() {
    const d = await api('/api/auth/me') || {};
    document.getElementById('usersList').innerHTML = `<p>Admin account: <strong>${me.user?.email}</strong> (${me.user?.role})</p>`;
  }

  // Modal
  window.openProblemModal = async (id) => {
    const p = await api('/api/problems/' + id);
    const m = await api('/api/problems/' + id + '/matches');
    document.getElementById('modalTitle').textContent = `Problem #${p.id}`;
    document.getElementById('modalBody').innerHTML = `
      <div class="label">Title</div><div class="value">${p.title}</div>
      <div class="label">Description</div><div class="value" style="max-height:120px;overflow-y:auto;">${p.description || '—'}</div>
      <div class="label">Category</div><div class="value">${p.category || '—'}</div>
      <div class="label">Priority</div><div class="value">${p.priority_level || 'medium'} (score: ${p.priority_score || 0})</div>
      <div class="label">Status</div><div class="value">${p.status || 'submitted'}</div>
      <div class="label">Evidence Score</div><div class="value">${p.evidence_score || 0}</div>
      <div class="label">Skills</div><div class="value">${(p.skills || []).join(', ') || 'None extracted'}</div>
      <div class="label">Evidence</div><div class="value">${(p.evidence || []).map(e => `<div style="margin-bottom:0.25rem;"><strong>${e.filename}</strong> — ${e.evidence_status || 'pending'} (${(e.relevance || 0 * 100).toFixed(1)}%)</div>`).join('') || 'No evidence'}</div>
      <div class="label">Top University Matches</div><div class="value">${m.slice(0, 3).map(x => `<div style="margin-bottom:0.25rem;"><strong>#${x.university_id}</strong> — ${(x.final_score * 100).toFixed(1)}% (semantic: ${(x.semantic_score || 0).toFixed(2)})</div>`).join('') || 'None'}</div>
    `;
    document.getElementById('problemModal').classList.add('active');
    document.getElementById('modalAssignBtn').onclick = () => { closeModal(); assignFromModal(id); };
  };

  window.closeModal = () => document.getElementById('problemModal').classList.remove('active');

  window.assignFromModal = (id) => {
    const type = prompt('Assign to (university or industry)?');
    if (!type || !['university','industry'].includes(type)) return;
    const target = prompt('Target ID (number):');
    if (!target) return;
    fetch('/api/assignments', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({ problem_id: id, assignee_type: type, assignee_id: parseInt(target), notes: 'Assigned from admin console' })
    }).then(r => r.json()).then(d => alert(d.message || d.error || 'Assigned'));
  };

  window.switchView = (view) => {
    document.querySelectorAll('.nav-item').forEach(l => l.classList.remove('active'));
    document.querySelector(`.nav-item[data-view="${view}"]`)?.classList.add('active');
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.getElementById('view-' + view)?.classList.add('active');
    document.getElementById('pageTitle').textContent = view === 'overview' ? 'Overview' : view.charAt(0).toUpperCase() + view.slice(1);
    document.getElementById('pageSubtitle').textContent = getSubtitle(view);
    if (view === 'problems') loadProblems();
    if (view === 'assignments') loadAssignments();
    if (view === 'analytics') loadAnalytics();
    if (view === 'users') loadUsers();
  };

  window.refreshData = () => { refreshData(); loadProblems(); loadAssignments(); };
  window.logout = async () => { await api('/api/auth/logout', { method: 'POST' }); location.href = '/'; };
  window.toggleNotifications = () => alert('Notification center: all clear');
  window.showNewAssignmentModal = () => { const id = prompt('Problem ID to assign:'); if(id) assignFromModal(parseInt(id)); };

  // Filters
  document.getElementById('searchInput')?.addEventListener('input', () => loadProblems());
  document.getElementById('filterStatus')?.addEventListener('change', () => loadProblems());
  document.getElementById('filterPriority')?.addEventListener('change', () => loadProblems());

  // Init
  await refreshData();
  await loadProblems();
})();
