/**
 * University Dashboard — Incoming Challenges Module
 * Manages AI-matched challenge cards, accept/decline workflows, and deadline countdowns.
 */

(function() {
  'use strict';

  // Track countdown intervals for cleanup
  let countdownIntervals = [];

  // ─────────────────────────────────────────────────────────────
  // API Helper
  // ─────────────────────────────────────────────────────────────
  async function api(ep, opts = {}) {
    const r = await fetch(ep, {
      ...opts,
      headers: {
        'Content-Type': 'application/json',
        ...(opts.headers || {})
      },
      credentials: 'same-origin'
    });
    return r.json();
  }

  // ─────────────────────────────────────────────────────────────
  // Load Incoming Challenges
  // ─────────────────────────────────────────────────────────────
  async function loadIncomingChallenges() {
    const container = document.getElementById('incomingChallenges');
    if (!container) return;

    container.innerHTML = '<div class="challenge-skeleton" style="padding:1rem;border:1px dashed var(--border);border-radius:12px;color:var(--text-tertiary);font-size:14px;">Loading challenges...</div>';

    try {
      const data = await api('/api/university/incoming');

      if (!data || data.length === 0) {
        container.innerHTML = `
          <div style="text-align:center;padding:3rem 1rem;color:var(--text-tertiary);">
            <div style="font-size:48px;margin-bottom:1rem;">&#x1F4ED;</div>
            <p style="font-size:15px;font-weight:500;color:var(--text-secondary);">No pending challenges</p>
            <p style="font-size:13px;margin-top:0.5rem;">New challenges will appear here when matched with your university.</p>
          </div>
        `;
        return;
      }

      container.innerHTML = data.map(challenge => renderChallengeCard(challenge)).join('');
      startCountdowns();
    } catch (err) {
      console.error('Failed to load incoming challenges:', err);
      container.innerHTML = `
        <div style="padding:1rem;border:1px solid var(--error);border-radius:12px;background:rgba(239,68,68,0.05);color:var(--error);font-size:14px;">
          Unable to load challenges. <button onclick="loadIncomingChallenges()" style="background:none;border:none;color:var(--primary);cursor:pointer;text-decoration:underline;">Try again</button>
        </div>
      `;
    }
  }

  // ─────────────────────────────────────────────────────────────
  // Render Challenge Card
  // ─────────────────────────────────────────────────────────────
  function renderChallengeCard(challenge) {
    const deadlineClass = getDeadlineClass(challenge.deadline);
    const deadlineLabel = getDeadlineLabel(challenge.deadline);

    // AI match pills
    const pills = (challenge.ai_match || {}).skills || [];
    const pillHtml = pills.length > 0
      ? pills.slice(0, 4).map(skill => `<span class="match-pill">${escapeHtml(skill)}</span>`).join('')
      : '';

    // Match score badge
    const matchScore = (challenge.ai_match || {}).score || 0;
    const scoreClass = matchScore >= 80 ? 'score-high' : matchScore >= 60 ? 'score-medium' : 'score-low';

    // Priority badge
    const priority = challenge.priority || 'medium';
    const priorityClass = `tag-${priority}`;

    return `
      <div class="challenge-card" data-id="${challenge.id}" style="border:1px solid var(--border);border-radius:12px;padding:1.25rem;margin-bottom:1rem;background:var(--surface-elevated);transition:box-shadow 0.2s,transform 0.2s;">
        <!-- Card Header -->
        <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:1rem;margin-bottom:1rem;">
          <div style="flex:1;min-width:0;">
            <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.25rem;flex-wrap:wrap;">
              <span class="tag ${priorityClass}" style="font-size:11px;font-weight:600;padding:2px 6px;border-radius:4px;">${challenge.priority?.toUpperCase() || 'MEDIUM'}</span>
              <span class="${scoreClass}" style="font-size:11px;font-weight:600;padding:2px 8px;border-radius:10px;">${matchScore}% Match</span>
              <span class="category-pill" style="font-size:11px;font-weight:500;padding:2px 8px;border-radius:10px;background:rgba(99,102,241,0.1);color:#6366f1;">${escapeHtml(challenge.category || 'General')}</span>
            </div>
            <h3 style="font-size:16px;font-weight:600;color:var(--text-primary);margin:0.25rem 0;line-height:1.3;">${escapeHtml(challenge.title || 'Untitled Challenge')}</h3>
            <p style="font-size:13px;color:var(--text-secondary);margin:0;line-height:1.5;">${escapeHtml(truncate(challenge.description || 'No description provided.', 180))}</p>
          </div>
        </div>

        <!-- AI Match Explanation Pills -->
        ${pillHtml ? `
        <div style="margin-bottom:1rem;">
          <div style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;color:var(--text-tertiary);margin-bottom:0.5rem;">AI Match Explanation</div>
          <div style="display:flex;flex-wrap:wrap;gap:0.375rem;">
            ${pillHtml}
            ${pills.length > 4 ? `<span class="match-pill more">+${pills.length - 4} more</span>` : ''}
          </div>
          ${(challenge.ai_match || {}).reasoning ? `
          <div style="margin-top:0.75rem;padding:0.75rem;background:var(--surface);border-radius:8px;border:1px solid var(--border);font-size:13px;color:var(--text-secondary);line-height:1.5;">
            <span style="font-weight:600;color:var(--primary);">Why matched:</span> ${escapeHtml(challenge.ai_match.reasoning)}
          </div>
          ` : ''}
        </div>
        ` : ''}

        <!-- Deadline Warning -->
        ${challenge.deadline ? `
        <div class="deadline-warning ${deadlineClass}" style="display:flex;align-items:center;gap:0.5rem;padding:0.625rem 0.875rem;border-radius:8px;margin-bottom:1rem;font-size:13px;font-weight:500;">
          <span style="font-size:14px;">${deadlineClass === 'deadline-critical' ? '&#x23F0;' : '&#x1F551;'}</span>
          <span>Deadline: <strong id="countdown-${challenge.id}">${deadlineLabel}</strong></span>
        </div>
        ` : ''}

        <!-- Actions -->
        <div style="display:flex;gap:0.5rem;justify-content:flex-end;">
          <button class="btn-decline" onclick="showDeclineModal(${challenge.id})" style="padding:0.5rem 1rem;border:1px solid var(--border);background:var(--surface);border-radius:6px;font-size:13px;font-weight:600;color:var(--text-secondary);cursor:pointer;transition:all 0.2s;">Decline</button>
          <button class="btn-accept" onclick="acceptChallenge(${challenge.id})" style="padding:0.5rem 1rem;background:linear-gradient(135deg,#10b981,#059669);color:#fff;border:none;border-radius:6px;font-size:13px;font-weight:600;cursor:pointer;box-shadow:0 2px 8px rgba(16,185,129,0.25);transition:all 0.2s;">Accept Challenge</button>
        </div>
      </div>
    `;
  }

  // ─────────────────────────────────────────────────────────────
  // Accept Challenge
  // ─────────────────────────────────────────────────────────────
  async function acceptChallenge(assignmentId) {
    const btn = document.querySelector(`[data-id="${assignmentId}"] .btn-accept`);
    if (btn) {
      btn.disabled = true;
      btn.textContent = 'Accepting...';
    }

    try {
      const result = await api(`/api/university/challenges/${assignmentId}/accept`, {
        method: 'POST',
        body: JSON.stringify({})
      });

      if (result.error) {
        showToast('Failed to accept: ' + result.error, 'error');
      } else {
        showToast('Challenge accepted successfully!', 'success');
        // Animate card removal
        const card = document.querySelector(`[data-id="${assignmentId}"]`);
        if (card) {
          card.style.transition = 'opacity 0.3s, transform 0.3s';
          card.style.opacity = '0';
          card.style.transform = 'translateX(20px)';
          setTimeout(() => card.remove(), 300);
        }
      }
    } catch (err) {
      console.error('Accept challenge error:', err);
      showToast('Network error. Please try again.', 'error');
    }

    if (btn) {
      btn.disabled = false;
      btn.textContent = 'Accept Challenge';
    }
  }

  // ─────────────────────────────────────────────────────────────
  // Decline Modal
  // ─────────────────────────────────────────────────────────────
  function showDeclineModal(assignmentId) {
    const modal = document.getElementById('declineModal');
    const input = document.getElementById('declineAssignmentId');
    const error = document.getElementById('declineError');
    const textarea = document.getElementById('declineReason');

    if (input) input.value = assignmentId;
    if (error) error.style.display = 'none';
    if (textarea) textarea.value = '';

    if (modal) {
      modal.classList.add('active');
      // Focus textarea for accessibility
      setTimeout(() => textarea?.focus(), 100);
    }
  }

  function closeDeclineModal() {
    const modal = document.getElementById('declineModal');
    if (modal) modal.classList.remove('active');
  }

  // ─────────────────────────────────────────────────────────────
  // Submit Decline
  // ─────────────────────────────────────────────────────────────
  async function submitDecline(event) {
    if (event) event.preventDefault();

    const assignmentId = document.getElementById('declineAssignmentId')?.value;
    const reason = document.getElementById('declineReason')?.value.trim();
    const error = document.getElementById('declineError');

    // Validate
    if (!reason || reason.length < 10) {
      if (error) {
        error.style.display = 'block';
        error.textContent = 'Please provide a reason (minimum 10 characters).';
      }
      return;
    }

    const btn = document.querySelector('#declineModal .btn-primary');
    if (btn) {
      btn.disabled = true;
      btn.textContent = 'Submitting...';
    }

    try {
      const result = await api(`/api/university/challenges/${assignmentId}/decline`, {
        method: 'POST',
        body: JSON.stringify({ reason })
      });

      if (result.error) {
        showToast('Failed to decline: ' + result.error, 'error');
      } else {
        closeDeclineModal();
        showToast('Challenge declined. Thank you for your feedback.', 'success');
        // Animate card removal
        const card = document.querySelector(`[data-id="${assignmentId}"]`);
        if (card) {
          card.style.transition = 'opacity 0.3s, transform 0.3s';
          card.style.opacity = '0';
          card.style.transform = 'translateX(-20px)';
          setTimeout(() => card.remove(), 300);
        }
      }
    } catch (err) {
      console.error('Decline challenge error:', err);
      showToast('Network error. Please try again.', 'error');
    }

    if (btn) {
      btn.disabled = false;
      btn.textContent = 'Confirm Decline';
    }
  }

  // ─────────────────────────────────────────────────────────────
  // Real-time Countdown
  // ─────────────────────────────────────────────────────────────
  function startCountdowns() {
    // Clear existing intervals
    countdownIntervals.forEach(clearInterval);
    countdownIntervals = [];

    document.querySelectorAll('[id^="countdown-"]').forEach(el => {
      const match = el.id.match(/^countdown-(\d+)$/);
      if (!match) return;

      const assignmentId = match[1];
      const card = document.querySelector(`[data-id="${assignmentId}"]`);
      const deadlineStr = card?.dataset.deadline;

      if (!deadlineStr) return;

      const updateCountdown = () => {
        const target = new Date(deadlineStr).getTime();
        const now = Date.now();
        const diff = target - now;

        if (diff <= 0) {
          el.textContent = 'Expired';
          el.parentElement.parentElement.classList.add('deadline-expired');
          return;
        }

        const days = Math.floor(diff / (1000 * 60 * 60 * 24));
        const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
        const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

        if (days > 0) {
          el.textContent = `${days}d ${hours}h remaining`;
        } else if (hours > 0) {
          el.textContent = `${hours}h ${minutes}m remaining`;
        } else {
          el.textContent = `${minutes}m remaining`;
        }
      };

      updateCountdown();
      const interval = setInterval(updateCountdown, 60000); // Update every minute
      countdownIntervals.push(interval);
    });
  }

  // ─────────────────────────────────────────────────────────────
  // Deadline Helpers
  // ─────────────────────────────────────────────────────────────
  function getDeadlineClass(deadline) {
    if (!deadline) return '';
    const diff = new Date(deadline).getTime() - Date.now();
    const hours = diff / (1000 * 60 * 60);
    if (hours < 0) return 'deadline-expired';
    if (hours < 24) return 'deadline-critical';
    if (hours < 72) return 'deadline-warning';
    return 'deadline-normal';
  }

  function getDeadlineLabel(deadline) {
    if (!deadline) return '';
    const diff = new Date(deadline).getTime() - Date.now();
    const hours = diff / (1000 * 60 * 60);
    if (hours < 0) return 'Expired';
    if (hours < 24) return `${Math.floor(hours)}h remaining`;
    if (hours < 72) return `${Math.floor(hours / 24)}d remaining`;
    return `${Math.floor(hours / 24)} days remaining`;
  }

  // ─────────────────────────────────────────────────────────────
  // Toast Notifications
  // ─────────────────────────────────────────────────────────────
  function showToast(message, type = 'info') {
    // Remove existing toast
    const existing = document.querySelector('.toast-notification');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = `toast-notification toast-${type}`;
    toast.style.cssText = `
      position: fixed;
      bottom: 2rem;
      right: 2rem;
      padding: 0.875rem 1.25rem;
      border-radius: 8px;
      font-size: 14px;
      font-weight: 500;
      z-index: 1000;
      box-shadow: var(--shadow-lg);
      animation: toastSlideIn 0.3s ease;
      max-width: 320px;
    `;

    const colors = {
      success: { bg: '#10b981', color: '#fff' },
      error: { bg: '#ef4444', color: '#fff' },
      info: { bg: '#2563eb', color: '#fff' }
    };
    const c = colors[type] || colors.info;
    toast.style.background = c.bg;
    toast.style.color = c.color;
    toast.textContent = message;

    // Add animation keyframes if not present
    if (!document.querySelector('#toast-styles')) {
      const style = document.createElement('style');
      style.id = 'toast-styles';
      style.textContent = `
        @keyframes toastSlideIn {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .btn-accept:hover { background: linear-gradient(135deg,#059669,#047857) !important; transform: translateY(-1px); }
        .btn-decline:hover { background: var(--surface-hover) !important; color: var(--text-primary) !important; }
      `;
      document.head.appendChild(style);
    }

    document.body.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transition = 'opacity 0.3s';
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  }

  // ─────────────────────────────────────────────────────────────
  // Utility Functions
  // ─────────────────────────────────────────────────────────────
  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  function truncate(text, maxLength) {
    if (!text || text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  }

  // ─────────────────────────────────────────────────────────────
  // Logout
  // ─────────────────────────────────────────────────────────────
  async function logout() {
    await api('/api/auth/logout', { method: 'POST' });
    location.href = '/';
  }

  // ─────────────────────────────────────────────────────────────
  // Initialization
  // ─────────────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', function() {
    // Close modal on backdrop click
    const modal = document.getElementById('declineModal');
    if (modal) {
      modal.addEventListener('click', function(e) {
        if (e.target === modal) closeDeclineModal();
      });
    }

    // Close modal on Escape key
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape') closeDeclineModal();
    });

    // Load incoming challenges
    loadIncomingChallenges();
  });

  // ─────────────────────────────────────────────────────────────
  // Global Expose for onclick handlers
  // ─────────────────────────────────────────────────────────────
  window.loadIncomingChallenges = loadIncomingChallenges;
  window.acceptChallenge = acceptChallenge;
  window.showDeclineModal = showDeclineModal;
  window.closeDeclineModal = closeDeclineModal;
  window.submitDecline = submitDecline;
  window.logout = logout;

})();
