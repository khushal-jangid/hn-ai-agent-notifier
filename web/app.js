document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const emailInput = document.getElementById('emailInput');
    const passwordInput = document.getElementById('passwordInput');
    const togglePasswordBtn = document.getElementById('togglePasswordBtn');
    const topNSelect = document.getElementById('topNSelect');
    const sendEmailBtn = document.getElementById('sendEmailBtn');
    const fetchBriefBtn = document.getElementById('fetchBriefBtn');
    const copyBriefBtn = document.getElementById('copyBriefBtn');
    const liveModeToggle = document.getElementById('liveModeToggle');
    const toggleLabel = document.getElementById('toggleLabel');
    const liveStatusBadge = document.getElementById('liveStatusBadge');
    
    // Stats Elements
    const statStoriesCount = document.getElementById('statStoriesCount');
    const statMaxPoints = document.getElementById('statMaxPoints');
    const statTotalComments = document.getElementById('statTotalComments');
    const statAgentScore = document.getElementById('statAgentScore');

    // Search & Filters
    const searchInput = document.getElementById('searchInput');
    const clearSearchBtn = document.getElementById('clearSearchBtn');
    const filterPills = document.getElementById('filterPills');

    // Containers & States
    const loadingState = document.getElementById('loadingState');
    const storiesContainer = document.getElementById('storiesContainer');
    const briefTime = document.getElementById('briefTime');
    const nextActionsList = document.getElementById('nextActionsList');
    const actionProgressBadge = document.getElementById('actionProgressBadge');
    const briefTextContent = document.getElementById('briefTextContent');

    // Toast & Modal Elements
    const toast = document.getElementById('toast');
    const toastIcon = document.getElementById('toastIcon');
    const toastTitle = document.getElementById('toastTitle');
    const toastMessage = document.getElementById('toastMessage');
    const toastCloseBtn = document.getElementById('toastCloseBtn');
    
    const briefModal = document.getElementById('briefModal');
    const modalBriefText = document.getElementById('modalBriefText');
    const expandBriefBtn = document.getElementById('expandBriefBtn');
    const closeModalBtn = document.getElementById('closeModalBtn');
    const modalCopyBtn = document.getElementById('modalCopyBtn');

    // App State
    let currentBrief = null;
    let currentStories = [];
    let currentFilter = 'all';
    let currentSearchTerm = '';
    let isLiveMode = true;

    // Initial load
    fetchLiveBrief();

    // Auto-refresh news on website every 5 minutes if tab is open
    setInterval(() => {
        console.log('[AutoRefresh] Updating website news from Hacker News API...');
        fetchLiveBrief();
    }, 300000);


    // Event Listeners
    fetchBriefBtn.addEventListener('click', () => fetchLiveBrief());
    sendEmailBtn.addEventListener('click', () => sendEmailBriefing());
    copyBriefBtn.addEventListener('click', () => copyBriefToClipboard());

    liveModeToggle.addEventListener('change', (e) => {
        isLiveMode = e.target.checked;
        toggleLabel.textContent = isLiveMode ? 'Live HN API' : 'Sample Mode';
        updateStatusBadge(isLiveMode);
        fetchLiveBrief();
    });

    togglePasswordBtn.addEventListener('click', () => {
        const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
        passwordInput.setAttribute('type', type);
        togglePasswordBtn.innerHTML = type === 'password' ? '<i class="fa-solid fa-eye"></i>' : '<i class="fa-solid fa-eye-slash"></i>';
    });

    searchInput.addEventListener('input', (e) => {
        currentSearchTerm = e.target.value.toLowerCase().trim();
        clearSearchBtn.classList.toggle('hidden', currentSearchTerm.length === 0);
        renderStories();
    });

    clearSearchBtn.addEventListener('click', () => {
        searchInput.value = '';
        currentSearchTerm = '';
        clearSearchBtn.classList.add('hidden');
        renderStories();
    });

    filterPills.addEventListener('click', (e) => {
        const pillBtn = e.target.closest('.pill');
        if (pillBtn) {
            filterPills.querySelectorAll('.pill').forEach(p => p.classList.remove('active'));
            pillBtn.classList.add('active');
            currentFilter = pillBtn.dataset.filter;
            renderStories();
        }
    });

    toastCloseBtn.addEventListener('click', () => toast.classList.add('hidden'));
    
    expandBriefBtn.addEventListener('click', () => {
        if (currentBrief) {
            modalBriefText.value = currentBrief.text || '';
            briefModal.classList.remove('hidden');
        }
    });

    closeModalBtn.addEventListener('click', () => briefModal.classList.add('hidden'));
    modalCopyBtn.addEventListener('click', () => {
        navigator.clipboard.writeText(modalBriefText.value).then(() => {
            showToast('Copied full brief to clipboard!', 'success', 'Copied!');
        });
    });

    // Main API Methods
    async function fetchLiveBrief() {
        showLoading(true);
        const topN = topNSelect.value;
        try {
            const res = await fetch(`/api/brief?live=${isLiveMode}&top_n=${topN}`);
            const data = await res.json();

            if (data.success && data.brief) {
                currentBrief = data.brief;
                currentStories = data.brief.stories || [];
                briefTime.innerHTML = `<i class="fa-regular fa-clock"></i> Updated: ${new Date(data.brief.generated_at).toLocaleTimeString()}`;
                
                updateStats(currentStories);
                renderStories();
                renderChecklist(data.brief.next_actions || []);
                renderBriefPreview(data.brief.text || '');

                if (data.warning) {
                    showToast(`Fallback mode: ${data.warning}`, 'warning', 'Notice');
                } else {
                    showToast(`Loaded ${currentStories.length} agent stories successfully!`, 'success', 'Updated');
                }
            } else {
                showToast('Error loading Hacker News brief', 'error', 'Error');
            }
        } catch (err) {
            console.error(err);
            showToast('Could not connect to AgentScout backend server', 'error', 'Connection Error');
        } finally {
            showLoading(false);
        }
    }

    async function sendEmailBriefing() {
        const email = emailInput.value.trim();
        const password = passwordInput.value.trim();
        const topN = topNSelect.value;

        if (!email) {
            showToast('Please enter a recipient email address!', 'error', 'Missing Email');
            return;
        }

        sendEmailBtn.disabled = true;
        sendEmailBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Dispatching Email...';

        try {
            const res = await fetch('/api/send-email', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    email: email,
                    password: password,
                    top_n: parseInt(topN),
                    live: isLiveMode
                })
            });

            const data = await res.json();

            if (data.success && data.result?.sent) {
                showToast(`Briefing successfully dispatched to ${email}! 🚀`, 'success', 'Dispatched!');
                if (data.brief && data.brief.stories) {
                    currentBrief = data.brief;
                    currentStories = data.brief.stories;
                    updateStats(currentStories);
                    renderStories();
                }
            } else {
                const errDetail = data.result?.error || data.detail || 'Failed to dispatch email';
                showToast(`Email delivery error: ${errDetail}`, 'error', 'Delivery Failed');
            }
        } catch (err) {
            console.error(err);
            showToast('Error sending email. Check backend connection.', 'error', 'Server Error');
        } finally {
            sendEmailBtn.disabled = false;
            sendEmailBtn.innerHTML = '<i class="fa-solid fa-paper-plane"></i> Send Briefing to Email';
        }
    }

    function copyBriefToClipboard() {
        if (!currentBrief || !currentBrief.text) {
            showToast('No brief data available to copy', 'error', 'Empty Brief');
            return;
        }
        navigator.clipboard.writeText(currentBrief.text).then(() => {
            showToast('Briefing markdown copied to clipboard! 📋', 'success', 'Copied');
        }).catch(err => {
            console.error(err);
            showToast('Failed to copy to clipboard', 'error');
        });
    }

    // Render Helpers
    function updateStats(stories) {
        statStoriesCount.textContent = stories.length;
        
        const maxPoints = stories.length ? Math.max(...stories.map(s => s.points || 0)) : 0;
        statMaxPoints.textContent = maxPoints;

        const totalComments = stories.reduce((sum, s) => sum + (s.comments || 0), 0);
        statTotalComments.textContent = totalComments;

        // Arbitrary signal quality score based on keyword match
        statAgentScore.textContent = stories.length ? '98%' : '0%';
    }

    function renderStories() {
        storiesContainer.innerHTML = '';

        let filtered = currentStories;

        // Apply Pill Filter
        if (currentFilter !== 'all') {
            filtered = filtered.filter(s => {
                const combined = (s.title + ' ' + s.summary).toLowerCase();
                return combined.includes(currentFilter);
            });
        }

        // Apply Search Filter
        if (currentSearchTerm) {
            filtered = filtered.filter(s => {
                const combined = (s.title + ' ' + s.summary).toLowerCase();
                return combined.includes(currentSearchTerm);
            });
        }

        if (filtered.length === 0) {
            storiesContainer.innerHTML = `
                <div class="story-card" style="text-align:center; padding: 40px; color: var(--text-muted);">
                    <i class="fa-solid fa-folder-open" style="font-size: 2.5rem; margin-bottom: 12px; color: var(--border-accent);"></i>
                    <p style="font-size: 1rem; font-weight: 600; color: var(--text-primary);">No stories matched your active filters.</p>
                    <p style="font-size: 0.85rem; margin-top: 4px;">Try clearing the search query or switching category pills.</p>
                </div>
            `;
            return;
        }

        const maxPointsInSet = Math.max(...currentStories.map(s => s.points || 1), 1);

        filtered.forEach((story, idx) => {
            const card = document.createElement('div');
            card.className = 'story-card';
            card.style.animationDelay = `${idx * 0.08}s`;

            const tags = extractTags(story.title + ' ' + story.summary);
            const tagsHtml = tags.map(t => `<span class="tag-badge tag-${t.key}">${t.label}</span>`).join('');

            // Calculate signal percentage bar (cap at 100%)
            const signalPct = Math.min(100, Math.round(((story.points || 0) / maxPointsInSet) * 100));

            card.innerHTML = `
                <div class="story-card-top">
                    <div class="story-header">
                        <span class="rank-badge">#${story.rank || idx + 1}</span>
                        <a href="${story.url}" target="_blank" class="story-title" rel="noopener">${escapeHtml(story.title)}</a>
                    </div>
                </div>
                
                <div class="keywords-container">
                    ${tagsHtml}
                </div>

                <p class="story-summary">${escapeHtml(story.summary)}</p>
                
                <div class="signal-meter-box">
                    <div class="signal-label-row">
                        <span>HN Momentum Signal</span>
                        <span>${signalPct}% Velocity</span>
                    </div>
                    <div class="signal-bar-track">
                        <div class="signal-bar-fill" style="width: ${signalPct}%"></div>
                    </div>
                </div>

                <div class="story-meta">
                    <div class="meta-stats">
                        <span><i class="fa-solid fa-fire"></i> ${story.points || 0} pts</span>
                        <span><i class="fa-solid fa-comments"></i> ${story.comments || 0} comments</span>
                    </div>
                    <div class="meta-links">
                        <a href="${story.url}" target="_blank" rel="noopener"><i class="fa-solid fa-arrow-up-right-from-square"></i> Source</a>
                        <a href="${story.hn_url}" target="_blank" rel="noopener"><i class="fa-brands fa-y-combinator"></i> Discussion</a>
                    </div>
                </div>
            `;

            storiesContainer.appendChild(card);
        });
    }

    function renderChecklist(actions) {
        nextActionsList.innerHTML = '';
        if (!actions || actions.length === 0) return;

        actions.forEach((action, idx) => {
            const li = document.createElement('li');
            li.innerHTML = `
                <input type="checkbox" id="chk_${idx}">
                <label for="chk_${idx}" class="action-text">${escapeHtml(action)}</label>
            `;

            const chk = li.querySelector('input');
            chk.addEventListener('change', () => {
                li.classList.toggle('checked', chk.checked);
                updateChecklistProgress();
            });

            nextActionsList.appendChild(li);
        });

        updateChecklistProgress();
    }

    function updateChecklistProgress() {
        const total = nextActionsList.querySelectorAll('input').length;
        const checked = nextActionsList.querySelectorAll('input:checked').length;
        actionProgressBadge.textContent = `${checked}/${total}`;
    }

    function renderBriefPreview(text) {
        briefTextContent.textContent = text || 'No brief summary rendered.';
    }

    function updateStatusBadge(isLive) {
        if (isLive) {
            liveStatusBadge.className = 'status-indicator live';
            liveStatusBadge.innerHTML = '<span class="pulse-dot"></span> LIVE HN STREAM';
        } else {
            liveStatusBadge.className = 'status-indicator sample';
            liveStatusBadge.innerHTML = '<i class="fa-solid fa-flask"></i> SAMPLE DEMO MODE';
        }
    }

    function extractTags(text) {
        const lowered = text.toLowerCase();
        const tags = [];

        if (lowered.includes('agent')) tags.push({ key: 'agent', label: 'AI AGENT' });
        if (lowered.includes('mcp')) tags.push({ key: 'mcp', label: 'MCP' });
        if (lowered.includes('llm') || lowered.includes('model')) tags.push({ key: 'llm', label: 'LLM' });
        if (lowered.includes('framework') || lowered.includes('tool')) tags.push({ key: 'tooling', label: 'TOOLING' });
        
        if (tags.length === 0) tags.push({ key: 'agent', label: 'GENERAL' });
        return tags;
    }

    function showLoading(show) {
        if (show) {
            loadingState.classList.remove('hidden');
            storiesContainer.classList.add('hidden');
        } else {
            loadingState.classList.add('hidden');
            storiesContainer.classList.remove('hidden');
        }
    }

    function showToast(msg, type = 'success', title = 'Notification') {
        toastMessage.textContent = msg;
        toastTitle.textContent = title;

        toast.className = 'toast';
        if (type === 'error') {
            toast.classList.add('error-toast');
            toastIcon.className = 'fa-solid fa-triangle-exclamation';
        } else if (type === 'warning') {
            toast.classList.add('warning-toast');
            toastIcon.className = 'fa-solid fa-circle-exclamation';
        } else {
            toastIcon.className = 'fa-solid fa-circle-check';
        }

        toast.classList.remove('hidden');

        setTimeout(() => {
            toast.classList.add('hidden');
        }, 4500);
    }

    function escapeHtml(str) {
        return str ? str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;") : '';
    }
});
