/**
 * ClubCredits - Frontend Application
 * Reactive single-page client with Server-Sent Events, transparent logic evaluation,
 * and protected administrator controls.
 */

(() => {
  'use strict';

  // Application State
  const state = {
    token: localStorage.getItem('clubcredits_token') || null,
    sessionType: localStorage.getItem('clubcredits_session_type') || null,
    currentUser: null,
    limits: { max_transfer: 50, daily_limit: 100 },
    members: [],
    transactions: [],
    stats: {},
    activeFilter: 'all',
    activeTab: 'member-section',
    selectedModalMember: null,
    eventSource: null,
    reconnectTimer: null,
    demoAccounts: [],
    directoryCategory: 'all',
    directorySearchQuery: '',
    adminRosterQuery: ''
  };

  // DOM Elements Cache
  const els = {
    // Navigation
    navBtns: document.querySelectorAll('.nav-btn'),
    tabContents: document.querySelectorAll('.tab-content'),
    liveIndicator: document.getElementById('live-indicator'),
    liveStatusText: document.getElementById('live-status-text'),
    sessionPill: document.getElementById('session-pill'),
    sessionUserName: document.getElementById('session-user-name'),
    btnSignout: document.getElementById('btn-signout'),
    activityCounter: document.getElementById('activity-counter'),

    // Member Section
    memberLoginPanel: document.getElementById('member-login-panel'),
    memberDashboard: document.getElementById('member-dashboard'),
    formMemberLogin: document.getElementById('form-member-login'),
    inputMemberId: document.getElementById('input-member-id'),
    inputMemberPass: document.getElementById('input-member-pass'),
    memberLoginError: document.getElementById('member-login-error'),
    btnDemoAccounts: document.querySelectorAll('.btn-demo-account'),
    btnSwitchMember: document.getElementById('btn-switch-member'),
    btnOpenDirectory: document.getElementById('btn-open-directory'),
    btnRandomDemo: document.getElementById('btn-random-demo'),

    // Demo Directory Modal
    directoryModalOverlay: document.getElementById('directory-modal-overlay'),
    btnDirectoryClose: document.getElementById('btn-directory-close'),
    btnDirectoryCancel: document.getElementById('btn-directory-cancel'),
    btnDirectoryRandom: document.getElementById('btn-directory-random'),
    inputDirectorySearch: document.getElementById('input-directory-search'),
    directoryAccountsGrid: document.getElementById('directory-accounts-grid'),
    directoryFilterTags: document.querySelectorAll('.dir-tag'),
    directoryFooterMeta: document.getElementById('directory-footer-meta'),

    // Member Profile & Balance
    memberAvatar: document.getElementById('member-avatar'),
    memberDisplayName: document.getElementById('member-display-name'),
    memberDisplayIdRole: document.getElementById('member-display-id-role'),
    memberBalanceVal: document.getElementById('member-balance-val'),
    memberDailySpentVal: document.getElementById('member-daily-spent-val'),
    memberDailyLimitVal: document.getElementById('member-daily-limit-val'),
    dailyProgressFill: document.getElementById('daily-progress-fill'),
    memberDailyRemainingVal: document.getElementById('member-daily-remaining-val'),
    summaryMaxTransfer: document.getElementById('summary-max-transfer'),
    summaryDailyLimit: document.getElementById('summary-daily-limit'),

    // Transfer Form
    formTransfer: document.getElementById('form-transfer'),
    selectRecipient: document.getElementById('select-recipient'),
    inputAmount: document.getElementById('input-amount'),
    btnSubmitTransfer: document.getElementById('btn-submit-transfer'),
    transferBtnText: document.getElementById('transfer-btn-text'),
    transferSpinner: document.getElementById('transfer-spinner'),
    amountChips: document.querySelectorAll('.btn-amount-chip:not(#btn-amt-max)'),
    btnAmtMax: document.getElementById('btn-amt-max'),

    // Reasoning Decision Box
    decisionBoxWrapper: document.getElementById('decision-box-wrapper'),
    decisionStatusBadge: document.getElementById('decision-status-badge'),
    propA: document.getElementById('prop-a'),
    propAMark: document.getElementById('prop-a-mark'),
    propB: document.getElementById('prop-b'),
    propBMark: document.getElementById('prop-b-mark'),
    propL: document.getElementById('prop-l'),
    propLMark: document.getElementById('prop-l-mark'),
    propD: document.getElementById('prop-d'),
    propDMark: document.getElementById('prop-d-mark'),
    decisionFinalText: document.getElementById('decision-final-text'),
    decisionReasonText: document.getElementById('decision-reason-text'),
    decisionMetaText: document.getElementById('decision-meta-text'),

    // Member Personal Table
    myTransfersTbody: document.getElementById('my-transfers-tbody'),

    // Activity Feed
    activityFeedList: document.getElementById('activity-feed-list'),
    activityEmptyState: document.getElementById('activity-empty-state'),
    filterBtns: document.querySelectorAll('.filter-btn'),
    countAll: document.getElementById('count-all'),
    countApproved: document.getElementById('count-approved'),
    countDeclined: document.getElementById('count-declined'),

    // Admin Section
    adminLoginPanel: document.getElementById('admin-login-panel'),
    adminDashboard: document.getElementById('admin-dashboard'),
    formAdminLogin: document.getElementById('form-admin-login'),
    inputAdminPass: document.getElementById('input-admin-pass'),
    adminLoginError: document.getElementById('admin-login-error'),
    btnAutofillAdmin: document.getElementById('btn-autofill-admin'),

    // Admin Metrics
    metricTotalMembers: document.getElementById('metric-total-members'),
    metricTotalCredits: document.getElementById('metric-total-credits'),
    metricApprovedTxns: document.getElementById('metric-approved-txns'),
    metricDeclinedTxns: document.getElementById('metric-declined-txns'),

    // Admin Limits
    formAdminLimits: document.getElementById('form-admin-limits'),
    inputAdminMaxTransfer: document.getElementById('input-admin-max-transfer'),
    inputAdminDailyLimit: document.getElementById('input-admin-daily-limit'),
    adminLimitsSuccess: document.getElementById('admin-limits-success'),

    // Admin Add Member
    formAdminAddMember: document.getElementById('form-admin-add-member'),
    inputNewMemberId: document.getElementById('input-new-member-id'),
    inputNewMemberName: document.getElementById('input-new-member-name'),
    inputNewMemberRole: document.getElementById('input-new-member-role'),
    inputNewMemberPass: document.getElementById('input-new-member-pass'),
    inputNewMemberBalance: document.getElementById('input-new-member-balance'),
    adminAddSuccess: document.getElementById('admin-add-success'),
    adminAddError: document.getElementById('admin-add-error'),

    // Admin Roster Table
    adminRosterTbody: document.getElementById('admin-roster-tbody'),
    btnResetDemoData: document.getElementById('btn-reset-demo-data'),
    inputAdminRosterSearch: document.getElementById('input-admin-roster-search'),
    adminRosterCountBadge: document.getElementById('admin-roster-count-badge'),

    // Admin Passcode
    formAdminChangePass: document.getElementById('form-admin-change-pass'),
    inputNewAdminPass: document.getElementById('input-new-admin-pass'),
    adminPassSuccess: document.getElementById('admin-pass-success'),
    adminPassError: document.getElementById('admin-pass-error'),

    // Balance Modal
    balanceModalOverlay: document.getElementById('balance-modal-overlay'),
    modalMemberName: document.getElementById('modal-member-name'),
    modalMemberId: document.getElementById('modal-member-id'),
    inputModalBalance: document.getElementById('input-modal-balance'),
    btnModalClose: document.getElementById('btn-modal-close'),
    btnModalCancel: document.getElementById('btn-modal-cancel'),
    btnModalSaveBalance: document.getElementById('btn-modal-save-balance')
  };

  // Helper: Escape HTML to avoid XSS
  function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  // Helper: Format Date
  function formatTime(isoStr) {
    try {
      const d = new Date(isoStr);
      if (isNaN(d.getTime())) return isoStr;
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
      return isoStr;
    }
  }

  // Helper: API Fetcher with Bearer Token
  async function api(path, options = {}) {
    const headers = options.headers || {};
    if (state.token) {
      headers['Authorization'] = `Bearer ${state.token}`;
    }
    if (options.body && typeof options.body === 'object' && !(options.body instanceof FormData)) {
      headers['Content-Type'] = 'application/json';
      options.body = JSON.stringify(options.body);
    }
    options.headers = headers;

    const res = await fetch(path, options);
    let data;
    try {
      data = await res.json();
    } catch {
      data = { error: 'Invalid JSON response from server' };
    }

    if (!res.ok) {
      const err = new Error(data.error || data.reason || `HTTP ${res.status}`);
      err.data = data;
      err.status = res.status;
      throw err;
    }
    return data;
  }

  // Connect SSE for Live Updates
  function initSSE() {
    if (state.eventSource) {
      state.eventSource.close();
    }

    els.liveStatusText.textContent = 'Connecting...';
    const es = new EventSource('/api/events');
    state.eventSource = es;

    es.onopen = () => {
      els.liveIndicator.classList.remove('reconnecting');
      els.liveStatusText.textContent = 'Live Sync';
    };

    es.onerror = () => {
      els.liveIndicator.classList.add('reconnecting');
      els.liveStatusText.textContent = 'Reconnecting...';
    };

    es.addEventListener('transfer_completed', (e) => {
      try {
        const payload = JSON.parse(e.data);
        handleTransferCompletedEvent(payload);
      } catch (err) {
        console.error('Error parsing transfer_completed event:', err);
      }
    });

    es.addEventListener('limits_updated', (e) => {
      try {
        const payload = JSON.parse(e.data);
        state.limits = payload.limits;
        renderLimits();
      } catch (err) {
        console.error('Error parsing limits_updated event:', err);
      }
    });

    es.addEventListener('member_updated', () => {
      loadState();
    });

    es.addEventListener('member_added', () => {
      loadState();
    });

    es.addEventListener('demo_reset', () => {
      loadState();
    });
  }

  function handleTransferCompletedEvent(payload) {
    const { transaction, sender, recipient } = payload;
    // Add transaction to top of local history
    state.transactions.unshift(transaction);

    // Update member balances in local state
    const sIdx = state.members.findIndex(m => m.id === sender.id);
    if (sIdx !== -1) {
      state.members[sIdx].balance = sender.balance;
      state.members[sIdx].today_spent = sender.today_spent;
    }
    const rIdx = state.members.findIndex(m => m.id === recipient.id);
    if (rIdx !== -1) {
      state.members[rIdx].balance = recipient.balance;
    }

    // If current logged in member is sender or recipient, update profile view
    if (state.currentUser && state.sessionType === 'member') {
      if (state.currentUser.id === sender.id) {
        state.currentUser.balance = sender.balance;
        state.currentUser.today_spent = sender.today_spent;
        renderMemberProfile();
      } else if (state.currentUser.id === recipient.id) {
        state.currentUser.balance = recipient.balance;
        renderMemberProfile();
      }
      renderMyTransfers();
    }

    // Refresh general feeds & tables
    renderActivityFeed();
    renderRecipientSelect();
    if (state.sessionType === 'admin') {
      renderAdminDashboard();
    }
  }

  // Load Full Public State
  async function loadState() {
    try {
      const data = await api('/api/state');
      state.limits = data.limits || { max_transfer: 50, daily_limit: 100 };
      state.members = data.members || [];
      state.transactions = data.recent_transactions || [];
      state.stats = data.stats || {};

      if (data.current_user) {
        state.currentUser = data.current_user;
        state.sessionType = data.current_user.type === 'admin' ? 'admin' : 'member';
      }

      await loadDemoAccounts();
      renderAll();
    } catch (err) {
      console.error('Failed to load state:', err);
    }
  }

  // Load Demo Accounts for Directory
  async function loadDemoAccounts() {
    try {
      const res = await api('/api/demo-accounts');
      state.demoAccounts = res.accounts || [];
      renderDemoDirectory();
    } catch (err) {
      console.error('Failed to load demo accounts:', err);
    }
  }

  // Main Render Routine
  function renderAll() {
    renderHeaderSession();
    renderLimits();
    renderRecipientSelect();
    renderActivityFeed();

    if (state.sessionType === 'member' && state.currentUser) {
      els.memberLoginPanel.style.display = 'none';
      els.memberDashboard.style.display = 'block';
      renderMemberProfile();
      renderMyTransfers();
    } else {
      els.memberLoginPanel.style.display = 'block';
      els.memberDashboard.style.display = 'none';
    }

    if (state.sessionType === 'admin') {
      els.adminLoginPanel.style.display = 'none';
      els.adminDashboard.style.display = 'block';
      renderAdminDashboard();
    } else {
      els.adminLoginPanel.style.display = 'block';
      els.adminDashboard.style.display = 'none';
    }
  }

  // Render Header Session Info
  function renderHeaderSession() {
    if (state.token && state.currentUser) {
      els.sessionPill.style.display = 'flex';
      const label = state.sessionType === 'admin' ? 'Treasurer Admin' : state.currentUser.name;
      els.sessionUserName.textContent = label;
    } else {
      els.sessionPill.style.display = 'none';
    }
  }

  // Render Limits Information
  function renderLimits() {
    const max = state.limits.max_transfer || 50;
    const daily = state.limits.daily_limit || 100;

    els.summaryMaxTransfer.textContent = `${max} credits`;
    els.summaryDailyLimit.textContent = `${daily} credits`;
    els.memberDailyLimitVal.textContent = String(daily);

    // Update admin inputs if on admin tab
    if (els.inputAdminMaxTransfer) {
      els.inputAdminMaxTransfer.value = max;
    }
    if (els.inputAdminDailyLimit) {
      els.inputAdminDailyLimit.value = daily;
    }
  }

  // Render Recipient Dropdown (Exclude Current Member)
  function renderRecipientSelect() {
    const currentMemberId = (state.sessionType === 'member' && state.currentUser) ? state.currentUser.id : null;
    const previousSelection = els.selectRecipient.value;

    let html = '<option value="" disabled selected>Choose a club member...</option>';
    state.members.forEach(m => {
      if (m.id !== currentMemberId) {
        html += `<option value="${escapeHtml(m.id)}">${escapeHtml(m.name)} (${escapeHtml(m.id)}) · ${escapeHtml(m.role || 'Member')}</option>`;
      }
    });
    els.selectRecipient.innerHTML = html;

    if (previousSelection && previousSelection !== currentMemberId) {
      els.selectRecipient.value = previousSelection;
    }
  }

  // Render Member Profile Card
  function renderMemberProfile() {
    if (!state.currentUser) return;
    const user = state.currentUser;
    const initials = user.name ? user.name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase() : 'CC';
    els.memberAvatar.textContent = initials;
    els.memberDisplayName.textContent = user.name;
    els.memberDisplayIdRole.textContent = `${user.id} · ${user.role || 'Club Member'}`;
    els.memberBalanceVal.textContent = String(user.balance);

    const spent = user.today_spent || 0;
    const dailyLimit = state.limits.daily_limit || 100;
    const remaining = Math.max(0, dailyLimit - spent);

    els.memberDailySpentVal.textContent = String(spent);
    els.memberDailyLimitVal.textContent = String(dailyLimit);
    els.memberDailyRemainingVal.textContent = String(remaining);

    const pct = Math.min(100, Math.round((spent / dailyLimit) * 100));
    els.dailyProgressFill.style.width = `${pct}%`;
    if (pct >= 90) {
      els.dailyProgressFill.style.background = 'linear-gradient(90deg, #F59E0B, #EF4444)';
    } else {
      els.dailyProgressFill.style.background = 'linear-gradient(90deg, var(--brand-green), var(--brand-teal))';
    }
  }

  // Render Member's Personal Transfer Log
  function renderMyTransfers() {
    if (!state.currentUser) return;
    const currId = state.currentUser.id;
    const myTxns = state.transactions.filter(t => t.sender_id === currId || t.recipient_id === currId);

    if (myTxns.length === 0) {
      els.myTransfersTbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No personal transfers yet. Try sending credits above!</td></tr>';
      return;
    }

    let html = '';
    myTxns.slice(0, 50).forEach(txn => {
      const isOutgoing = txn.sender_id === currId;
      const isApproved = txn.status === 'approved';
      const peerName = isOutgoing ? txn.recipient_name : txn.sender_name;
      const peerId = isOutgoing ? txn.recipient_id : txn.sender_id;
      const typeLabel = isOutgoing ? 'Sent' : 'Received';
      const checks = txn.checks || {};

      html += `
        <tr>
          <td>
            <span class="badge-status ${isApproved ? 'approved' : 'declined'}">
              ${isApproved ? '✓ Approved' : '✗ Declined'}
            </span>
          </td>
          <td><strong>${typeLabel}</strong></td>
          <td>${escapeHtml(peerName)} <span class="text-muted">(${escapeHtml(peerId)})</span></td>
          <td><strong>${escapeHtml(txn.amount)}</strong> credits</td>
          <td>
            <span class="checks-pill" title="A=${checks.A}, B=${checks.B}, L=${checks.L}, D=${checks.D}">
              A:${checks.A ? '✓' : '✗'} B:${checks.B ? '✓' : '✗'} L:${checks.L ? '✓' : '✗'} D:${checks.D ? '✓' : '✗'}
            </span>
          </td>
          <td class="text-muted">${escapeHtml(formatTime(txn.timestamp))}</td>
        </tr>
      `;
    });
    els.myTransfersTbody.innerHTML = html;
  }

  // Render Compact Visible Reasoning Box
  function renderDecisionReasoning(result) {
    const { decision, reason, checks, transaction } = result;
    const isApproved = decision === 'approved';

    els.decisionBoxWrapper.style.display = 'block';
    els.decisionBoxWrapper.className = `decision-box-wrapper status-${decision}`;

    els.decisionStatusBadge.textContent = isApproved ? 'Approved' : 'Declined';
    els.decisionStatusBadge.className = `decision-badge ${decision}`;

    // Update Propositions
    const setMark = (el, passed) => {
      el.textContent = passed ? '✓' : '✗';
      el.className = `prop-mark ${passed ? 'pass' : 'fail'}`;
    };

    setMark(els.propAMark, checks.A);
    setMark(els.propBMark, checks.B);
    setMark(els.propLMark, checks.L);
    setMark(els.propDMark, checks.D);

    els.decisionFinalText.textContent = isApproved ? 'Approved' : 'Declined';
    els.decisionFinalText.className = isApproved ? 'text-success' : 'text-danger';
    els.decisionReasonText.textContent = reason;

    const txnId = transaction && transaction.id ? transaction.id : 'TXN-LOCAL';
    const txnTime = transaction && transaction.timestamp ? formatTime(transaction.timestamp) : new Date().toLocaleTimeString();
    els.decisionMetaText.textContent = `Transaction: ${txnId} · Recorded ${txnTime} · Evaluated on server`;

    // Scroll slightly if on small screens to ensure visibility
    els.decisionBoxWrapper.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  // Render Activity Feed
  function renderActivityFeed() {
    const txns = state.transactions;
    els.activityCounter.textContent = String(txns.length);

    let approvedCount = 0;
    let declinedCount = 0;
    txns.forEach(t => {
      if (t.status === 'approved') approvedCount++;
      else declinedCount++;
    });

    els.countAll.textContent = String(txns.length);
    els.countApproved.textContent = String(approvedCount);
    els.countDeclined.textContent = String(declinedCount);

    const filtered = txns.filter(t => {
      if (state.activeFilter === 'approved') return t.status === 'approved';
      if (state.activeFilter === 'declined') return t.status === 'declined';
      return true;
    });

    if (filtered.length === 0) {
      els.activityEmptyState.style.display = 'block';
      els.activityFeedList.innerHTML = '';
      els.activityFeedList.appendChild(els.activityEmptyState);
      return;
    }

    els.activityEmptyState.style.display = 'none';
    let html = '';
    filtered.forEach(txn => {
      const isApproved = txn.status === 'approved';
      const checks = txn.checks || {};
      html += `
        <article class="activity-item ${isApproved ? 'approved-item' : 'declined-item'}">
          <div class="activity-item-main">
            <div class="activity-flow-row">
              <span class="flow-sender">${escapeHtml(txn.sender_name)} (${escapeHtml(txn.sender_id)})</span>
              <span class="flow-arrow">→</span>
              <span class="flow-recipient">${escapeHtml(txn.recipient_name)} (${escapeHtml(txn.recipient_id)})</span>
              <span class="flow-amount">${escapeHtml(txn.amount)} credits</span>
            </div>
            <div class="activity-reason-desc">
              ${escapeHtml(txn.reason)}
            </div>
            <div class="activity-meta-row">
              <span class="checks-pill" title="Proposition Logic">
                A:${checks.A ? '✓' : '✗'} B:${checks.B ? '✓' : '✗'} L:${checks.L ? '✓' : '✗'} D:${checks.D ? '✓' : '✗'}
              </span>
              <span>Policy: T ↔ (A ∧ B ∧ L ∧ D)</span>
              <span>•</span>
              <span>${escapeHtml(txn.id)}</span>
              <span>•</span>
              <time datetime="${escapeHtml(txn.timestamp)}">${escapeHtml(formatTime(txn.timestamp))}</time>
            </div>
          </div>
          <div class="activity-item-aside">
            <span class="badge-status ${isApproved ? 'approved' : 'declined'}">
              ${isApproved ? '✓ Approved' : '✗ Declined'}
            </span>
          </div>
        </article>
      `;
    });
    els.activityFeedList.innerHTML = html;
  }

  // Render Admin Dashboard
  function renderAdminDashboard() {
    // KPIs
    const totalMembers = state.members.length;
    const totalCredits = state.members.reduce((acc, m) => acc + (m.balance || 0), 0);
    let approved = 0;
    let declined = 0;
    state.transactions.forEach(t => {
      if (t.status === 'approved') approved++;
      else declined++;
    });

    els.metricTotalMembers.textContent = String(totalMembers);
    els.metricTotalCredits.textContent = String(totalCredits);
    els.metricApprovedTxns.textContent = String(approved);
    els.metricDeclinedTxns.textContent = String(declined);

    // Membership Roster Table with Live Search Filter
    const query = (state.adminRosterQuery || '').trim().toLowerCase();
    const filteredMembers = state.members.filter(m => {
      if (!query) return true;
      return m.name.toLowerCase().includes(query) ||
             m.id.toLowerCase().includes(query) ||
             (m.role && m.role.toLowerCase().includes(query));
    });

    if (els.adminRosterCountBadge) {
      els.adminRosterCountBadge.textContent = query
        ? `Showing ${filteredMembers.length} of ${totalMembers} Members`
        : `${totalMembers} Members`;
    }

    if (filteredMembers.length === 0) {
      els.adminRosterTbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No members match your search criteria.</td></tr>';
      return;
    }

    let html = '';
    filteredMembers.forEach(m => {
      html += `
        <tr>
          <td><code>${escapeHtml(m.id)}</code></td>
          <td><strong>${escapeHtml(m.name)}</strong></td>
          <td>${escapeHtml(m.role || 'Member')}</td>
          <td><strong>${escapeHtml(m.balance)}</strong> credits</td>
          <td>${escapeHtml(m.today_spent || 0)} / ${state.limits.daily_limit} cr</td>
          <td>
            <button class="btn btn-sm btn-outline btn-set-member-balance" data-id="${escapeHtml(m.id)}" data-name="${escapeHtml(m.name)}" data-bal="${m.balance}">
              Set Balance
            </button>
          </td>
        </tr>
      `;
    });
    els.adminRosterTbody.innerHTML = html;

    // Attach click events to "Set Balance" buttons
    document.querySelectorAll('.btn-set-member-balance').forEach(btn => {
      btn.addEventListener('click', () => {
        const id = btn.getAttribute('data-id');
        const name = btn.getAttribute('data-name');
        const bal = btn.getAttribute('data-bal');
        openBalanceModal(id, name, bal);
      });
    });
  }

  // Demo Accounts Directory Modal Functions
  function openDirectoryModal() {
    els.directoryModalOverlay.style.display = 'flex';
    renderDemoDirectory();
    if (els.inputDirectorySearch) {
      els.inputDirectorySearch.focus();
    }
  }

  function closeDirectoryModal() {
    els.directoryModalOverlay.style.display = 'none';
  }

  function renderDemoDirectory() {
    if (!els.directoryAccountsGrid) return;
    const query = (state.directorySearchQuery || '').trim().toLowerCase();
    const cat = state.directoryCategory || 'all';

    const filtered = state.demoAccounts.filter(acc => {
      const matchesQuery = !query ||
        acc.name.toLowerCase().includes(query) ||
        acc.id.toLowerCase().includes(query) ||
        (acc.role && acc.role.toLowerCase().includes(query));

      if (!matchesQuery) return false;

      if (cat === 'lead') {
        return acc.role && (acc.role.includes('Lead') || acc.role.includes('Captain') || acc.role.includes('President'));
      }
      if (cat === 'stem') {
        return acc.role && (acc.role.includes('Robotics') || acc.role.includes('Science') || acc.role.includes('Coding') || acc.role.includes('Math') || acc.role.includes('AI') || acc.role.includes('Cyber') || acc.role.includes('Rocketry'));
      }
      if (cat === 'arts') {
        return acc.role && (acc.role.includes('Design') || acc.role.includes('Art') || acc.role.includes('Theater') || acc.role.includes('Photo') || acc.role.includes('Radio') || acc.role.includes('Music') || acc.role.includes('Journalism'));
      }
      if (cat === 'highbal') {
        return acc.balance > 100;
      }
      return true;
    });

    if (els.directoryFooterMeta) {
      els.directoryFooterMeta.textContent = `Showing ${filtered.length} of ${state.demoAccounts.length} accounts`;
    }

    if (filtered.length === 0) {
      els.directoryAccountsGrid.innerHTML = '<div class="empty-state" style="grid-column: 1 / -1;"><p>No demo accounts found matching search.</p></div>';
      return;
    }

    let html = '';
    filtered.forEach(acc => {
      const initials = acc.name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
      html += `
        <div class="dir-account-card" data-id="${escapeHtml(acc.id)}" data-pass="${escapeHtml(acc.passcode)}" title="Click to sign in immediately as ${escapeHtml(acc.name)}">
          <div class="dir-card-top">
            <div class="dir-avatar">${initials}</div>
            <div class="dir-meta">
              <div class="dir-name">${escapeHtml(acc.name)}</div>
              <span class="dir-id-badge">${escapeHtml(acc.id)}</span>
            </div>
          </div>
          <div class="dir-role">${escapeHtml(acc.role)}</div>
          <div class="dir-bottom-row">
            <span class="dir-balance">${acc.balance} credits</span>
            <span class="dir-passcode">Key: ${escapeHtml(acc.passcode)}</span>
          </div>
        </div>
      `;
    });
    els.directoryAccountsGrid.innerHTML = html;

    els.directoryAccountsGrid.querySelectorAll('.dir-account-card').forEach(card => {
      card.addEventListener('click', () => {
        const id = card.getAttribute('data-id');
        const pass = card.getAttribute('data-pass');
        signInWithDemoAccount(id, pass);
      });
    });
  }

  function signInWithDemoAccount(id, pass) {
    closeDirectoryModal();
    // Switch to member tab if not active
    const memberTabBtn = document.getElementById('nav-member-tab');
    if (memberTabBtn) memberTabBtn.click();

    els.inputMemberId.value = id;
    els.inputMemberPass.value = pass;
    els.formMemberLogin.dispatchEvent(new Event('submit'));
  }

  function signInRandomDemo() {
    if (!state.demoAccounts || state.demoAccounts.length === 0) return;
    const randomIndex = Math.floor(Math.random() * state.demoAccounts.length);
    const chosen = state.demoAccounts[randomIndex];
    signInWithDemoAccount(chosen.id, chosen.passcode);
  }

  // Open Balance Adjuster Modal
  function openBalanceModal(id, name, currentBalance) {
    state.selectedModalMember = { id, name, balance: currentBalance };
    els.modalMemberName.textContent = name;
    els.modalMemberId.textContent = id;
    els.inputModalBalance.value = currentBalance;
    els.balanceModalOverlay.style.display = 'flex';
    els.inputModalBalance.focus();
  }

  function closeBalanceModal() {
    els.balanceModalOverlay.style.display = 'none';
    state.selectedModalMember = null;
  }

  // Setup Event Listeners
  function initEvents() {
    // Nav tabs toggle
    els.navBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        const targetId = btn.getAttribute('data-tab');
        state.activeTab = targetId;

        els.navBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        els.tabContents.forEach(tab => {
          if (tab.id === targetId) {
            tab.classList.add('active');
          } else {
            tab.classList.remove('active');
          }
        });
      });
    });

    // Sign out button
    els.btnSignout.addEventListener('click', async () => {
      try {
        await api('/api/auth/logout', { method: 'POST' });
      } catch (e) {
        console.warn(e);
      }
      state.token = null;
      state.sessionType = null;
      state.currentUser = null;
      localStorage.removeItem('clubcredits_token');
      localStorage.removeItem('clubcredits_session_type');
      loadState();
    });

    // Switch account button (in member dashboard)
    if (els.btnSwitchMember) {
      els.btnSwitchMember.addEventListener('click', async () => {
        try {
          await api('/api/auth/logout', { method: 'POST' });
        } catch (e) {
          console.warn(e);
        }
        state.token = null;
        state.sessionType = null;
        state.currentUser = null;
        localStorage.removeItem('clubcredits_token');
        localStorage.removeItem('clubcredits_session_type');
        loadState();
      });
    }

    // Member Login Form
    els.formMemberLogin.addEventListener('submit', async (e) => {
      e.preventDefault();
      els.memberLoginError.style.display = 'none';
      const memberId = els.inputMemberId.value.trim();
      const passcode = els.inputMemberPass.value.trim();

      try {
        const res = await api('/api/auth/member-login', {
          method: 'POST',
          body: { member_id: memberId, passcode: passcode }
        });

        state.token = res.token;
        state.sessionType = 'member';
        state.currentUser = res.user;
        localStorage.setItem('clubcredits_token', res.token);
        localStorage.setItem('clubcredits_session_type', 'member');

        els.inputMemberPass.value = '';
        loadState();
      } catch (err) {
        els.memberLoginError.textContent = err.message || 'Invalid member credentials';
        els.memberLoginError.style.display = 'block';
      }
    });

    // Demo Member Quick-Sign-In buttons
    els.btnDemoAccounts.forEach(btn => {
      btn.addEventListener('click', () => {
        const id = btn.getAttribute('data-id');
        const pass = btn.getAttribute('data-pass');
        els.inputMemberId.value = id;
        els.inputMemberPass.value = pass;
        els.formMemberLogin.dispatchEvent(new Event('submit'));
      });
    });

    // Admin Quick-Autofill button
    if (els.btnAutofillAdmin) {
      els.btnAutofillAdmin.addEventListener('click', () => {
        els.inputAdminPass.value = 'adminpass';
        els.formAdminLogin.dispatchEvent(new Event('submit'));
      });
    }

    // Admin Login Form
    els.formAdminLogin.addEventListener('submit', async (e) => {
      e.preventDefault();
      els.adminLoginError.style.display = 'none';
      const passcode = els.inputAdminPass.value.trim();

      try {
        const res = await api('/api/auth/admin-login', {
          method: 'POST',
          body: { passcode: passcode }
        });

        state.token = res.token;
        state.sessionType = 'admin';
        state.currentUser = res.user;
        localStorage.setItem('clubcredits_token', res.token);
        localStorage.setItem('clubcredits_session_type', 'admin');

        els.inputAdminPass.value = '';
        loadState();
      } catch (err) {
        els.adminLoginError.textContent = err.message || 'Incorrect administrator passcode';
        els.adminLoginError.style.display = 'block';
      }
    });

    // Amount chips click
    els.amountChips.forEach(chip => {
      chip.addEventListener('click', () => {
        const amt = parseInt(chip.getAttribute('data-amt'), 10);
        els.inputAmount.value = amt;
      });
    });

    // Max Safe chip click
    if (els.btnAmtMax) {
      els.btnAmtMax.addEventListener('click', () => {
        if (!state.currentUser) return;
        const bal = state.currentUser.balance || 0;
        const maxSingle = state.limits.max_transfer || 50;
        const dailyLimit = state.limits.daily_limit || 100;
        const dailySpent = state.currentUser.today_spent || 0;
        const dailyRemaining = Math.max(0, dailyLimit - dailySpent);

        const safeMax = Math.min(bal, maxSingle, dailyRemaining);
        els.inputAmount.value = Math.max(1, safeMax);
      });
    }

    // Submit Transfer Form
    els.formTransfer.addEventListener('submit', async (e) => {
      e.preventDefault();
      const recipientId = els.selectRecipient.value;
      const amount = parseInt(els.inputAmount.value, 10);

      if (!recipientId) {
        alert('Please select a recipient member.');
        return;
      }
      if (!amount || amount <= 0) {
        alert('Please enter a positive whole number of credits.');
        return;
      }

      // UI Loading state
      els.transferBtnText.textContent = 'Evaluating policy...';
      els.transferSpinner.style.display = 'inline-block';
      els.btnSubmitTransfer.disabled = true;

      try {
        const res = await api('/api/transfer', {
          method: 'POST',
          body: { recipient_id: recipientId, amount: amount }
        });

        renderDecisionReasoning(res);
        els.inputAmount.value = '';
      } catch (err) {
        // If declined, API sends 200 with decision="declined" OR 400/401 with reason and checks
        if (err.data && err.data.checks) {
          renderDecisionReasoning(err.data);
        } else {
          alert(err.message || 'Transfer failed');
        }
      } finally {
        els.transferBtnText.textContent = 'Submit Transfer';
        els.transferSpinner.style.display = 'none';
        els.btnSubmitTransfer.disabled = false;
      }
    });

    // Activity Feed Filter Tabs
    els.filterBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        els.filterBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        state.activeFilter = btn.getAttribute('data-filter');
        renderActivityFeed();
      });
    });

    // Admin Save Limits Form
    els.formAdminLimits.addEventListener('submit', async (e) => {
      e.preventDefault();
      els.adminLimitsSuccess.style.display = 'none';
      const maxTransfer = parseInt(els.inputAdminMaxTransfer.value, 10);
      const dailyLimit = parseInt(els.inputAdminDailyLimit.value, 10);

      try {
        const res = await api('/api/admin/set-limits', {
          method: 'POST',
          body: { max_transfer: maxTransfer, daily_limit: dailyLimit }
        });
        state.limits = res.limits;
        renderLimits();
        els.adminLimitsSuccess.textContent = 'Transfer limits updated and broadcast to all members.';
        els.adminLimitsSuccess.style.display = 'block';
        setTimeout(() => { els.adminLimitsSuccess.style.display = 'none'; }, 4000);
      } catch (err) {
        alert(err.message || 'Failed to update limits');
      }
    });

    // Admin Add Member Form
    els.formAdminAddMember.addEventListener('submit', async (e) => {
      e.preventDefault();
      els.adminAddSuccess.style.display = 'none';
      els.adminAddError.style.display = 'none';

      const memberId = els.inputNewMemberId.value.trim().toUpperCase();
      const name = els.inputNewMemberName.value.trim();
      const role = els.inputNewMemberRole.value.trim() || 'Club Member';
      const passcode = els.inputNewMemberPass.value.trim();
      const balance = parseInt(els.inputNewMemberBalance.value, 10) || 0;

      try {
        await api('/api/admin/add-member', {
          method: 'POST',
          body: { member_id: memberId, name, role, passcode, balance }
        });

        els.adminAddSuccess.textContent = `Member ${name} (${memberId}) enrolled successfully!`;
        els.adminAddSuccess.style.display = 'block';
        els.formAdminAddMember.reset();
        els.inputNewMemberBalance.value = '50';
        setTimeout(() => { els.adminAddSuccess.style.display = 'none'; }, 4000);
        loadState();
      } catch (err) {
        els.adminAddError.textContent = err.message || 'Failed to enroll member';
        els.adminAddError.style.display = 'block';
      }
    });

    // Admin Reset Demo Data
    if (els.btnResetDemoData) {
      els.btnResetDemoData.addEventListener('click', async () => {
        if (!confirm('Reset group ledger to original demo state with default sample balances?')) return;
        try {
          await api('/api/admin/reset-demo', { method: 'POST' });
          alert('Group ledger reset to default demo accounts.');
          loadState();
        } catch (err) {
          alert(err.message || 'Failed to reset demo data');
        }
      });
    }

    // Admin Change Passcode
    els.formAdminChangePass.addEventListener('submit', async (e) => {
      e.preventDefault();
      els.adminPassSuccess.style.display = 'none';
      els.adminPassError.style.display = 'none';

      const newPass = els.inputNewAdminPass.value.trim();
      try {
        await api('/api/admin/change-passcode', {
          method: 'POST',
          body: { new_passcode: newPass }
        });
        els.adminPassSuccess.textContent = 'Administrator passcode updated successfully.';
        els.adminPassSuccess.style.display = 'block';
        els.inputNewAdminPass.value = '';
        setTimeout(() => { els.adminPassSuccess.style.display = 'none'; }, 4000);
      } catch (err) {
        els.adminPassError.textContent = err.message || 'Failed to change passcode';
        els.adminPassError.style.display = 'block';
      }
    });

    // Balance Modal Events
    els.btnModalClose.addEventListener('click', closeBalanceModal);
    els.btnModalCancel.addEventListener('click', closeBalanceModal);
    els.balanceModalOverlay.addEventListener('click', (e) => {
      if (e.target === els.balanceModalOverlay) closeBalanceModal();
    });

    els.btnModalSaveBalance.addEventListener('click', async () => {
      if (!state.selectedModalMember) return;
      const newBal = parseInt(els.inputModalBalance.value, 10);
      if (isNaN(newBal) || newBal < 0) {
        alert('Please enter a valid non-negative credit amount.');
        return;
      }

      try {
        await api('/api/admin/set-balance', {
          method: 'POST',
          body: { member_id: state.selectedModalMember.id, balance: newBal }
        });
        closeBalanceModal();
        loadState();
      } catch (err) {
        alert(err.message || 'Failed to update member balance');
      }
    });

    // Demo Directory Modal & Random Login Events
    if (els.btnOpenDirectory) {
      els.btnOpenDirectory.addEventListener('click', openDirectoryModal);
    }
    if (els.btnDirectoryClose) {
      els.btnDirectoryClose.addEventListener('click', closeDirectoryModal);
    }
    if (els.btnDirectoryCancel) {
      els.btnDirectoryCancel.addEventListener('click', closeDirectoryModal);
    }
    if (els.directoryModalOverlay) {
      els.directoryModalOverlay.addEventListener('click', (e) => {
        if (e.target === els.directoryModalOverlay) closeDirectoryModal();
      });
    }

    if (els.btnRandomDemo) {
      els.btnRandomDemo.addEventListener('click', signInRandomDemo);
    }
    if (els.btnDirectoryRandom) {
      els.btnDirectoryRandom.addEventListener('click', signInRandomDemo);
    }

    if (els.inputDirectorySearch) {
      els.inputDirectorySearch.addEventListener('input', (e) => {
        state.directorySearchQuery = e.target.value;
        renderDemoDirectory();
      });
    }

    if (els.directoryFilterTags) {
      els.directoryFilterTags.forEach(tag => {
        tag.addEventListener('click', () => {
          els.directoryFilterTags.forEach(t => t.classList.remove('active'));
          tag.classList.add('active');
          state.directoryCategory = tag.getAttribute('data-cat') || 'all';
          renderDemoDirectory();
        });
      });
    }

    // Admin Roster Search
    if (els.inputAdminRosterSearch) {
      els.inputAdminRosterSearch.addEventListener('input', (e) => {
        state.adminRosterQuery = e.target.value;
        renderAdminDashboard();
      });
    }
  }

  // Initialization
  document.addEventListener('DOMContentLoaded', () => {
    initEvents();
    loadState();
    initSSE();
  });

})();
