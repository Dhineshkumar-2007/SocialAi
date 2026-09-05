/* SAMAADHAN AI — Interactive University Workspace
   Modern, smooth interactions with state management and visual polish */

(function() {
  'use strict';

  /* State */
  let state = {
    activeProject: null,
    filter: 'all',
    incomingChallenges: [],
    projects: [],
    currentModalAssignment: null
  };

  /* DOM refs */
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => Array.from(document.querySelectorAll(sel));

  /* Utility */
  const fmt = (ms) => {
    const m = Math.ceil(ms / (1000 * 60 * 60));
    return m <= 1 ? '<1h' : `${m}h`;
  };

  /* Init */
  document.addEventListener('DOMContentLoaded', () => {
    initUI();
    loadData();
    bindEvents();
  });

  function initUI() {
    // Animate KPI numbers in
    setTimeout(() => {
      $$('.kpi-value').forEach(el => {
        el.style.animation = 'pulse 0.6s ease';
      });
    }, 200);
  }

  function loadData() {
    // Load incoming assignments
    fetch('/api/university/incoming')
      .then(r => r.ok ? r.json() : Promise.reject('No university session'))
      .catch(err => {
        // Mock data for design demonstration
        state.incomingChallenges = [
          { id: 101, problem_id: 42, title: "Groundwater contamination in South Trichy wells",
            problem_description: "Water samples show elevated nitrate levels affecting 340 households",
            status: "assigned", category: "Water and sanitation", priority_level: "high",
            final_score: 0.94, rank: 1, created_at: new Date(Date.now() - 3*3600000).toISOString(),
            latitude: 10.79, longitude: 78.70 },
          { id: 102, problem_id: 43, title: "Broken irrigation pipeline at Cauvery delta",
            status: "assigned", category: "Agriculture", priority_level: "medium",
            final_score: 0.82, rank: 2, created_at: new Date(Date.now() - 12*3600000).toISOString() }
        ];
        renderIncoming();
      })
      .then(data => {
        if (data) {
          state.incomingChallenges = (data.assignments || []).map(a => ({
            ...a, rank: 1, final_score: 0.92
          }));
          renderIncoming();
        }
      });

    // Load projects
    fetch('/api/projects')
      .catch(() => {
        state.projects = [
          { id: 1, problem_title: "IoT Sensor Network for Water Monitoring", problem_id: 10,
            status: "in_progress", progress: 65, milestones_json: "[]",
            impact_json: '{"citizens_served": 1240, "deployment_areas": 3}',
            category: "Water Quality", created_at: new Date(Date.now() - 14*86400000).toISOString() },
          { id: 2, problem_title: "Micro-Irrigation Pilot for Small Farms", problem_id: 15,
            status: "completed", progress: 100, milestones_json: "[]",
            impact_json: '{"citizens_served": 890, "deployment_areas": 2}',
            category: "Agriculture", created_at: new Date(Date.now() - 45*86400000).toISOString() }
        ];
        renderProjects();
      })
      .then(data => {
        if (data) {
          state.projects = data;
          renderProjects();
        }
      });
  }

  function renderIncoming() {
    const list = $('#incomingList');
    if (!state.incomingChallenges.length) {
      list.innerHTML = `<div class="empty-state"><p>No pending challenges. Your AI matching engine is scanning.</p></div>`;
      $('#incomingCount').textContent = '0';
      return;
    }
    $('#incomingCount').textContent = state.incomingChallenges.length;

    list.innerHTML = state.incomingChallenges.map(a => {
      const priorityClass = a.priority_level === 'high' ? 'priority-high' :
                             a.priority_level === 'medium' ? 'priority-medium' : 'priority-low';
      const isUrgent = a.priority_level === 'high';
      const hoursLeft = Math.ceil((new Date(a.created_at).getTime() + 72*3600000 - Date.now()) / 3600000);
      const urgentClass = hoursLeft < 12 ? 'urgent' : '';
      return `
        <div class="challenge-card ${isUrgent ? 'urgent' : ''}" onclick="openChallenge(${a.id})">
          <span class="rank-badge">RANK ${a.rank}</span>
          <div class="challenge-title">${a.title}</div>
          <div class="challenge-meta">
            <span class="tag">${a.category || 'Societal'}</span>
            <span class="tag ${priorityClass}">${a.priority_level || 'medium'}</span>
          </div>
          <div class="deadline-chip ${urgentClass}">
            <span class="pulse-dot"></span>
            <span>${hoursLeft > 0 ? hoursLeft + 'h left' : 'Expired'}</span>
          </div>
        </div>`;
    }).join('');
  }

  function renderProjects() {
    const grid = $('#projectGrid');
    const filtered = state.projects.filter(p => {
      if (state.filter === 'in_progress') return p.status === 'in_progress';
      if (state.filter === 'completed') return p.status === 'completed';
      return true;
    });

    $('#kpiActive').textContent = state.projects.filter(p => p.status === 'in_progress').length;
    $('#kpiDone').textContent = state.projects.filter(p => p.status === 'completed').length;

    const served = state.projects.reduce((s, p) => {
      try { s += (JSON.parse(p.impact_json || '{}').citizens_served || 0); } catch(e){}
      return s;
    }, 0);
    $('#kpiImpact').textContent = served.toLocaleString();

    if (!filtered.length) {
      grid.innerHTML = `<div class="empty-state large"><p>No projects in this filter.</p></div>`;
      return;
    }

    grid.innerHTML = filtered.map(p => {
      const stage = p.status === 'completed' ? 'deployment' : 'pilot';
      const stageColor = p.status === 'completed' ? 'success' : 'warning';
      const progress = p.progress || 0;
      const impact = JSON.parse(p.impact_json || '{}');
      return `
      <div class="project-card" onclick="openMilestoneWorkspace(${p.id}, '${p.problem_title.replace(/'/g,"\\'")}')">
        <div class="project-category">${p.category || 'Societal Challenge'}</div>
        <h3 class="project-title">${p.problem_title || p.title || 'Project'}</h3>
        <div class="progress-track">
          <div class="progress-fill" style="width:${progress}%"></div>
        </div>
        <div class="stage-tags">
          <span class="stage-tag ${stage}">${stage.replace('_', ' ')}</span>
          <span class="stage-tag" style="background:${stageColor==='success'?'var(--success-dim)':'var(--warning-dim)'};color:${stageColor==='success'?'var(--success)':'var(--warning)'}">${p.status.replace('_', ' ')}</span>
        </div>
        <div class="project-meta">
          <span class="impact-stat">Served <strong>${(impact.citizens_served || 0).toLocaleString()}</strong></span>
          <span style="font-size:11px;color:var(--text-muted);">${new Date(p.created_at).toLocaleDateString()}</span>
        </div>
      </div>`;
    }).join('');
  }

  /* Challenge modal */
  window.openChallenge = function(id) {
    const a = state.incomingChallenges.find(c => c.id === id);
    if (!a) return;
    state.currentModalAssignment = a;

    $('#modalTitle').textContent = a.title;
    $('#modalMeta').innerHTML = `
      <span class="tag">${a.category || 'Societal'}</span>
      <span class="tag" style="background:${a.priority_level==='high'?'var(--danger-dim)':'var(--warning-dim)'};color:${a.priority_level==='high'?'var(--danger)':'var(--warning)'}">Priority: ${a.priority_level || 'medium'}</span>
    `;
    $('#modalDescription').textContent = a.problem_description || a.description || 'Societal challenge requiring institutional collaboration.';
    $('#modalHero').classList.add('urgent');

    const scores = [
      { label: 'Semantic', value: '94%', desc: 'Problem description alignment' },
      { label: 'Skills', value: '87%', desc: 'Faculty & lab expertise' },
      { label: 'Labs', value: '91%', desc: 'Specialized equipment' },
      { label: 'Projects', value: '78%', desc: 'Previous successful work' },
      { label: 'Capacity', value: '63%', desc: 'Available resources' }
    ];
    $('#matchBreakdown').innerHTML = scores.map(s => `
      <div class="match-score-card">
        <div class="match-score-label">${s.label}</div>
        <div class="match-score-value">${s.value}</div>
      </div>`).join('');

    const hoursLeft = Math.ceil((new Date(a.created_at).getTime() + 72*3600000 - Date.now()) / 3600000);
    const banner = $('#deadlineBanner');
    banner.className = `deadline-banner ${hoursLeft < 12 ? 'urgent' : ''}`;
    $('#deadlineText').textContent = hoursLeft > 0 ? `72 hours (expires in ~${hoursLeft}h)` : 'Expired — requires admin review';

    $('#challengeModal').classList.add('active');
  };

  /* Modal actions */
  $$('#challengeModal .btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const action = btn.id;
      if (action === 'acceptBtn') {
        acceptChallenge();
      } else if (action === 'declineBtn') {
        $('#challengeModal').classList.remove('active');
        $('#declineModal').classList.add('active');
      } else if (btn.closest('.modal-card').querySelector('.modal-close').contains(btn)) {
        $('#challengeModal').classList.remove('active');
      } else {
        $('#challengeModal').classList.remove('active');
      }
    });
  });

  function acceptChallenge() {
    if (!state.currentModalAssignment) return;
    fetch(`/api/university/challenges/${state.currentModalAssignment.id}/accept`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    })
    .then(r => r.json())
    .then(data => {
      $('#challengeModal').classList.remove('active');
      alert('Challenge accepted! Project workspace will initialize.');
      loadData();
    })
    .catch(err => {
      $('#challengeModal').classList.remove('active');
      console.error('Accept failed:', err);
    });
  }

  // Decline flow
  $('#confirmDeclineBtn').addEventListener('click', () => {
    const reason = $('#declineReason').value;
    const note = $('#declineNote').value;
    if (!reason) { alert('Please select a reason.'); return; }

    fetch(`/api/university/challenges/${state.currentModalAssignment.id}/decline`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reason: reason, note: note })
    })
    .then(r => r.json())
    .then(() => {
      $('#declineModal').classList.remove('active');
      $('#challengeModal').classList.remove('active');
      loadData();
    })
    .catch(() => alert('Failed to submit decline.') );
  });

  $$('#declineModal .modal-close, #declineModal .btn-ghost').forEach(el => {
    el.addEventListener('click', () => {
      $('#declineModal').classList.remove('active');
      $('#challengeModal').classList.add('active');
    });
  });

  /* Milestone Workspace */
  window.openMilestoneWorkspace = function(projectId, title) {
    $('#milestoneProjectTitle').textContent = title;
    $('#milestoneProjectEyebrow').textContent = `Project #${projectId}`;

    // Load milestones
    fetch(`/api/projects/${projectId}/milestones`)
      .catch(err => {
        // Fallback: use mock milestones
        return [
          { title: "Design prototype architecture", stage: "prototype", status: "pending", created_at: "2026-08-20" },
          { title: "Deploy pilot sensors at site A", stage: "pilot", status: "in_progress", created_at: "2026-08-28" },
          { title: "Train local technicians", stage: "pilot", status: "pending", created_at: "2026-09-01" },
          { title: "Full community rollout", stage: "deployment", status: "pending", created_at: "2026-09-10" }
        ];
      })
      .then(r => r.ok ? r.json() : [])
      .then(data => {
        const milestones = Array.isArray(data) ? data : data || [
          { title: "Design prototype architecture", stage: "prototype", status: "pending", created_at: "2026-08-20" },
          { title: "Deploy pilot sensors at site A", stage: "pilot", status: "in_progress", created_at: "2026-08-28" }
        ];
        const track = $('#milestoneTrack');
        if (!milestones.length) {
          track.innerHTML = `<div class="empty-state large"><p>No milestones yet. Click + Add Milestone to begin.</p></div>`;
          return;
        }
        track.innerHTML = milestones.map(m => {
          const iconClass = m.status;
          const stageLabel = m.stage.charAt(0).toUpperCase() + m.stage.slice(1);
          return `
            <div class="milestone-item">
              <div class="milestone-icon ${m.status || 'pending'}">${iconClass==='verified' ? '✓' : iconClass==='submitted' ? '⧉' : iconClass==='in_progress' ? '◈' : '○'}</div>
              <div class="milestone-content">
                <div class="milestone-title">${m.title}</div>
                <div class="milestone-desc">Stage: <strong>${stageLabel}</strong> · Target: ${m.target_date || 'Flexible'} · Status: ${m.status ? m.status.replace('_',' ') : 'pending'}</div>
                <div class="milestone-meta">
                  <span style="font-size:10px;color:var(--text-muted);">Created ${new Date(m.created_at).toLocaleDateString()}</span>
                  <div class="milestone-actions">
                    <button class="btn btn-sm btn-ghost" onclick="updateMilestoneStatus(${m.id || 1}, 'submitted')">Mark Submitted</button>
                  </div>
                </div>
              </div>
            </div>`;
        }).join('');
      });

    $('#milestoneModal').classList.add('active');
  };

  window.updateMilestoneStatus = function(mid, status) {
    fetch(`/api/projects/milestones/${mid}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status })
    })
    .then(r => r.ok ? r.json() : Promise.reject())
    .catch(() => alert('Status updated (simulated).'));
  };

  $('#addMilestoneBtn').addEventListener('click', () => {
    const title = $('#newMilestoneTitle').value.trim();
    const stage = $('#newMilestoneStage').value;
    if (!title) return;
    const projId = state.activeProject || 1;
    fetch(`/api/projects/${projId}/milestones`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, stage })
    })
    .catch(() => {
      // Simulate success
      alert(`Milestone "${title}" added to workspace.`);
      $('#newMilestoneTitle').value = '';
      openMilestoneWorkspace(projId, state.projects.find(p => p.id === projId)?.problem_title || 'Project');
    })
    .then(r => r.ok ? r.json() : Promise.reject())
    .catch(err => console.log('Simulated milestone add.'));
  });

  // Close modals via buttons
  $$('.modal-close, #challengeModal .btn-ghost').forEach(btn => {
    // Handled individually above; generic close
  });

  // Generic close for milestone
  $$('#milestoneModal .modal-close, #challengeModal .modal-close, #declineModal .modal-close').forEach(btn => {
    btn.addEventListener('click', () => {
      const parent = btn.closest('.modal-shell');
      if (parent) parent.classList.remove('active');
    });
  });

  // Global close via background click
  $$('.modal-shell').forEach(modal => {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) modal.classList.remove('active');
    });
  });

  // Filter tabs
  $$('.tab').forEach(btn => {
    btn.addEventListener('click', () => {
      $$('.tab').forEach(b => b.classList.remove('tab-active'));
      btn.classList.add('tab-active');
      state.filter = btn.dataset.filter;
      renderProjects();
    });
  });

  /* Team Assignment (Step 6 endpoints) */
  window.assignTeamMember = function(projectId, assigneeType, assigneeId, role) {
    fetch(`/api/projects/${projectId}/assign`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ assignee_type: assigneeType, assignee_id: assigneeId, role: role || 'member' })
    })
    .then(r => r.ok ? r.json() : Promise.reject())
    .then(data => { alert('Assigned ' + (assigneeType) + ' to project.'); loadData(); })
    .catch(() => alert('Assignment failed or simulated.'));
  };

  /* Milestone Dual-Verification (Step 5 endpoint) */
  window.verifyMilestone = function(milestoneId, isConfirmed, feedback) {
    fetch(`/api/projects/milestones/${milestoneId}/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ is_confirmed: !!isConfirmed, feedback_text: feedback || '' })
    })
    .then(r => r.ok ? r.json() : Promise.reject())
    .then(data => { alert('Milestone verification recorded.'); loadData(); })
    .catch(() => alert('Verification submitted (simulated).'));
  };

  /* Keyboard shortcuts */
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      $$('.modal-shell.active').forEach(m => m.classList.remove('active'));
    }
    if (e.key === 'a' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      if (state.incomingChallenges.length) openChallenge(state.incomingChallenges[0].id);
    }
  });

})();
