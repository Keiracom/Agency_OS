/* ========================================
   Agency OS v3.0 - Application JavaScript
   ======================================== */

// Page Templates
const pages = {
    // ==================== DASHBOARD ====================
    dashboard: {
        title: 'Dashboard',
        breadcrumb: 'Monday, 22 December 2025',
        content: `
            <!-- AI Agents Status Bar -->
            <div class="agents-bar">
                <div class="agent-status">
                    <div class="agent-icon content">🤖</div>
                    <div class="agent-info">
                        <div class="agent-name">Content Agent</div>
                        <div class="agent-stats">247 messages generated today</div>
                    </div>
                </div>
                <div class="agent-status">
                    <div class="agent-icon reply">💬</div>
                    <div class="agent-info">
                        <div class="agent-name">Reply Agent</div>
                        <div class="agent-stats">34 replies classified • 8 responses sent</div>
                    </div>
                </div>
                <div class="agent-status" style="border-right: none;">
                    <div class="agent-icon cmo">🧠</div>
                    <div class="agent-info">
                        <div class="agent-name">CMO Agent</div>
                        <div class="agent-stats">3 campaigns optimized • 2 suggestions</div>
                    </div>
                </div>
            </div>

            <!-- Stats Row -->
            <div class="stats-row">
                <div class="stat-card">
                    <div class="stat-label">Active Leads</div>
                    <div class="stat-value">847</div>
                    <div class="stat-change up">↑ +12.5% this week</div>
                </div>
                <div class="stat-card success">
                    <div class="stat-label">Meetings Booked</div>
                    <div class="stat-value">34</div>
                    <div class="stat-change up">↑ +8 from last week</div>
                </div>
                <div class="stat-card warning">
                    <div class="stat-label">Response Rate</div>
                    <div class="stat-value">18.4%</div>
                    <div class="stat-change up">↑ +2.1% vs benchmark</div>
                </div>
                <div class="stat-card purple">
                    <div class="stat-label">Pipeline Value</div>
                    <div class="stat-value">$127K</div>
                    <div class="stat-change up">↑ +$34K this month</div>
                </div>
                <div class="stat-card orange">
                    <div class="stat-label">Avg YES Score</div>
                    <div class="stat-value">73</div>
                    <div class="stat-change up">↑ Above target (65)</div>
                </div>
            </div>

            <!-- Main Grid -->
            <div class="main-grid">
                <!-- Campaigns Panel -->
                <div class="panel">
                    <div class="panel-header">
                        <h2 class="panel-title">Active Campaigns</h2>
                        <div class="panel-actions">
                            <button class="btn">Filter</button>
                            <button class="btn btn-primary">+ New Campaign</button>
                        </div>
                    </div>
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Campaign</th>
                                <th>Mode</th>
                                <th>Channels</th>
                                <th>Progress</th>
                                <th>Leads</th>
                                <th>YES</th>
                                <th>Status</th>
                                <th>Mtgs</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td>
                                    <div style="display: flex; align-items: center; gap: 10px;">
                                        <div style="width: 28px; height: 28px; border-radius: 4px; background: rgba(18, 52, 153, 0.1); color: var(--primary); display: flex; align-items: center; justify-content: center;">✉</div>
                                        <div>
                                            <div style="font-weight: 500; font-size: 13px;">Sydney Digital Agencies</div>
                                            <div style="font-size: 10px; color: var(--text-muted);">$100K-500K MRR • Creative</div>
                                        </div>
                                    </div>
                                </td>
                                <td><span class="permission-badge auto">Auto</span></td>
                                <td>
                                    <div class="channel-pills">
                                        <div class="channel-pill email">✉</div>
                                        <div class="channel-pill linkedin">in</div>
                                        <div class="channel-pill sms">💬</div>
                                    </div>
                                </td>
                                <td>
                                    <div class="sequence-progress">
                                        <div class="sequence-step complete">1</div>
                                        <div class="sequence-step complete">2</div>
                                        <div class="sequence-step active">3</div>
                                        <div class="sequence-step pending">4</div>
                                    </div>
                                </td>
                                <td>234 / 1.2K</td>
                                <td>
                                    <div class="yes-score">
                                        <div class="yes-score-bar"><div class="yes-score-fill high" style="width: 82%"></div></div>
                                        <span class="yes-score-value">82</span>
                                    </div>
                                </td>
                                <td><span class="status-badge active">● Active</span></td>
                                <td><strong>12</strong></td>
                            </tr>
                            <tr>
                                <td>
                                    <div style="display: flex; align-items: center; gap: 10px;">
                                        <div style="width: 28px; height: 28px; border-radius: 4px; background: rgba(136, 108, 228, 0.1); color: var(--accent-purple); display: flex; align-items: center; justify-content: center;">📞</div>
                                        <div>
                                            <div style="font-weight: 500; font-size: 13px;">Melbourne Performance</div>
                                            <div style="font-size: 10px; color: var(--text-muted);">$50K-200K MRR • Performance</div>
                                        </div>
                                    </div>
                                </td>
                                <td><span class="permission-badge boss">Boss</span></td>
                                <td>
                                    <div class="channel-pills">
                                        <div class="channel-pill email">✉</div>
                                        <div class="channel-pill voice">📞</div>
                                        <div class="channel-pill mail">📬</div>
                                    </div>
                                </td>
                                <td>
                                    <div class="sequence-progress">
                                        <div class="sequence-step complete">1</div>
                                        <div class="sequence-step active">2</div>
                                        <div class="sequence-step pending">3</div>
                                        <div class="sequence-step pending">4</div>
                                    </div>
                                </td>
                                <td>189 / 850</td>
                                <td>
                                    <div class="yes-score">
                                        <div class="yes-score-bar"><div class="yes-score-fill high" style="width: 76%"></div></div>
                                        <span class="yes-score-value">76</span>
                                    </div>
                                </td>
                                <td><span class="status-badge active">● Active</span></td>
                                <td><strong>8</strong></td>
                            </tr>
                            <tr>
                                <td>
                                    <div style="display: flex; align-items: center; gap: 10px;">
                                        <div style="width: 28px; height: 28px; border-radius: 4px; background: rgba(0, 119, 181, 0.1); color: #0077b5; display: flex; align-items: center; justify-content: center;">in</div>
                                        <div>
                                            <div style="font-weight: 500; font-size: 13px;">Brisbane Full Service</div>
                                            <div style="font-size: 10px; color: var(--text-muted);">$200K+ MRR • Full Service</div>
                                        </div>
                                    </div>
                                </td>
                                <td><span class="permission-badge auto">Auto</span></td>
                                <td>
                                    <div class="channel-pills">
                                        <div class="channel-pill linkedin">in</div>
                                        <div class="channel-pill email">✉</div>
                                    </div>
                                </td>
                                <td>
                                    <div class="sequence-progress">
                                        <div class="sequence-step complete">1</div>
                                        <div class="sequence-step complete">2</div>
                                        <div class="sequence-step complete">3</div>
                                        <div class="sequence-step active">4</div>
                                    </div>
                                </td>
                                <td>67 / 320</td>
                                <td>
                                    <div class="yes-score">
                                        <div class="yes-score-bar"><div class="yes-score-fill medium" style="width: 68%"></div></div>
                                        <span class="yes-score-value">68</span>
                                    </div>
                                </td>
                                <td><span class="status-badge active">● Active</span></td>
                                <td><strong>6</strong></td>
                            </tr>
                            <tr>
                                <td>
                                    <div style="display: flex; align-items: center; gap: 10px;">
                                        <div style="width: 28px; height: 28px; border-radius: 4px; background: rgba(16, 124, 16, 0.1); color: var(--success); display: flex; align-items: center; justify-content: center;">💬</div>
                                        <div>
                                            <div style="font-weight: 500; font-size: 13px;">Perth Boutique Agencies</div>
                                            <div style="font-size: 10px; color: var(--text-muted);">$30K-100K MRR • Boutique</div>
                                        </div>
                                    </div>
                                </td>
                                <td><span class="permission-badge boss">Boss</span></td>
                                <td>
                                    <div class="channel-pills">
                                        <div class="channel-pill sms">💬</div>
                                        <div class="channel-pill email">✉</div>
                                        <div class="channel-pill voice">📞</div>
                                    </div>
                                </td>
                                <td>
                                    <div class="sequence-progress">
                                        <div class="sequence-step complete">1</div>
                                        <div class="sequence-step pending">2</div>
                                        <div class="sequence-step pending">3</div>
                                        <div class="sequence-step pending">4</div>
                                    </div>
                                </td>
                                <td>112 / 450</td>
                                <td>
                                    <div class="yes-score">
                                        <div class="yes-score-bar"><div class="yes-score-fill medium" style="width: 61%"></div></div>
                                        <span class="yes-score-value">61</span>
                                    </div>
                                </td>
                                <td><span class="status-badge paused">● Paused</span></td>
                                <td><strong>4</strong></td>
                            </tr>
                        </tbody>
                    </table>
                </div>

                <!-- Right Column -->
                <div style="display: flex; flex-direction: column; gap: 24px;">
                    <!-- Hot Leads -->
                    <div class="panel">
                        <div class="panel-header">
                            <h2 class="panel-title">🔥 Hot Leads</h2>
                            <button class="btn">View All</button>
                        </div>
                        <div class="panel-body">
                            <div class="lead-item">
                                <div class="lead-avatar">SM</div>
                                <div class="lead-info">
                                    <div class="lead-name">Sarah Mitchell</div>
                                    <div class="lead-company">Pixel & Co Digital • Sydney</div>
                                </div>
                                <div class="lead-score">
                                    <div class="lead-score-value">94</div>
                                    <div class="lead-score-label">YES Score</div>
                                </div>
                            </div>
                            <div class="lead-item">
                                <div class="lead-avatar">JK</div>
                                <div class="lead-info">
                                    <div class="lead-name">James Kirkwood</div>
                                    <div class="lead-company">Momentum Agency • Melbourne</div>
                                </div>
                                <div class="lead-score">
                                    <div class="lead-score-value">91</div>
                                    <div class="lead-score-label">YES Score</div>
                                </div>
                            </div>
                            <div class="lead-item">
                                <div class="lead-avatar">LT</div>
                                <div class="lead-info">
                                    <div class="lead-name">Lisa Tran</div>
                                    <div class="lead-company">Growth Labs • Brisbane</div>
                                </div>
                                <div class="lead-score">
                                    <div class="lead-score-value">88</div>
                                    <div class="lead-score-label">YES Score</div>
                                </div>
                            </div>
                            <div class="lead-item">
                                <div class="lead-avatar">MW</div>
                                <div class="lead-info">
                                    <div class="lead-name">Michael Wong</div>
                                    <div class="lead-company">Digital Edge • Perth</div>
                                </div>
                                <div class="lead-score">
                                    <div class="lead-score-value">85</div>
                                    <div class="lead-score-label">YES Score</div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Pipeline -->
                    <div class="panel">
                        <div class="panel-header">
                            <h2 class="panel-title">Pipeline Overview</h2>
                        </div>
                        <div class="panel-body">
                            <div class="pipeline-stages">
                                <div class="pipeline-stage">
                                    <div class="pipeline-count">847</div>
                                    <div class="pipeline-label">Leads</div>
                                </div>
                                <div class="pipeline-stage">
                                    <div class="pipeline-count">156</div>
                                    <div class="pipeline-label">Engaged</div>
                                </div>
                                <div class="pipeline-stage active">
                                    <div class="pipeline-count">34</div>
                                    <div class="pipeline-label">Meeting</div>
                                </div>
                                <div class="pipeline-stage">
                                    <div class="pipeline-count">12</div>
                                    <div class="pipeline-label">Proposal</div>
                                </div>
                                <div class="pipeline-stage">
                                    <div class="pipeline-count">4</div>
                                    <div class="pipeline-label">Closed</div>
                                </div>
                            </div>
                            <div style="display: flex; justify-content: space-between; padding-top: 12px; border-top: 1px solid var(--border);">
                                <div>
                                    <div style="font-size: 10px; color: var(--text-muted);">Weighted Pipeline</div>
                                    <div style="font-size: 20px; font-weight: 600; color: var(--primary);">$127,450</div>
                                </div>
                                <div style="text-align: right;">
                                    <div style="font-size: 10px; color: var(--text-muted);">Conversion Rate</div>
                                    <div style="font-size: 20px; font-weight: 600; color: var(--success);">4.0%</div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Deliverability Health -->
                    <div class="panel">
                        <div class="panel-header">
                            <h2 class="panel-title">Deliverability Health</h2>
                        </div>
                        <div class="panel-body">
                            <div class="compliance-grid">
                                <div class="compliance-item">
                                    <div class="compliance-value good">0.8%</div>
                                    <div class="compliance-label">Bounce Rate</div>
                                </div>
                                <div class="compliance-item">
                                    <div class="compliance-value good">0.1%</div>
                                    <div class="compliance-label">Spam Rate</div>
                                </div>
                                <div class="compliance-item">
                                    <div class="compliance-value warning">19</div>
                                    <div class="compliance-label">Unsubscribes</div>
                                </div>
                                <div class="compliance-item">
                                    <div class="compliance-value good">63%</div>
                                    <div class="compliance-label">LinkedIn Accept</div>
                                </div>
                            </div>
                            <div style="margin-top: 12px; padding: 10px; background: rgba(16, 124, 16, 0.05); border-radius: 4px; border: 1px solid rgba(16, 124, 16, 0.1);">
                                <div style="font-size: 11px; color: var(--success); font-weight: 500;">✓ All channels performing well</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Bottom Row -->
            <div class="bottom-row">
                <!-- Channel Performance -->
                <div class="panel">
                    <div class="panel-header">
                        <h2 class="panel-title">Channel Performance</h2>
                    </div>
                    <div class="panel-body">
                        <div class="channel-perf-item">
                            <div class="channel-perf-icon" style="background: rgba(18,52,153,0.1); color: var(--primary);">✉</div>
                            <div class="channel-perf-info">
                                <div class="channel-perf-name">Email</div>
                                <div class="channel-perf-stats">2,847 sent • 612 opened • 89 replies</div>
                            </div>
                            <div class="channel-perf-rate">
                                <div class="channel-perf-value">21.5%</div>
                                <div class="channel-perf-label">Open Rate</div>
                            </div>
                        </div>
                        <div class="channel-perf-item">
                            <div class="channel-perf-icon" style="background: rgba(0,119,181,0.1); color: #0077b5;">in</div>
                            <div class="channel-perf-info">
                                <div class="channel-perf-name">LinkedIn</div>
                                <div class="channel-perf-stats">456 requests • 289 accepted • 67 replies</div>
                            </div>
                            <div class="channel-perf-rate">
                                <div class="channel-perf-value">63.4%</div>
                                <div class="channel-perf-label">Accept Rate</div>
                            </div>
                        </div>
                        <div class="channel-perf-item">
                            <div class="channel-perf-icon" style="background: rgba(16,124,16,0.1); color: var(--success);">💬</div>
                            <div class="channel-perf-info">
                                <div class="channel-perf-name">SMS</div>
                                <div class="channel-perf-stats">523 sent • 47 replies</div>
                            </div>
                            <div class="channel-perf-rate">
                                <div class="channel-perf-value">9.0%</div>
                                <div class="channel-perf-label">Reply Rate</div>
                            </div>
                        </div>
                        <div class="channel-perf-item">
                            <div class="channel-perf-icon" style="background: rgba(136,108,228,0.1); color: var(--accent-purple);">📞</div>
                            <div class="channel-perf-info">
                                <div class="channel-perf-name">Voice AI</div>
                                <div class="channel-perf-stats">189 calls • 34 conversations</div>
                            </div>
                            <div class="channel-perf-rate">
                                <div class="channel-perf-value">18.0%</div>
                                <div class="channel-perf-label">Connect Rate</div>
                            </div>
                        </div>
                        <div class="channel-perf-item">
                            <div class="channel-perf-icon" style="background: rgba(247,99,12,0.1); color: var(--accent-orange);">📬</div>
                            <div class="channel-perf-info">
                                <div class="channel-perf-name">Direct Mail</div>
                                <div class="channel-perf-stats">85 sent • 12 QR scans</div>
                            </div>
                            <div class="channel-perf-rate">
                                <div class="channel-perf-value">14.1%</div>
                                <div class="channel-perf-label">Response Rate</div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Activity Feed -->
                <div class="panel">
                    <div class="panel-header">
                        <h2 class="panel-title">Recent Activity</h2>
                    </div>
                    <div class="panel-body">
                        <div class="activity-item">
                            <div class="activity-icon meeting">📅</div>
                            <div class="activity-content">
                                <div class="activity-text"><strong>Meeting booked</strong> with Sarah Mitchell @ Pixel & Co</div>
                                <div class="activity-meta">
                                    <span class="activity-time">2 min ago</span>
                                    <span class="activity-tag">YES: 94</span>
                                </div>
                            </div>
                        </div>
                        <div class="activity-item">
                            <div class="activity-icon ai">🤖</div>
                            <div class="activity-content">
                                <div class="activity-text"><strong>Reply Agent</strong> classified positive intent from James K.</div>
                                <div class="activity-meta">
                                    <span class="activity-time">8 min ago</span>
                                    <span class="activity-tag">Auto-responded</span>
                                </div>
                            </div>
                        </div>
                        <div class="activity-item">
                            <div class="activity-icon call">📞</div>
                            <div class="activity-content">
                                <div class="activity-text"><strong>Voice AI</strong> completed 4min call with Lisa Tran</div>
                                <div class="activity-meta">
                                    <span class="activity-time">32 min ago</span>
                                    <span class="activity-tag">Meeting requested</span>
                                </div>
                            </div>
                        </div>
                        <div class="activity-item">
                            <div class="activity-icon open">👁</div>
                            <div class="activity-content">
                                <div class="activity-text"><strong>Email opened 3x</strong> by Michael Wong</div>
                                <div class="activity-meta">
                                    <span class="activity-time">1 hr ago</span>
                                    <span class="activity-tag">Step 2 of 4</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Results -->
                <div class="panel">
                    <div class="panel-header">
                        <h2 class="panel-title">Results This Month</h2>
                    </div>
                    <div class="panel-body">
                        <div class="results-highlight">
                            <div class="results-value">34</div>
                            <div class="results-label">Meetings Booked</div>
                        </div>
                        <div class="results-metric">
                            <span class="results-metric-label">Deals Closed</span>
                            <span class="results-metric-value success">4</span>
                        </div>
                        <div class="results-metric">
                            <span class="results-metric-label">Revenue Generated</span>
                            <span class="results-metric-value success">$18,500</span>
                        </div>
                        <div class="results-metric">
                            <span class="results-metric-label">Proposals Sent</span>
                            <span class="results-metric-value">12</span>
                        </div>
                        <div class="results-metric">
                            <span class="results-metric-label">Avg Days to Meeting</span>
                            <span class="results-metric-value">4.2</span>
                        </div>
                        <div style="margin-top: 16px; padding: 12px; background: rgba(18, 52, 153, 0.05); border-radius: 4px;">
                            <div style="font-size: 10px; color: var(--text-muted); margin-bottom: 4px;">Pipeline Value</div>
                            <div style="font-size: 18px; font-weight: 600; color: var(--primary);">$127,450 <span style="font-size: 11px; color: var(--success); font-weight: 400;">↑ 36% MoM</span></div>
                        </div>
                    </div>
                </div>
            </div>
        `
    },

    // ==================== ANALYTICS ====================
    analytics: {
        title: 'Analytics',
        breadcrumb: 'Performance Insights',
        content: `
            <!-- Stats Row -->
            <div class="stats-row">
                <div class="stat-card">
                    <div class="stat-label">Total Outreach</div>
                    <div class="stat-value">4,100</div>
                    <div class="stat-change up">↑ +18% this month</div>
                </div>
                <div class="stat-card success">
                    <div class="stat-label">Total Responses</div>
                    <div class="stat-value">312</div>
                    <div class="stat-change up">↑ +24% this month</div>
                </div>
                <div class="stat-card warning">
                    <div class="stat-label">Avg Response Time</div>
                    <div class="stat-value">2.4h</div>
                    <div class="stat-change up">↓ -1.2h improvement</div>
                </div>
                <div class="stat-card purple">
                    <div class="stat-label">Meeting Rate</div>
                    <div class="stat-value">4.0%</div>
                    <div class="stat-change up">↑ +0.8% this month</div>
                </div>
                <div class="stat-card orange">
                    <div class="stat-label">Close Rate</div>
                    <div class="stat-value">12%</div>
                    <div class="stat-change up">↑ +2% this month</div>
                </div>
            </div>

            <!-- Tabs -->
            <div class="tabs">
                <div class="tab active">Overview</div>
                <div class="tab">By Campaign</div>
                <div class="tab">By Channel</div>
                <div class="tab">By Time</div>
            </div>

            <div class="two-column">
                <!-- Response Trend -->
                <div class="panel">
                    <div class="panel-header">
                        <h2 class="panel-title">Response Trend (30 Days)</h2>
                    </div>
                    <div class="panel-body">
                        <div class="chart-placeholder" style="height: 250px;">
                            📈 Response rate chart would render here<br>
                            <small style="color: var(--text-muted);">Showing daily responses over time</small>
                        </div>
                    </div>
                </div>

                <!-- Channel Comparison -->
                <div class="panel">
                    <div class="panel-header">
                        <h2 class="panel-title">Channel Comparison</h2>
                    </div>
                    <div class="panel-body">
                        <div class="chart-placeholder" style="height: 250px;">
                            📊 Bar chart comparing channel performance<br>
                            <small style="color: var(--text-muted);">Email vs LinkedIn vs SMS vs Voice vs Mail</small>
                        </div>
                    </div>
                </div>
            </div>

            <div class="two-column" style="margin-top: 24px;">
                <!-- Best Performing Campaigns -->
                <div class="panel">
                    <div class="panel-header">
                        <h2 class="panel-title">Top Performing Campaigns</h2>
                    </div>
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Campaign</th>
                                <th>Response Rate</th>
                                <th>Meetings</th>
                                <th>Trend</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td style="font-weight: 500;">Sydney Digital Agencies</td>
                                <td>24.3%</td>
                                <td>12</td>
                                <td><span style="color: var(--success);">↑ +3.2%</span></td>
                            </tr>
                            <tr>
                                <td style="font-weight: 500;">Enterprise Re-engagement</td>
                                <td>22.1%</td>
                                <td>4</td>
                                <td><span style="color: var(--success);">↑ +5.1%</span></td>
                            </tr>
                            <tr>
                                <td style="font-weight: 500;">Melbourne Performance</td>
                                <td>18.7%</td>
                                <td>8</td>
                                <td><span style="color: var(--success);">↑ +1.4%</span></td>
                            </tr>
                            <tr>
                                <td style="font-weight: 500;">Brisbane Full Service</td>
                                <td>15.2%</td>
                                <td>6</td>
                                <td><span style="color: var(--warning);">→ +0.2%</span></td>
                            </tr>
                        </tbody>
                    </table>
                </div>

                <!-- Best Times -->
                <div class="panel">
                    <div class="panel-header">
                        <h2 class="panel-title">Best Send Times</h2>
                    </div>
                    <div class="panel-body">
                        <div style="margin-bottom: 16px;">
                            <div style="font-size: 12px; font-weight: 500; margin-bottom: 8px;">🏆 Top Performing Hours</div>
                            <div style="display: flex; gap: 8px;">
                                <div style="padding: 12px 20px; background: rgba(16, 124, 16, 0.1); border-radius: 4px; text-align: center;">
                                    <div style="font-size: 18px; font-weight: 600; color: var(--success);">9-10am</div>
                                    <div style="font-size: 10px; color: var(--text-muted);">32% open rate</div>
                                </div>
                                <div style="padding: 12px 20px; background: rgba(18, 52, 153, 0.1); border-radius: 4px; text-align: center;">
                                    <div style="font-size: 18px; font-weight: 600; color: var(--primary);">2-3pm</div>
                                    <div style="font-size: 10px; color: var(--text-muted);">28% open rate</div>
                                </div>
                                <div style="padding: 12px 20px; background: rgba(136, 108, 228, 0.1); border-radius: 4px; text-align: center;">
                                    <div style="font-size: 18px; font-weight: 600; color: var(--accent-purple);">7-8am</div>
                                    <div style="font-size: 10px; color: var(--text-muted);">25% open rate</div>
                                </div>
                            </div>
                        </div>
                        <div>
                            <div style="font-size: 12px; font-weight: 500; margin-bottom: 8px;">📅 Best Days</div>
                            <div style="display: flex; gap: 8px;">
                                <span class="status-badge active">Tuesday</span>
                                <span class="status-badge active">Wednesday</span>
                                <span class="status-badge pending">Thursday</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `
    },

    // ==================== CAMPAIGNS ====================
    campaigns: {
        title: 'Campaigns',
        breadcrumb: '12 Active Campaigns',
        content: `
            <!-- Filters Bar -->
            <div class="filters-bar">
                <div class="filter-group">
                    <span class="filter-label">Status:</span>
                    <select class="filter-select">
                        <option>All</option>
                        <option selected>Active</option>
                        <option>Paused</option>
                        <option>Draft</option>
                    </select>
                </div>
                <div class="filter-group">
                    <span class="filter-label">Channel:</span>
                    <select class="filter-select">
                        <option>All Channels</option>
                        <option>Email</option>
                        <option>LinkedIn</option>
                        <option>SMS</option>
                        <option>Voice AI</option>
                        <option>Direct Mail</option>
                    </select>
                </div>
                <div class="filter-group">
                    <span class="filter-label">Mode:</span>
                    <select class="filter-select">
                        <option>All</option>
                        <option>Auto Pilot</option>
                        <option>Boss Mode</option>
                    </select>
                </div>
                <div style="margin-left: auto;">
                    <button class="btn btn-primary">+ Create Campaign</button>
                </div>
            </div>

            <!-- Campaigns Table -->
            <div class="panel">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Campaign</th>
                            <th>Mode</th>
                            <th>Channels</th>
                            <th>Progress</th>
                            <th>Leads</th>
                            <th>Sent</th>
                            <th>Responses</th>
                            <th>YES Score</th>
                            <th>Meetings</th>
                            <th>Status</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>
                                <div style="display: flex; align-items: center; gap: 10px;">
                                    <div style="width: 32px; height: 32px; border-radius: 4px; background: rgba(18, 52, 153, 0.1); color: var(--primary); display: flex; align-items: center; justify-content: center;">✉</div>
                                    <div>
                                        <div style="font-weight: 500;">Sydney Digital Agencies</div>
                                        <div style="font-size: 10px; color: var(--text-muted);">$100K-500K MRR • Creative</div>
                                    </div>
                                </div>
                            </td>
                            <td><span class="permission-badge auto">Auto</span></td>
                            <td>
                                <div class="channel-pills">
                                    <div class="channel-pill email">✉</div>
                                    <div class="channel-pill linkedin">in</div>
                                    <div class="channel-pill sms">💬</div>
                                </div>
                            </td>
                            <td>
                                <div class="sequence-progress">
                                    <div class="sequence-step complete">1</div>
                                    <div class="sequence-step complete">2</div>
                                    <div class="sequence-step active">3</div>
                                    <div class="sequence-step pending">4</div>
                                </div>
                            </td>
                            <td>1,200</td>
                            <td>2,847</td>
                            <td>89 (3.1%)</td>
                            <td>
                                <div class="yes-score">
                                    <div class="yes-score-bar"><div class="yes-score-fill high" style="width: 82%"></div></div>
                                    <span class="yes-score-value">82</span>
                                </div>
                            </td>
                            <td><strong>12</strong></td>
                            <td><span class="status-badge active">● Active</span></td>
                            <td>
                                <button class="btn" style="padding: 4px 8px;">⚙️</button>
                            </td>
                        </tr>
                        <tr>
                            <td>
                                <div style="display: flex; align-items: center; gap: 10px;">
                                    <div style="width: 32px; height: 32px; border-radius: 4px; background: rgba(136, 108, 228, 0.1); color: var(--accent-purple); display: flex; align-items: center; justify-content: center;">📞</div>
                                    <div>
                                        <div style="font-weight: 500;">Melbourne Performance</div>
                                        <div style="font-size: 10px; color: var(--text-muted);">$50K-200K MRR • Performance</div>
                                    </div>
                                </div>
                            </td>
                            <td><span class="permission-badge boss">Boss</span></td>
                            <td>
                                <div class="channel-pills">
                                    <div class="channel-pill email">✉</div>
                                    <div class="channel-pill voice">📞</div>
                                    <div class="channel-pill mail">📬</div>
                                </div>
                            </td>
                            <td>
                                <div class="sequence-progress">
                                    <div class="sequence-step complete">1</div>
                                    <div class="sequence-step active">2</div>
                                    <div class="sequence-step pending">3</div>
                                    <div class="sequence-step pending">4</div>
                                </div>
                            </td>
                            <td>850</td>
                            <td>1,523</td>
                            <td>67 (4.4%)</td>
                            <td>
                                <div class="yes-score">
                                    <div class="yes-score-bar"><div class="yes-score-fill high" style="width: 76%"></div></div>
                                    <span class="yes-score-value">76</span>
                                </div>
                            </td>
                            <td><strong>8</strong></td>
                            <td><span class="status-badge active">● Active</span></td>
                            <td>
                                <button class="btn" style="padding: 4px 8px;">⚙️</button>
                            </td>
                        </tr>
                        <tr>
                            <td>
                                <div style="display: flex; align-items: center; gap: 10px;">
                                    <div style="width: 32px; height: 32px; border-radius: 4px; background: rgba(0, 119, 181, 0.1); color: #0077b5; display: flex; align-items: center; justify-content: center;">in</div>
                                    <div>
                                        <div style="font-weight: 500;">Brisbane Full Service</div>
                                        <div style="font-size: 10px; color: var(--text-muted);">$200K+ MRR • Full Service</div>
                                    </div>
                                </div>
                            </td>
                            <td><span class="permission-badge auto">Auto</span></td>
                            <td>
                                <div class="channel-pills">
                                    <div class="channel-pill linkedin">in</div>
                                    <div class="channel-pill email">✉</div>
                                </div>
                            </td>
                            <td>
                                <div class="sequence-progress">
                                    <div class="sequence-step complete">1</div>
                                    <div class="sequence-step complete">2</div>
                                    <div class="sequence-step complete">3</div>
                                    <div class="sequence-step active">4</div>
                                </div>
                            </td>
                            <td>320</td>
                            <td>892</td>
                            <td>34 (3.8%)</td>
                            <td>
                                <div class="yes-score">
                                    <div class="yes-score-bar"><div class="yes-score-fill medium" style="width: 68%"></div></div>
                                    <span class="yes-score-value">68</span>
                                </div>
                            </td>
                            <td><strong>6</strong></td>
                            <td><span class="status-badge active">● Active</span></td>
                            <td>
                                <button class="btn" style="padding: 4px 8px;">⚙️</button>
                            </td>
                        </tr>
                        <tr>
                            <td>
                                <div style="display: flex; align-items: center; gap: 10px;">
                                    <div style="width: 32px; height: 32px; border-radius: 4px; background: rgba(16, 124, 16, 0.1); color: var(--success); display: flex; align-items: center; justify-content: center;">💬</div>
                                    <div>
                                        <div style="font-weight: 500;">Perth Boutique Agencies</div>
                                        <div style="font-size: 10px; color: var(--text-muted);">$30K-100K MRR • Boutique</div>
                                    </div>
                                </div>
                            </td>
                            <td><span class="permission-badge boss">Boss</span></td>
                            <td>
                                <div class="channel-pills">
                                    <div class="channel-pill sms">💬</div>
                                    <div class="channel-pill email">✉</div>
                                    <div class="channel-pill voice">📞</div>
                                </div>
                            </td>
                            <td>
                                <div class="sequence-progress">
                                    <div class="sequence-step complete">1</div>
                                    <div class="sequence-step pending">2</div>
                                    <div class="sequence-step pending">3</div>
                                    <div class="sequence-step pending">4</div>
                                </div>
                            </td>
                            <td>450</td>
                            <td>523</td>
                            <td>21 (4.0%)</td>
                            <td>
                                <div class="yes-score">
                                    <div class="yes-score-bar"><div class="yes-score-fill medium" style="width: 61%"></div></div>
                                    <span class="yes-score-value">61</span>
                                </div>
                            </td>
                            <td><strong>4</strong></td>
                            <td><span class="status-badge paused">● Paused</span></td>
                            <td>
                                <button class="btn" style="padding: 4px 8px;">⚙️</button>
                            </td>
                        </tr>
                        <tr>
                            <td>
                                <div style="display: flex; align-items: center; gap: 10px;">
                                    <div style="width: 32px; height: 32px; border-radius: 4px; background: rgba(247, 99, 12, 0.1); color: var(--accent-orange); display: flex; align-items: center; justify-content: center;">📬</div>
                                    <div>
                                        <div style="font-weight: 500;">Enterprise Re-engagement</div>
                                        <div style="font-size: 10px; color: var(--text-muted);">$500K+ MRR • Enterprise</div>
                                    </div>
                                </div>
                            </td>
                            <td><span class="permission-badge auto">Auto</span></td>
                            <td>
                                <div class="channel-pills">
                                    <div class="channel-pill mail">📬</div>
                                    <div class="channel-pill email">✉</div>
                                    <div class="channel-pill linkedin">in</div>
                                    <div class="channel-pill voice">📞</div>
                                </div>
                            </td>
                            <td>
                                <div class="sequence-progress">
                                    <div class="sequence-step complete">1</div>
                                    <div class="sequence-step complete">2</div>
                                    <div class="sequence-step active">3</div>
                                    <div class="sequence-step pending">4</div>
                                </div>
                            </td>
                            <td>85</td>
                            <td>312</td>
                            <td>19 (6.1%)</td>
                            <td>
                                <div class="yes-score">
                                    <div class="yes-score-bar"><div class="yes-score-fill high" style="width: 89%"></div></div>
                                    <span class="yes-score-value">89</span>
                                </div>
                            </td>
                            <td><strong>4</strong></td>
                            <td><span class="status-badge active">● Active</span></td>
                            <td>
                                <button class="btn" style="padding: 4px 8px;">⚙️</button>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        `
    },
Engaged</span></td>
                            <td><button class="btn" style="padding: 4px 8px;">View</button></td>
                        </tr>
                        <tr>
                            <td><input type="checkbox"></td>
                            <td>
                                <div style="display: flex; align-items: center; gap: 10px;">
                                    <div class="lead-avatar">LT</div>
                                    <div>
                                        <div style="font-weight: 500;">Lisa Tran</div>
                                        <div style="font-size: 10px; color: var(--text-muted);">Founder</div>
                                    </div>
                                </div>
                            </td>
                            <td>
                                <div style="font-weight: 500;">Growth Labs</div>
                                <div style="font-size: 10px; color: var(--text-muted);">Brisbane • $95K MRR</div>
                            </td>
                            <td>Brisbane Full Service</td>
                            <td>
                                <div class="yes-score">
                                    <div class="yes-score-bar"><div class="yes-score-fill high" style="width: 88%"></div></div>
                                    <span class="yes-score-value">88</span>
                                </div>
                            </td>
                            <td>
                                <div class="sequence-progress">
                                    <div class="sequence-step complete">1</div>
                                    <div class="sequence-step complete">2</div>
                                    <div class="sequence-step active">3</div>
                                    <div class="sequence-step pending">4</div>
                                </div>
                            </td>
                            <td>
                                <div style="font-size: 11px;">Voice call completed</div>
                                <div style="font-size: 10px; color: var(--text-muted);">32 min ago</div>
                            </td>
                            <td><span class="status-badge active">Engaged</span></td>
                            <td><button class="btn" style="padding: 4px 8px;">View</button></td>
                        </tr>
                        <tr>
                            <td><input type="checkbox"></td>
                            <td>
                                <div style="display: flex; align-items: center; gap: 10px;">
                                    <div class="lead-avatar">MW</div>
                                    <div>
                                        <div style="font-weight: 500;">Michael Wong</div>
                                        <div style="font-size: 10px; color: var(--text-muted);">Director</div>
                                    </div>
                                </div>
                            </td>
                            <td>
                                <div style="font-weight: 500;">Digital Edge</div>
                                <div style="font-size: 10px; color: var(--text-muted);">Perth • $75K MRR</div>
                            </td>
                            <td>Perth Boutique</td>
                            <td>
                                <div class="yes-score">
                                    <div class="yes-score-bar"><div class="yes-score-fill high" style="width: 85%"></div></div>
                                    <span class="yes-score-value">85</span>
                                </div>
                            </td>
                            <td>
                                <div class="sequence-progress">
                                    <div class="sequence-step complete">1</div>
                                    <div class="sequence-step active">2</div>
                                    <div class="sequence-step pending">3</div>
                                    <div class="sequence-step pending">4</div>
                                </div>
                            </td>
                            <td>
                                <div style="font-size: 11px;">Email opened 3x</div>
                                <div style="font-size: 10px; color: var(--text-muted);">1 hr ago</div>
                            </td>
                            <td><span class="status-badge pending">Contacted</span></td>
                            <td><button class="btn" style="padding: 4px 8px;">View</button></td>
                        </tr>
                        <tr>
                            <td><input type="checkbox"></td>
                            <td>
                                <div style="display: flex; align-items: center; gap: 10px;">
                                    <div class="lead-avatar">BH</div>
                                    <div>
                                        <div style="font-weight: 500;">Ben Harper</div>
                                        <div style="font-size: 10px; color: var(--text-muted);">CEO</div>
                                    </div>
                                </div>
                            </td>
                            <td>
                                <div style="font-weight: 500;">Harper Media Group</div>
                                <div style="font-size: 10px; color: var(--text-muted);">Sydney • $520K MRR</div>
                            </td>
                            <td>Enterprise Re-engagement</td>
                            <td>
                                <div class="yes-score">
                                    <div class="yes-score-bar"><div class="yes-score-fill high" style="width: 92%"></div></div>
                                    <span class="yes-score-value">92</span>
                                </div>
                            </td>
                            <td>
                                <div class="sequence-progress">
                                    <div class="sequence-step complete">1</div>
                                    <div class="sequence-step complete">2</div>
                                    <div class="sequence-step active">3</div>
                                    <div class="sequence-step pending">4</div>
                                </div>
                            </td>
                            <td>
                                <div style="font-size: 11px;">QR code scanned</div>
                                <div style="font-size: 10px; color: var(--text-muted);">2 hrs ago</div>
                            </td>
                            <td><span class="status-badge active">Engaged</span></td>
                            <td><button class="btn" style="padding: 4px 8px;">View</button></td>
                        </tr>
                    </tbody>
                </table>
                <div style="padding: 16px; display: flex; justify-content: space-between; align-items: center; border-top: 1px solid var(--border);">
                    <span style="font-size: 12px; color: var(--text-muted);">Showing 1-5 of 847 leads</span>
                    <div style="display: flex; gap: 8px;">
                        <button class="btn" disabled>Previous</button>
                        <button class="btn">Next</button>
                    </div>
                </div>
            </div>
        `
    },

    // ==================== EMAIL ====================
    email: {
        title: 'Email Channel',
        breadcrumb: '2,847 emails sent this month',
        content: `
            <!-- Stats Row -->
            <div class="stats-row">
                <div class="stat-card">
                    <div class="stat-label">Emails Sent</div>
                    <div class="stat-value">2,847</div>
                    <div class="stat-change up">↑ +342 today</div>
                </div>
                <div class="stat-card success">
                    <div class="stat-label">Open Rate</div>
                    <div class="stat-value">21.5%</div>
                    <div class="stat-change up">↑ +2.3% vs avg</div>
                </div>
                <div class="stat-card warning">
                    <div class="stat-label">Reply Rate</div>
                    <div class="stat-value">3.1%</div>
                    <div class="stat-change up">↑ +0.4% vs avg</div>
                </div>
                <div class="stat-card purple">
                    <div class="stat-label">Positive Replies</div>
                    <div class="stat-value">89</div>
                    <div class="stat-change up">↑ +12 this week</div>
                </div>
                <div class="stat-card orange">
                    <div class="stat-label">Meetings</div>
                    <div class="stat-value">23</div>
                    <div class="stat-change up">↑ From email channel</div>
                </div>
            </div>

            <div class="two-column">
                <!-- Recent Emails -->
                <div class="panel">
                    <div class="panel-header">
                        <h2 class="panel-title">Recent Email Activity</h2>
                        <button class="btn">View All</button>
                    </div>
                    <div class="panel-body" style="padding: 0;">
                        <div class="activity-item" style="padding: 16px;">
                            <div class="activity-icon email">✉</div>
                            <div class="activity-content">
                                <div class="activity-text"><strong>Sarah Mitchell</strong> opened email 3x</div>
                                <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">Subject: "Quick question about your client acquisition..."</div>
                                <div class="activity-meta">
                                    <span class="activity-time">5 min ago</span>
                                    <span class="activity-tag">Step 3</span>
                                </div>
                            </div>
                        </div>
                        <div class="activity-item" style="padding: 16px;">
                            <div class="activity-icon reply">↩</div>
                            <div class="activity-content">
                                <div class="activity-text"><strong>James Kirkwood</strong> replied positively</div>
                                <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">"Thanks for reaching out, I'd be interested in learning more..."</div>
                                <div class="activity-meta">
                                    <span class="activity-time">12 min ago</span>
                                    <span class="activity-tag">Auto-responded</span>
                                </div>
                            </div>
                        </div>
                        <div class="activity-item" style="padding: 16px;">
                            <div class="activity-icon email">✉</div>
                            <div class="activity-content">
                                <div class="activity-text"><strong>47 emails</strong> sent in batch</div>
                                <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">Sydney Digital Agencies - Step 2</div>
                                <div class="activity-meta">
                                    <span class="activity-time">1 hr ago</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Deliverability -->
                <div class="panel">
                    <div class="panel-header">
                        <h2 class="panel-title">Deliverability Health</h2>
                    </div>
                    <div class="panel-body">
                        <div class="compliance-grid">
                            <div class="compliance-item">
                                <div class="compliance-value good">0.8%</div>
                                <div class="compliance-label">Bounce Rate</div>
                            </div>
                            <div class="compliance-item">
                                <div class="compliance-value good">0.1%</div>
                                <div class="compliance-label">Spam Rate</div>
                            </div>
                            <div class="compliance-item">
                                <div class="compliance-value warning">19</div>
                                <div class="compliance-label">Unsubscribes</div>
                            </div>
                            <div class="compliance-item">
                                <div class="compliance-value good">98.2%</div>
                                <div class="compliance-label">Delivery Rate</div>
                            </div>
                        </div>
                        <div style="margin-top: 16px; padding: 12px; background: rgba(16, 124, 16, 0.05); border-radius: 4px;">
                            <div style="font-size: 11px; color: var(--success); font-weight: 500;">✓ All email metrics healthy</div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Email Templates -->
            <div class="panel" style="margin-top: 24px;">
                <div class="panel-header">
                    <h2 class="panel-title">Active Email Sequences</h2>
                    <button class="btn btn-primary">+ New Sequence</button>
                </div>
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Sequence</th>
                            <th>Campaign</th>
                            <th>Steps</th>
                            <th>Active Leads</th>
                            <th>Open Rate</th>
                            <th>Reply Rate</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td style="font-weight: 500;">Creative Agency Outreach v2</td>
                            <td>Sydney Digital</td>
                            <td>4 emails</td>
                            <td>234</td>
                            <td><span style="color: var(--success);">24.3%</span></td>
                            <td><span style="color: var(--success);">3.8%</span></td>
                            <td><span class="status-badge active">● Active</span></td>
                        </tr>
                        <tr>
                            <td style="font-weight: 500;">Performance Agency Intro</td>
                            <td>Melbourne Performance</td>
                            <td>4 emails</td>
                            <td>189</td>
                            <td><span style="color: var(--success);">21.1%</span></td>
                            <td><span style="color: var(--warning);">2.9%</span></td>
                            <td><span class="status-badge active">● Active</span></td>
                        </tr>
                        <tr>
                            <td style="font-weight: 500;">Enterprise Follow-up</td>
                            <td>Enterprise Re-engagement</td>
                            <td>3 emails</td>
                            <td>23</td>
                            <td><span style="color: var(--success);">32.1%</span></td>
                            <td><span style="color: var(--success);">6.2%</span></td>
                            <td><span class="status-badge active">● Active</span></td>
                        </tr>
                    </tbody>
                </table>
            </div>
        `
    },

    // ==================== LINKEDIN ====================
    linkedin: {
        title: 'LinkedIn Channel',
        breadcrumb: '456 connection requests this month',
        content: `
            <!-- Stats Row -->
            <div class="stats-row">
                <div class="stat-card">
                    <div class="stat-label">Requests Sent</div>
                    <div class="stat-value">456</div>
                    <div class="stat-change up">↑ +52 today</div>
                </div>
                <div class="stat-card success">
                    <div class="stat-label">Accept Rate</div>
                    <div class="stat-value">63.4%</div>
                    <div class="stat-change up">↑ +8.2% vs avg</div>
                </div>
                <div class="stat-card warning">
                    <div class="stat-label">Reply Rate</div>
                    <div class="stat-value">23.2%</div>
                    <div class="stat-change up">↑ +4.1% vs avg</div>
                </div>
                <div class="stat-card purple">
                    <div class="stat-label">Conversations</div>
                    <div class="stat-value">67</div>
                    <div class="stat-change up">↑ Active threads</div>
                </div>
                <div class="stat-card orange">
                    <div class="stat-label">Meetings</div>
                    <div class="stat-value">8</div>
                    <div class="stat-change up">↑ From LinkedIn</div>
                </div>
            </div>

            <div class="two-column">
                <!-- Recent Activity -->
                <div class="panel">
                    <div class="panel-header">
                        <h2 class="panel-title">Recent LinkedIn Activity</h2>
                    </div>
                    <div class="panel-body" style="padding: 0;">
                        <div class="activity-item" style="padding: 16px;">
                            <div class="activity-icon linkedin">in</div>
                            <div class="activity-content">
                                <div class="activity-text"><strong>Sarah Mitchell</strong> accepted connection</div>
                                <div class="activity-meta">
                                    <span class="activity-time">3 min ago</span>
                                    <span class="activity-tag">Auto-messaged</span>
                                </div>
                            </div>
                        </div>
                        <div class="activity-item" style="padding: 16px;">
                            <div class="activity-icon reply">💬</div>
                            <div class="activity-content">
                                <div class="activity-text"><strong>Tom Richards</strong> replied to message</div>
                                <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">"Thanks for connecting! Would love to hear more..."</div>
                                <div class="activity-meta">
                                    <span class="activity-time">15 min ago</span>
                                </div>
                            </div>
                        </div>
                        <div class="activity-item" style="padding: 16px;">
                            <div class="activity-icon linkedin">in</div>
                            <div class="activity-content">
                                <div class="activity-text"><strong>12 connection requests</strong> sent</div>
                                <div class="activity-meta">
                                    <span class="activity-time">1 hr ago</span>
                                    <span class="activity-tag">Brisbane Campaign</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Account Health -->
                <div class="panel">
                    <div class="panel-header">
                        <h2 class="panel-title">Account Health</h2>
                    </div>
                    <div class="panel-body">
                        <div class="compliance-grid">
                            <div class="compliance-item">
                                <div class="compliance-value good">63%</div>
                                <div class="compliance-label">Accept Rate</div>
                            </div>
                            <div class="compliance-item">
                                <div class="compliance-value good">42/100</div>
                                <div class="compliance-label">Daily Limit</div>
                            </div>
                            <div class="compliance-item">
                                <div class="compliance-value good">0</div>
                                <div class="compliance-label">Warnings</div>
                            </div>
                            <div class="compliance-item">
                                <div class="compliance-value good">Active</div>
                                <div class="compliance-label">Account Status</div>
                            </div>
                        </div>
                        <div style="margin-top: 16px; padding: 12px; background: rgba(16, 124, 16, 0.05); border-radius: 4px;">
                            <div style="font-size: 11px; color: var(--success); font-weight: 500;">✓ LinkedIn account in good standing</div>
                        </div>
                    </div>
                </div>
            </div>
        `
    },

    // ==================== SMS ====================
    sms: {
        title: 'SMS Channel',
        breadcrumb: '523 messages sent this month',
        content: `
            <!-- Stats Row -->
            <div class="stats-row">
                <div class="stat-card">
                    <div class="stat-label">SMS Sent</div>
                    <div class="stat-value">523</div>
                    <div class="stat-change up">↑ +67 today</div>
                </div>
                <div class="stat-card success">
                    <div class="stat-label">Delivery Rate</div>
                    <div class="stat-value">98.1%</div>
                    <div class="stat-change up">↑ Excellent</div>
                </div>
                <div class="stat-card warning">
                    <div class="stat-label">Reply Rate</div>
                    <div class="stat-value">9.0%</div>
                    <div class="stat-change up">↑ +1.2% vs avg</div>
                </div>
                <div class="stat-card purple">
                    <div class="stat-label">Replies</div>
                    <div class="stat-value">47</div>
                    <div class="stat-change up">↑ +8 today</div>
                </div>
                <div class="stat-card orange">
                    <div class="stat-label">Opt-outs</div>
                    <div class="stat-value">3</div>
                    <div class="stat-change up">0.6% rate</div>
                </div>
            </div>

            <div class="two-column">
                <!-- Recent SMS -->
                <div class="panel">
                    <div class="panel-header">
                        <h2 class="panel-title">Recent SMS Activity</h2>
                    </div>
                    <div class="panel-body" style="padding: 0;">
                        <div class="activity-item" style="padding: 16px;">
                            <div class="activity-icon sms">💬</div>
                            <div class="activity-content">
                                <div class="activity-text"><strong>Lisa Tran</strong> replied</div>
                                <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">"Yes, I'm available Thursday afternoon"</div>
                                <div class="activity-meta">
                                    <span class="activity-time">5 min ago</span>
                                    <span class="activity-tag">Positive</span>
                                </div>
                            </div>
                        </div>
                        <div class="activity-item" style="padding: 16px;">
                            <div class="activity-icon sms">💬</div>
                            <div class="activity-content">
                                <div class="activity-text"><strong>23 SMS</strong> sent in batch</div>
                                <div class="activity-meta">
                                    <span class="activity-time">30 min ago</span>
                                    <span class="activity-tag">Perth Campaign</span>
                                </div>
                            </div>
                        </div>
                        <div class="activity-item" style="padding: 16px;">
                            <div class="activity-icon reply">↩</div>
                            <div class="activity-content">
                                <div class="activity-text"><strong>Michael Wong</strong> replied</div>
                                <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">"Send me more info please"</div>
                                <div class="activity-meta">
                                    <span class="activity-time">1 hr ago</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- SMS Health -->
                <div class="panel">
                    <div class="panel-header">
                        <h2 class="panel-title">SMS Health</h2>
                    </div>
                    <div class="panel-body">
                        <div class="compliance-grid">
                            <div class="compliance-item">
                                <div class="compliance-value good">98.1%</div>
                                <div class="compliance-label">Delivery Rate</div>
                            </div>
                            <div class="compliance-item">
                                <div class="compliance-value good">0.6%</div>
                                <div class="compliance-label">Opt-out Rate</div>
                            </div>
                            <div class="compliance-item">
                                <div class="compliance-value good">0</div>
                                <div class="compliance-label">Carrier Blocks</div>
                            </div>
                            <div class="compliance-item">
                                <div class="compliance-value good">Active</div>
                                <div class="compliance-label">Number Status</div>
                            </div>
                        </div>
                        <div style="margin-top: 16px; padding: 12px; background: rgba(16, 124, 16, 0.05); border-radius: 4px;">
                            <div style="font-size: 11px; color: var(--success); font-weight: 500;">✓ SMS channel performing well</div>
                        </div>
                    </div>
                </div>
            </div>
        `
    },

    // ==================== VOICE AI ====================
    voice: {
        title: 'Voice AI Channel',
        breadcrumb: '189 calls this month',
        content: `
            <!-- Stats Row -->
            <div class="stats-row">
                <div class="stat-card">
                    <div class="stat-label">Calls Made</div>
                    <div class="stat-value">189</div>
                    <div class="stat-change up">↑ +24 today</div>
                </div>
                <div class="stat-card success">
                    <div class="stat-label">Connect Rate</div>
                    <div class="stat-value">18.0%</div>
                    <div class="stat-change up">↑ +2.1% vs avg</div>
                </div>
                <div class="stat-card warning">
                    <div class="stat-label">Avg Duration</div>
                    <div class="stat-value">3.2m</div>
                    <div class="stat-change up">Good engagement</div>
                </div>
                <div class="stat-card purple">
                    <div class="stat-label">Conversations</div>
                    <div class="stat-value">34</div>
                    <div class="stat-change up">↑ +6 today</div>
                </div>
                <div class="stat-card orange">
                    <div class="stat-label">Interested</div>
                    <div class="stat-value">12</div>
                    <div class="stat-change up">35% of connects</div>
                </div>
            </div>

            <div class="two-column">
                <!-- Recent Calls -->
                <div class="panel">
                    <div class="panel-header">
                        <h2 class="panel-title">Recent Voice AI Calls</h2>
                    </div>
                    <div class="panel-body" style="padding: 0;">
                        <div class="activity-item" style="padding: 16px;">
                            <div class="activity-icon call">📞</div>
                            <div class="activity-content">
                                <div class="activity-text"><strong>Lisa Tran</strong> - 4 min call</div>
                                <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">Outcome: Interested - Meeting requested</div>
                                <div class="activity-meta">
                                    <span class="activity-time">32 min ago</span>
                                    <span class="activity-tag" style="background: rgba(16, 124, 16, 0.1); color: var(--success);">Positive</span>
                                </div>
                            </div>
                        </div>
                        <div class="activity-item" style="padding: 16px;">
                            <div class="activity-icon call">📞</div>
                            <div class="activity-content">
                                <div class="activity-text"><strong>David Chen</strong> - 2 min call</div>
                                <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">Outcome: Not interested at this time</div>
                                <div class="activity-meta">
                                    <span class="activity-time">1 hr ago</span>
                                    <span class="activity-tag">Neutral</span>
                                </div>
                            </div>
                        </div>
                        <div class="activity-item" style="padding: 16px;">
                            <div class="activity-icon call">📞</div>
                            <div class="activity-content">
                                <div class="activity-text"><strong>Emma Wilson</strong> - 5 min call</div>
                                <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">Outcome: Very interested - Call back scheduled</div>
                                <div class="activity-meta">
                                    <span class="activity-time">2 hrs ago</span>
                                    <span class="activity-tag" style="background: rgba(16, 124, 16, 0.1); color: var(--success);">Hot Lead</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Voice Stats -->
                <div class="panel">
                    <div class="panel-header">
                        <h2 class="panel-title">Call Outcomes</h2>
                    </div>
                    <div class="panel-body">
                        <div style="margin-bottom: 16px;">
                            <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                                <span style="font-size: 12px;">Interested</span>
                                <span style="font-size: 12px; font-weight: 600;">35%</span>
                            </div>
                            <div style="height: 8px; background: var(--bg-main); border-radius: 4px; overflow: hidden;">
                                <div style="height: 100%; width: 35%; background: var(--success); border-radius: 4px;"></div>
                            </div>
                        </div>
                        <div style="margin-bottom: 16px;">
                            <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                                <span style="font-size: 12px;">Call Back Later</span>
                                <span style="font-size: 12px; font-weight: 600;">25%</span>
                            </div>
                            <div style="height: 8px; background: var(--bg-main); border-radius: 4px; overflow: hidden;">
                                <div style="height: 100%; width: 25%; background: var(--warning); border-radius: 4px;"></div>
                            </div>
                        </div>
                        <div style="margin-bottom: 16px;">
                            <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                                <span style="font-size: 12px;">Not Interested</span>
                                <span style="font-size: 12px; font-weight: 600;">22%</span>
                            </div>
                            <div style="height: 8px; background: var(--bg-main); border-radius: 4px; overflow: hidden;">
                                <div style="height: 100%; width: 22%; background: var(--danger); border-radius: 4px;"></div>
                            </div>
                        </div>
                        <div>
                            <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                                <span style="font-size: 12px;">Voicemail</span>
                                <span style="font-size: 12px; font-weight: 600;">18%</span>
                            </div>
                            <div style="height: 8px; background: var(--bg-main); border-radius: 4px; overflow: hidden;">
                                <div style="height: 100%; width: 18%; background: var(--text-muted); border-radius: 4px;"></div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `
    },

    // ==================== DIRECT MAIL ====================
    directmail: {
        title: 'Direct Mail Channel',
        breadcrumb: '85 pieces sent this month',
        content: `
            <!-- Stats Row -->
            <div class="stats-row">
                <div class="stat-card">
                    <div class="stat-label">Mail Sent</div>
                    <div class="stat-value">85</div>
                    <div class="stat-change up">↑ +12 this week</div>
                </div>
                <div class="stat-card success">
                    <div class="stat-label">Delivered</div>
                    <div class="stat-value">82</div>
                    <div class="stat-change up">96.5% delivery</div>
                </div>
                <div class="stat-card warning">
                    <div class="stat-label">QR Scans</div>
                    <div class="stat-value">12</div>
                    <div class="stat-change up">14.1% scan rate</div>
                </div>
                <div class="stat-card purple">
                    <div class="stat-label">Responses</div>
                    <div class="stat-value">4</div>
                    <div class="stat-change up">4.7% response</div>
                </div>
                <div class="stat-card orange">
                    <div class="stat-label">Meetings</div>
                    <div class="stat-value">2</div>
                    <div class="stat-change up">From direct mail</div>
                </div>
            </div>

            <div class="two-column">
                <!-- Recent Activity -->
                <div class="panel">
                    <div class="panel-header">
                        <h2 class="panel-title">Recent Direct Mail Activity</h2>
                    </div>
                    <div class="panel-body" style="padding: 0;">
                        <div class="activity-item" style="padding: 16px;">
                            <div class="activity-icon" style="background: rgba(247, 99, 12, 0.1); color: var(--accent-orange);">📬</div>
                            <div class="activity-content">
                                <div class="activity-text"><strong>Ben Harper</strong> scanned QR code</div>
                                <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">Viewed landing page for 2m 34s</div>
                                <div class="activity-meta">
                                    <span class="activity-time">2 hrs ago</span>
                                    <span class="activity-tag">Enterprise</span>
                                </div>
                            </div>
                        </div>
                        <div class="activity-item" style="padding: 16px;">
                            <div class="activity-icon" style="background: rgba(247, 99, 12, 0.1); color: var(--accent-orange);">📬</div>
                            <div class="activity-content">
                                <div class="activity-text"><strong>8 pieces</strong> delivered today</div>
                                <div class="activity-meta">
                                    <span class="activity-time">4 hrs ago</span>
                                    <span class="activity-tag">Melbourne Campaign</span>
                                </div>
                            </div>
                        </div>
                        <div class="activity-item" style="padding: 16px;">
                            <div class="activity-icon reply">↩</div>
                            <div class="activity-content">
                                <div class="activity-text"><strong>Amanda Foster</strong> called after receiving mail</div>
                                <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">"I got your letter, let's schedule a call"</div>
                                <div class="activity-meta">
                                    <span class="activity-time">Yesterday</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Mail Types -->
                <div class="panel">
                    <div class="panel-header">
                        <h2 class="panel-title">Mail Pieces by Type</h2>
                    </div>
                    <div class="panel-body">
                        <div style="margin-bottom: 16px;">
                            <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                                <span style="font-size: 12px;">Handwritten Cards</span>
                                <span style="font-size: 12px; font-weight: 600;">45 sent</span>
                            </div>
                            <div style="height: 8px; background: var(--bg-main); border-radius: 4px; overflow: hidden;">
                                <div style="height: 100%; width: 53%; background: var(--accent-orange); border-radius: 4px;"></div>
                            </div>
                        </div>
                        <div style="margin-bottom: 16px;">
                            <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                                <span style="font-size: 12px;">Premium Letters</span>
                                <span style="font-size: 12px; font-weight: 600;">28 sent</span>
                            </div>
                            <div style="height: 8px; background: var(--bg-main); border-radius: 4px; overflow: hidden;">
                                <div style="height: 100%; width: 33%; background: var(--primary); border-radius: 4px;"></div>
                            </div>
                        </div>
                        <div>
                            <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                                <span style="font-size: 12px;">Gift Boxes</span>
                                <span style="font-size: 12px; font-weight: 600;">12 sent</span>
                            </div>
                            <div style="height: 8px; background: var(--bg-main); border-radius: 4px; overflow: hidden;">
                                <div style="height: 100%; width: 14%; background: var(--accent-purple); border-radius: 4px;"></div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `
    },

    // ==================== INBOX ====================
    inbox: {
        title: 'Inbox',
        breadcrumb: '8 unread messages',
        content: `
            <div class="main-grid">
                <!-- Messages List -->
                <div class="panel">
                    <div class="panel-header">
                        <h2 class="panel-title">All Messages</h2>
                        <div class="panel-actions">
                            <select class="filter-select">
                                <option>All Channels</option>
                                <option>Email</option>
                                <option>LinkedIn</option>
                                <option>SMS</option>
                            </select>
                            <select class="filter-select">
                                <option>All</option>
                                <option>Unread</option>
                                <option>Needs Response</option>
                            </select>
                        </div>
                    </div>
                    <div style="max-height: 600px; overflow-y: auto;">
                        <div class="message-item unread">
                            <div class="message-header">
                                <span class="message-from">Sarah Mitchell</span>
                                <span class="message-time">2 min ago</span>
                            </div>
                            <div class="message-subject">Re: Quick question about client acquisition</div>
                            <div class="message-preview">Thanks for reaching out! I'd love to hear more about how you can help us...</div>
                            <div class="message-tags">
                                <span class="activity-tag">Email</span>
                                <span class="activity-tag" style="background: rgba(16, 124, 16, 0.1); color: var(--success);">Positive</span>
                            </div>
                        </div>
                        <div class="message-item unread">
                            <div class="message-header">
                                <span class="message-from">James Kirkwood</span>
                                <span class="message-time">8 min ago</span>
                            </div>
                            <div class="message-subject">Re: Partnership opportunity</div>
                            <div class="message-preview">This sounds interesting. Can you send over some case studies?</div>
                            <div class="message-tags">
                                <span class="activity-tag">Email</span>
                                <span class="activity-tag" style="background: rgba(16, 124, 16, 0.1); color: var(--success);">Interested</span>
                            </div>
                        </div>
                        <div class="message-item unread">
                            <div class="message-header">
                                <span class="message-from">Lisa Tran</span>
                                <span class="message-time">15 min ago</span>
                            </div>
                            <div class="message-subject">SMS Reply</div>
                            <div class="message-preview">Yes, I'm available Thursday afternoon for a call</div>
                            <div class="message-tags">
                                <span class="activity-tag">SMS</span>
                                <span class="activity-tag" style="background: rgba(16, 124, 16, 0.1); color: var(--success);">Meeting Request</span>
                            </div>
                        </div>
                        <div class="message-item">
                            <div class="message-header">
                                <span class="message-from">Tom Richards</span>
                                <span class="message-time">1 hr ago</span>
                            </div>
                            <div class="message-subject">LinkedIn Message</div>
                            <div class="message-preview">Thanks for connecting! Would love to hear more about your services...</div>
                            <div class="message-tags">
                                <span class="activity-tag">LinkedIn</span>
                            </div>
                        </div>
                        <div class="message-item">
                            <div class="message-header">
                                <span class="message-from">Amanda Foster</span>
                                <span class="message-time">2 hrs ago</span>
                            </div>
                            <div class="message-subject">Re: Your letter</div>
                            <div class="message-preview">I received your letter in the mail. Let's schedule a time to talk...</div>
                            <div class="message-tags">
                                <span class="activity-tag">Email</span>
                                <span class="activity-tag" style="background: rgba(16, 124, 16, 0.1); color: var(--success);">Hot</span>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Message Detail / Quick Actions -->
                <div style="display: flex; flex-direction: column; gap: 24px;">
                    <div class="panel">
                        <div class="panel-header">
                            <h2 class="panel-title">Quick Stats</h2>
                        </div>
                        <div class="panel-body">
                            <div class="compliance-grid">
                                <div class="compliance-item">
                                    <div class="compliance-value" style="color: var(--primary);">8</div>
                                    <div class="compliance-label">Unread</div>
                                </div>
                                <div class="compliance-item">
                                    <div class="compliance-value" style="color: var(--success);">5</div>
                                    <div class="compliance-label">Positive</div>
                                </div>
                                <div class="compliance-item">
                                    <div class="compliance-value" style="color: var(--warning);">2</div>
                                    <div class="compliance-label">Needs Action</div>
                                </div>
                                <div class="compliance-item">
                                    <div class="compliance-value" style="color: var(--text-muted);">12</div>
                                    <div class="compliance-label">Today Total</div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="panel">
                        <div class="panel-header">
                            <h2 class="panel-title">AI Classification</h2>
                        </div>
                        <div class="panel-body">
                            <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 12px;">Reply Agent has classified today's messages:</div>
                            <div style="margin-bottom: 12px;">
                                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                                    <span style="font-size: 12px; color: var(--success);">● Positive Intent</span>
                                    <span style="font-size: 12px; font-weight: 600;">5</span>
                                </div>
                            </div>
                            <div style="margin-bottom: 12px;">
                                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                                    <span style="font-size: 12px; color: var(--warning);">● Questions</span>
                                    <span style="font-size: 12px; font-weight: 600;">3</span>
                                </div>
                            </div>
                            <div style="margin-bottom: 12px;">
                                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                                    <span style="font-size: 12px; color: var(--danger);">● Not Interested</span>
                                    <span style="font-size: 12px; font-weight: 600;">2</span>
                                </div>
                            </div>
                            <div>
                                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                                    <span style="font-size: 12px; color: var(--text-muted);">● Out of Office</span>
                                    <span style="font-size: 12px; font-weight: 600;">2</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `
    },

    // ==================== MEETINGS ====================
    meetings: {
        title: 'Meetings',
        breadcrumb: '34 meetings this month',
        content: `
            <!-- Stats Row -->
            <div class="stats-row" style="grid-template-columns: repeat(4, 1fr);">
                <div class="stat-card">
                    <div class="stat-label">This Month</div>
                    <div class="stat-value">34</div>
                    <div class="stat-change up">↑ +8 from last month</div>
                </div>
                <div class="stat-card success">
                    <div class="stat-label">Completed</div>
                    <div class="stat-value">28</div>
                    <div class="stat-change up">82% show rate</div>
                </div>
                <div class="stat-card warning">
                    <div class="stat-label">Upcoming</div>
                    <div class="stat-value">6</div>
                    <div class="stat-change">Next 7 days</div>
                </div>
                <div class="stat-card purple">
                    <div class="stat-label">Proposals Sent</div>
                    <div class="stat-value">12</div>
                    <div class="stat-change up">43% of meetings</div>
                </div>
            </div>

            <div class="two-column">
                <!-- Upcoming Meetings -->
                <div class="panel">
                    <div class="panel-header">
                        <h2 class="panel-title">Upcoming Meetings</h2>
                    </div>
                    <div class="panel-body">
                        <div class="meeting-card" style="border-left: 3px solid var(--success);">
                            <div class="meeting-time">Today, 2:00 PM AEDT</div>
                            <div class="meeting-title">Discovery Call - Pixel & Co Digital</div>
                            <div class="meeting-attendee">Sarah Mitchell • CEO</div>
                            <div class="meeting-actions">
                                <button class="btn btn-primary" style="padding: 6px 12px;">Join Call</button>
                                <button class="btn" style="padding: 6px 12px;">Prep Notes</button>
                            </div>
                        </div>
                        <div class="meeting-card">
                            <div class="meeting-time">Tomorrow, 10:00 AM AEDT</div>
                            <div class="meeting-title">Follow-up - Momentum Agency</div>
                            <div class="meeting-attendee">James Kirkwood • Managing Director</div>
                            <div class="meeting-actions">
                                <button class="btn" style="padding: 6px 12px;">Prep Notes</button>
                                <button class="btn" style="padding: 6px 12px;">Reschedule</button>
                            </div>
                        </div>
                        <div class="meeting-card">
                            <div class="meeting-time">Wed, 24 Dec, 3:00 PM AEDT</div>
                            <div class="meeting-title">Demo - Growth Labs</div>
                            <div class="meeting-attendee">Lisa Tran • Founder</div>
                            <div class="meeting-actions">
                                <button class="btn" style="padding: 6px 12px;">Prep Notes</button>
                                <button class="btn" style="padding: 6px 12px;">Reschedule</button>
                            </div>
                        </div>
                        <div class="meeting-card">
                            <div class="meeting-time">Thu, 26 Dec, 11:00 AM AEDT</div>
                            <div class="meeting-title">Intro Call - Digital Edge</div>
                            <div class="meeting-attendee">Michael Wong • Director</div>
                            <div class="meeting-actions">
                                <button class="btn" style="padding: 6px 12px;">Prep Notes</button>
                                <button class="btn" style="padding: 6px 12px;">Reschedule</button>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Recent Completed -->
                <div class="panel">
                    <div class="panel-header">
                        <h2 class="panel-title">Recently Completed</h2>
                    </div>
                    <div class="panel-body">
                        <div class="meeting-card" style="opacity: 0.8;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <div class="meeting-time" style="color: var(--text-muted);">Yesterday</div>
                                    <div class="meeting-title">Discovery - Harper Media Group</div>
                                    <div class="meeting-attendee">Ben Harper • CEO</div>
                                </div>
                                <span class="status-badge completed">Proposal Sent</span>
                            </div>
                        </div>
                        <div class="meeting-card" style="opacity: 0.8;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <div class="meeting-time" style="color: var(--text-muted);">Dec 20</div>
                                    <div class="meeting-title">Demo - Apex Creative</div>
                                    <div class="meeting-attendee">Rachel Green • CMO</div>
                                </div>
                                <span class="status-badge active">Follow-up Set</span>
                            </div>
                        </div>
                        <div class="meeting-card" style="opacity: 0.8;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <div class="meeting-time" style="color: var(--text-muted);">Dec 19</div>
                                    <div class="meeting-title">Intro - Coastal Digital</div>
                                    <div class="meeting-attendee">Mark Thompson • Owner</div>
                                </div>
                                <span class="status-badge paused">No Fit</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `
    },

    // ==================== PIPELINE ====================
    pipeline: {
        title: 'Pipeline',
        breadcrumb: '$127,450 weighted value',
        content: `
            <!-- Stats Row -->
            <div class="stats-row" style="grid-template-columns: repeat(4, 1fr);">
                <div class="stat-card">
                    <div class="stat-label">Total Pipeline</div>
                    <div class="stat-value">$284K</div>
                    <div class="stat-change up">↑ +$52K this month</div>
                </div>
                <div class="stat-card success">
                    <div class="stat-label">Weighted Pipeline</div>
                    <div class="stat-value">$127K</div>
                    <div class="stat-change up">↑ +$34K this month</div>
                </div>
                <div class="stat-card warning">
                    <div class="stat-label">Avg Deal Size</div>
                    <div class="stat-value">$4,625</div>
                    <div class="stat-change up">↑ +$320 vs avg</div>
                </div>
                <div class="stat-card purple">
                    <div class="stat-label">Close Rate</div>
                    <div class="stat-value">12%</div>
                    <div class="stat-change up">↑ +2% this month</div>
                </div>
            </div>

            <!-- Pipeline Stages -->
            <div class="panel" style="margin-bottom: 24px;">
                <div class="panel-header">
                    <h2 class="panel-title">Pipeline Stages</h2>
                </div>
                <div class="panel-body">
                    <div style="display: flex; gap: 4px;">
                        <div style="flex: 1; padding: 20px; background: var(--bg-main); border-radius: 4px 0 0 4px; text-align: center;">
                            <div style="font-size: 28px; font-weight: 600;">847</div>
                            <div style="font-size: 11px; color: var(--text-muted); text-transform: uppercase;">Leads</div>
                            <div style="font-size: 10px; color: var(--text-muted); margin-top: 4px;">$0</div>
                        </div>
                        <div style="flex: 1; padding: 20px; background: rgba(18, 52, 153, 0.1); text-align: center;">
                            <div style="font-size: 28px; font-weight: 600; color: var(--primary);">156</div>
                            <div style="font-size: 11px; color: var(--text-muted); text-transform: uppercase;">Engaged</div>
                            <div style="font-size: 10px; color: var(--text-muted); margin-top: 4px;">$0</div>
                        </div>
                        <div style="flex: 1; padding: 20px; background: rgba(136, 108, 228, 0.1); text-align: center;">
                            <div style="font-size: 28px; font-weight: 600; color: var(--accent-purple);">34</div>
                            <div style="font-size: 11px; color: var(--text-muted); text-transform: uppercase;">Meeting</div>
                            <div style="font-size: 10px; color: var(--primary); margin-top: 4px;">$156,400</div>
                        </div>
                        <div style="flex: 1; padding: 20px; background: rgba(255, 140, 0, 0.1); text-align: center;">
                            <div style="font-size: 28px; font-weight: 600; color: var(--warning);">12</div>
                            <div style="font-size: 11px; color: var(--text-muted); text-transform: uppercase;">Proposal</div>
                            <div style="font-size: 10px; color: var(--primary); margin-top: 4px;">$78,500</div>
                        </div>
                        <div style="flex: 1; padding: 20px; background: rgba(16, 124, 16, 0.1); text-align: center;">
                            <div style="font-size: 28px; font-weight: 600; color: var(--success);">8</div>
                            <div style="font-size: 11px; color: var(--text-muted); text-transform: uppercase;">Negotiation</div>
                            <div style="font-size: 10px; color: var(--primary); margin-top: 4px;">$49,200</div>
                        </div>
                        <div style="flex: 1; padding: 20px; background: var(--success); color: white; border-radius: 0 4px 4px 0; text-align: center;">
                            <div style="font-size: 28px; font-weight: 600;">4</div>
                            <div style="font-size: 11px; text-transform: uppercase; opacity: 0.9;">Closed Won</div>
                            <div style="font-size: 10px; margin-top: 4px;">$18,500</div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Deals Table -->
            <div class="panel">
                <div class="panel-header">
                    <h2 class="panel-title">Active Deals</h2>
                    <div class="panel-actions">
                        <select class="filter-select">
                            <option>All Stages</option>
                            <option>Meeting</option>
                            <option>Proposal</option>
                            <option>Negotiation</option>
                        </select>
                    </div>
                </div>
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Company</th>
                            <th>Contact</th>
                            <th>Value</th>
                            <th>Stage</th>
                            <th>Probability</th>
                            <th>Weighted</th>
                            <th>Next Step</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td style="font-weight: 500;">Pixel & Co Digital</td>
                            <td>Sarah Mitchell</td>
                            <td>$5,500/mo</td>
                            <td><span class="status-badge" style="background: rgba(136, 108, 228, 0.1); color: var(--accent-purple);">Meeting</span></td>
                            <td>40%</td>
                            <td style="font-weight: 600; color: var(--primary);">$2,200</td>
                            <td style="font-size: 11px;">Discovery call today</td>
                            <td><button class="btn" style="padding: 4px 8px;">View</button></td>
                        </tr>
                        <tr>
                            <td style="font-weight: 500;">Harper Media Group</td>
                            <td>Ben Harper</td>
                            <td>$7,500/mo</td>
                            <td><span class="status-badge" style="background: rgba(255, 140, 0, 0.1); color: var(--warning);">Proposal</span></td>
                            <td>60%</td>
                            <td style="font-weight: 600; color: var(--primary);">$4,500</td>
                            <td style="font-size: 11px;">Proposal review Thu</td>
                            <td><button class="btn" style="padding: 4px 8px;">View</button></td>
                        </tr>
                        <tr>
                            <td style="font-weight: 500;">Momentum Agency</td>
                            <td>James Kirkwood</td>
                            <td>$4,500/mo</td>
                            <td><span class="status-badge" style="background: rgba(136, 108, 228, 0.1); color: var(--accent-purple);">Meeting</span></td>
                            <td>40%</td>
                            <td style="font-weight: 600; color: var(--primary);">$1,800</td>
                            <td style="font-size: 11px;">Follow-up tomorrow</td>
                            <td><button class="btn" style="padding: 4px 8px;">View</button></td>
                        </tr>
                        <tr>
                            <td style="font-weight: 500;">Apex Creative</td>
                            <td>Rachel Green</td>
                            <td>$6,000/mo</td>
                            <td><span class="status-badge" style="background: rgba(16, 124, 16, 0.1); color: var(--success);">Negotiation</span></td>
                            <td>80%</td>
                            <td style="font-weight: 600; color: var(--primary);">$4,800</td>
                            <td style="font-size: 11px;">Contract review</td>
                            <td><button class="btn" style="padding: 4px 8px;">View</button></td>
                        </tr>
                        <tr>
                            <td style="font-weight: 500;">Growth Labs</td>
                            <td>Lisa Tran</td>
                            <td>$3,500/mo</td>
                            <td><span class="status-badge" style="background: rgba(136, 108, 228, 0.1); color: var(--accent-purple);">Meeting</span></td>
                            <td>40%</td>
                            <td style="font-weight: 600; color: var(--primary);">$1,400</td>
                            <td style="font-size: 11px;">Demo on Wed</td>
                            <td><button class="btn" style="padding: 4px 8px;">View</button></td>
                        </tr>
                    </tbody>
                </table>
            </div>
        `
    },

    // ==================== SETTINGS ====================
    settings: {
        title: 'Settings',
        breadcrumb: 'Account & Configuration',
        content: `
            <div class="tabs">
                <div class="tab active">General</div>
                <div class="tab">Integrations</div>
                <div class="tab">Team</div>
                <div class="tab">Billing</div>
            </div>

            <div class="two-column">
                <!-- General Settings -->
                <div class="panel">
                    <div class="panel-header">
                        <h2 class="panel-title">Account Settings</h2>
                    </div>
                    <div class="panel-body">
                        <div class="form-group">
                            <label class="form-label">Company Name</label>
                            <input type="text" class="form-input" value="Your Agency Name">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Primary Email</label>
                            <input type="email" class="form-input" value="you@agency.com">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Timezone</label>
                            <select class="form-select">
                                <option selected>Australia/Sydney (AEDT)</option>
                                <option>Australia/Melbourne</option>
                                <option>Australia/Brisbane</option>
                                <option>Australia/Perth</option>
                            </select>
                        </div>
                        <button class="btn btn-primary">Save Changes</button>
                    </div>
                </div>

                <!-- Mode Settings -->
                <div class="panel">
                    <div class="panel-header">
                        <h2 class="panel-title">Automation Mode</h2>
                    </div>
                    <div class="panel-body">
                        <div style="margin-bottom: 20px;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                                <div>
                                    <div style="font-weight: 500;">Default Mode</div>
                                    <div style="font-size: 11px; color: var(--text-muted);">Applied to new campaigns</div>
                                </div>
                                <select class="filter-select">
                                    <option selected>Auto Pilot</option>
                                    <option>Boss Mode</option>
                                </select>
                            </div>
                        </div>
                        <div style="padding: 16px; background: var(--bg-main); border-radius: 4px; margin-bottom: 16px;">
                            <div style="font-weight: 500; margin-bottom: 8px;">🚀 Auto Pilot</div>
                            <div style="font-size: 12px; color: var(--text-muted);">AI agents send messages, classify replies, and respond automatically. You review results.</div>
                        </div>
                        <div style="padding: 16px; background: var(--bg-main); border-radius: 4px;">
                            <div style="font-weight: 500; margin-bottom: 8px;">👔 Boss Mode</div>
                            <div style="font-size: 12px; color: var(--text-muted);">AI agents draft messages and suggest responses. You approve before sending.</div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="two-column" style="margin-top: 24px;">
                <!-- Notification Settings -->
                <div class="panel">
                    <div class="panel-header">
                        <h2 class="panel-title">Notifications</h2>
                    </div>
                    <div class="panel-body">
                        <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px 0; border-bottom: 1px solid var(--border);">
                            <div>
                                <div style="font-weight: 500;">Meeting Booked</div>
                                <div style="font-size: 11px; color: var(--text-muted);">Get notified when a meeting is scheduled</div>
                            </div>
                            <div class="toggle-switch">
                                <div class="toggle-track active">
                                    <div class="toggle-thumb"></div>
                                </div>
                            </div>
                        </div>
                        <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px 0; border-bottom: 1px solid var(--border);">
                            <div>
                                <div style="font-weight: 500;">Positive Reply</div>
                                <div style="font-size: 11px; color: var(--text-muted);">Alert when AI detects positive intent</div>
                            </div>
                            <div class="toggle-switch">
                                <div class="toggle-track active">
                                    <div class="toggle-thumb"></div>
                                </div>
                            </div>
                        </div>
                        <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px 0; border-bottom: 1px solid var(--border);">
                            <div>
                                <div style="font-weight: 500;">Daily Summary</div>
                                <div style="font-size: 11px; color: var(--text-muted);">Receive daily performance report</div>
                            </div>
                            <div class="toggle-switch">
                                <div class="toggle-track active">
                                    <div class="toggle-thumb"></div>
                                </div>
                            </div>
                        </div>
                        <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px 0;">
                            <div>
                                <div style="font-weight: 500;">Deliverability Alerts</div>
                                <div style="font-size: 11px; color: var(--text-muted);">Warn about potential issues</div>
                            </div>
                            <div class="toggle-switch">
                                <div class="toggle-track active">
                                    <div class="toggle-thumb"></div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Connected Accounts -->
                <div class="panel">
                    <div class="panel-header">
                        <h2 class="panel-title">Connected Accounts</h2>
                    </div>
                    <div class="panel-body">
                        <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px 0; border-bottom: 1px solid var(--border);">
                            <div style="display: flex; align-items: center; gap: 12px;">
                                <div style="width: 32px; height: 32px; background: rgba(18, 52, 153, 0.1); border-radius: 4px; display: flex; align-items: center; justify-content: center;">✉</div>
                                <div>
                                    <div style="font-weight: 500;">Email</div>
                                    <div style="font-size: 11px; color: var(--text-muted);">you@agency.com</div>
                                </div>
                            </div>
                            <span class="status-badge active">Connected</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px 0; border-bottom: 1px solid var(--border);">
                            <div style="display: flex; align-items: center; gap: 12px;">
                                <div style="width: 32px; height: 32px; background: rgba(0, 119, 181, 0.1); border-radius: 4px; display: flex; align-items: center; justify-content: center; color: #0077b5;">in</div>
                                <div>
                                    <div style="font-weight: 500;">LinkedIn</div>
                                    <div style="font-size: 11px; color: var(--text-muted);">Your Name</div>
                                </div>
                            </div>
                            <span class="status-badge active">Connected</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px 0; border-bottom: 1px solid var(--border);">
                            <div style="display: flex; align-items: center; gap: 12px;">
                                <div style="width: 32px; height: 32px; background: rgba(16, 124, 16, 0.1); border-radius: 4px; display: flex; align-items: center; justify-content: center; color: var(--success);">💬</div>
                                <div>
                                    <div style="font-weight: 500;">SMS</div>
                                    <div style="font-size: 11px; color: var(--text-muted);">+61 4XX XXX XXX</div>
                                </div>
                            </div>
                            <span class="status-badge active">Connected</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px 0;">
                            <div style="display: flex; align-items: center; gap: 12px;">
                                <div style="width: 32px; height: 32px; background: rgba(136, 108, 228, 0.1); border-radius: 4px; display: flex; align-items: center; justify-content: center; color: var(--accent-purple);">📅</div>
                                <div>
                                    <div style="font-weight: 500;">Calendar</div>
                                    <div style="font-size: 11px; color: var(--text-muted);">Google Calendar</div>
                                </div>
                            </div>
                            <span class="status-badge active">Connected</span>
                        </div>
                    </div>
                </div>
            </div>
        `
    }
};

// ==================== NAVIGATION & ROUTING ====================

// Initialize app
document.addEventListener('DOMContentLoaded', function() {
    // Load initial page
    const hash = window.location.hash.slice(1) || 'dashboard';
    loadPage(hash);

    // Handle navigation clicks
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            const page = this.dataset.page;
            loadPage(page);
            window.location.hash = page;
        });
    });

    // Handle hash changes
    window.addEventListener('hashchange', function() {
        const hash = window.location.hash.slice(1) || 'dashboard';
        loadPage(hash);
    });

    // Mode toggle
    document.getElementById('mode-toggle').addEventListener('click', function() {
        const modeValue = document.getElementById('mode-value');
        if (modeValue.textContent === 'Auto Pilot') {
            modeValue.textContent = 'Boss Mode';
            modeValue.classList.add('boss');
            modeValue.classList.remove('auto');
        } else {
            modeValue.textContent = 'Auto Pilot';
            modeValue.classList.remove('boss');
            modeValue.classList.add('auto');
        }
    });
});

// Load page content
function loadPage(pageName) {
    const page = pages[pageName];
    if (!page) {
        console.error('Page not found:', pageName);
        return;
    }

    // Update page title and breadcrumb
    document.getElementById('page-title').textContent = page.title;
    document.getElementById('breadcrumb').textContent = page.breadcrumb;

    // Update page content
    document.getElementById('page-content').innerHTML = page.content;

    // Update active nav item
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
        if (item.dataset.page === pageName) {
            item.classList.add('active');
        }
    });

    // Scroll to top
    window.scrollTo(0, 0);
}
