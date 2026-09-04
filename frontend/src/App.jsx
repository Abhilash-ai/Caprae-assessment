import React, { useState, useEffect, useMemo } from 'react';
import './App.css';

export default function App() {
  const [csvText, setCsvText] = useState('');
  const [fileName, setFileName] = useState('');
  const [loading, setLoading] = useState(false);
  const [batchData, setBatchData] = useState(null);
  const [error, setError] = useState(null);

  // ICP Configuration state
  const [showConfig, setShowConfig] = useState(false);
  const [config, setConfig] = useState({
    weight_seniority: 40,
    weight_industry: 35,
    weight_size: 25,
    min_company_size: 50,
    max_company_size: 1000
  });

  // Table controls state
  const [searchTerm, setSearchTerm] = useState('');
  const [filterMode, setFilterMode] = useState('unique'); // 'all', 'unique', 'duplicates', 'issues', 'tier1'
  const [sortBy, setSortBy] = useState('icp_score'); // 'icp_score', 'data_quality_score', 'name', 'company'
  const [sortOrder, setSortOrder] = useState('desc');
  const [excludeDuplicatesInExport, setExcludeDuplicatesInExport] = useState(true);

  // Auto-load sample data on first load for immediate testability
  useEffect(() => {
    loadSampleData();
  }, []);

  const loadSampleData = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetch('/api/leads/sample');
      if (!res.ok) throw new Error('Failed to load sample dataset');
      const data = await res.json();
      
      // Convert JSON leads to CSV text representation for textarea
      if (data.leads && data.leads.length > 0) {
        const headers = Object.keys(data.leads[0]).join(',');
        const rows = data.leads.map(row => Object.values(row).join(','));
        const fullCsv = [headers, ...rows].join('\n');
        setCsvText(fullCsv);
        setFileName(data.filename || 'sample_leads_raw.csv');
      }

      // Automatically trigger processing on the loaded sample
      await processCsvLeads(data.leads, data.filename);
    } catch (err) {
      console.error(err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setFileName(file.name);
    const reader = new FileReader();
    reader.onload = (evt) => {
      setCsvText(evt.target.result);
    };
    reader.readAsText(file);
  };

  const parseCsvToObjects = (text) => {
    const lines = text.trim().split(/\r?\n/);
    if (lines.length < 2) return [];
    
    // Naive CSV splitter respecting quotes
    const splitRow = (row) => {
      const result = [];
      let current = '';
      let inQuotes = false;
      for (let i = 0; i < row.length; i++) {
        const char = row[i];
        if (char === '"') {
          inQuotes = !inQuotes;
        } else if (char === ',' && !inQuotes) {
          result.push(current.trim());
          current = '';
        } else {
          current += char;
        }
      }
      result.push(current.trim());
      return result;
    };

    const headers = splitRow(lines[0]).map(h => h.trim().toLowerCase());
    const leads = [];

    for (let i = 1; i < lines.length; i++) {
      if (!lines[i].trim()) continue;
      const values = splitRow(lines[i]);
      const obj = {};
      headers.forEach((h, idx) => {
        obj[h] = values[idx] || '';
      });
      leads.push(obj);
    }

    return leads;
  };

  const processCsvLeads = async (leadsArray = null, customFilename = null) => {
    try {
      setLoading(true);
      setError(null);

      const targetLeads = leadsArray || parseCsvToObjects(csvText);
      if (!targetLeads || targetLeads.length === 0) {
        throw new Error('Please upload or paste a CSV with at least one data row.');
      }

      const payload = {
        filename: customFilename || fileName || 'pasted_leads.csv',
        leads: targetLeads,
        icp_config: {
          weight_seniority: Number(config.weight_seniority),
          weight_industry: Number(config.weight_industry),
          weight_size: Number(config.weight_size),
          min_company_size: Number(config.min_company_size),
          max_company_size: Number(config.max_company_size)
        }
      };

      const res = await fetch('/api/leads/process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || 'Processing failed');
      }

      const data = await res.json();
      setBatchData(data);
    } catch (err) {
      console.error(err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleExport = (crmType) => {
    if (!batchData || !batchData.id) return;
    const url = `/api/batches/${batchData.id}/export?crm=${crmType}&only_unique=${excludeDuplicatesInExport}`;
    window.open(url, '_blank');
  };

  // Filter and sort leads for display
  const displayedLeads = useMemo(() => {
    if (!batchData || !batchData.leads) return [];

    return batchData.leads
      .filter((lead) => {
        // Mode filter
        if (filterMode === 'unique' && lead.is_duplicate) return false;
        if (filterMode === 'duplicates' && !lead.is_duplicate) return false;
        if (filterMode === 'issues' && (!lead.quality_issues || lead.quality_issues.length === 0)) return false;
        if (filterMode === 'tier1' && !lead.icp_tier.includes('Tier 1')) return false;

        // Search query filter
        if (searchTerm) {
          const term = searchTerm.toLowerCase();
          const fullName = `${lead.first_name} ${lead.last_name}`.toLowerCase();
          const company = (lead.company || '').toLowerCase();
          const title = (lead.title || '').toLowerCase();
          const email = (lead.email || '').toLowerCase();
          const domain = (lead.domain || '').toLowerCase();

          return (
            fullName.includes(term) ||
            company.includes(term) ||
            title.includes(term) ||
            email.includes(term) ||
            domain.includes(term)
          );
        }
        return true;
      })
      .sort((a, b) => {
        let valA = a[sortBy];
        let valB = b[sortBy];

        if (sortBy === 'name') {
          valA = `${a.first_name} ${a.last_name}`.toLowerCase();
          valB = `${b.first_name} ${b.last_name}`.toLowerCase();
        } else if (sortBy === 'company') {
          valA = (a.company || '').toLowerCase();
          valB = (b.company || '').toLowerCase();
        }

        if (valA < valB) return sortOrder === 'asc' ? -1 : 1;
        if (valA > valB) return sortOrder === 'asc' ? 1 : -1;
        return 0;
      });
  }, [batchData, filterMode, searchTerm, sortBy, sortOrder]);

  const toggleSort = (field) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortOrder('desc');
    }
  };

  return (
    <div className="app-container">
      {/* Header */}
      <header>
        <div className="header-brand">
          <h1>
            Caprae Lead Prioritization & Enrichment Engine
            <span className="badge-tag">Path A: Quality First</span>
          </h1>
          <div className="header-subtitle">
            Post-scraping intelligence for SDR teams: Fuzzy deduplication, automated data hygiene validation, configurable ICP scoring, and CRM-ready export.
          </div>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button className="btn" onClick={loadSampleData} disabled={loading}>
            🔄 Load Sample Scraped Leads
          </button>
          <button 
            className="btn btn-primary" 
            onClick={() => processCsvLeads()}
            disabled={loading || !csvText.trim()}
          >
            {loading ? 'Processing...' : '⚡ Run Pipeline'}
          </button>
        </div>
      </header>

      {error && (
        <div style={{ background: '#7f1d1d', border: '1px solid #ef4444', padding: '0.75rem 1rem', borderRadius: '6px', marginBottom: '1rem', color: '#fecaca', fontSize: '0.85rem' }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Metrics Banner */}
      {batchData && (
        <div className="grid-cols-4">
          <div className="metric-card">
            <span className="metric-title">Total Scraped Leads</span>
            <span className="metric-value">{batchData.total_leads}</span>
            <span className="metric-desc">Raw records ingested</span>
          </div>
          <div className="metric-card">
            <span className="metric-title">Unique Contacts</span>
            <span className="metric-value" style={{ color: '#34d399' }}>{batchData.unique_leads}</span>
            <span className="metric-desc">Primary targets identified</span>
          </div>
          <div className="metric-card">
            <span className="metric-title">Duplicates Pruned</span>
            <span className="metric-value" style={{ color: '#f87171' }}>
              {batchData.duplicate_leads} ({batchData.total_leads ? Math.round((batchData.duplicate_leads / batchData.total_leads) * 100) : 0}%)
            </span>
            <span className="metric-desc">Fuzzy clusters collapsed</span>
          </div>
          <div className="metric-card">
            <span className="metric-title">High-Fit ICP (Tier 1)</span>
            <span className="metric-value" style={{ color: '#60a5fa' }}>{batchData.high_fit_leads}</span>
            <span className="metric-desc">Score &ge; 75 / 100</span>
          </div>
          <div className="metric-card">
            <span className="metric-title">Data Quality Health</span>
            <span className="metric-value" style={{ color: batchData.avg_quality_score >= 80 ? '#34d399' : '#fbbf24' }}>
              {batchData.avg_quality_score}%
            </span>
            <span className="metric-desc">Avg hygiene & validity score</span>
          </div>
        </div>
      )}

      {/* Configuration & Input Section */}
      <div className="card">
        <div className="card-header">
          <h2 className="card-title">Ingestion & Scoring Parameters</h2>
          <button className="btn btn-sm" onClick={() => setShowConfig(!showConfig)}>
            {showConfig ? 'Hide ICP Weights ▲' : 'Configure ICP Criteria ▼'}
          </button>
        </div>

        {showConfig && (
          <div style={{ marginBottom: '1.25rem', paddingBottom: '1rem', borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
            <div className="config-grid">
              <div className="config-item">
                <label>Title Seniority Weight: {config.weight_seniority}%</label>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={config.weight_seniority}
                  onChange={(e) => setConfig({ ...config, weight_seniority: e.target.value })}
                />
              </div>
              <div className="config-item">
                <label>Target Industry Weight: {config.weight_industry}%</label>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={config.weight_industry}
                  onChange={(e) => setConfig({ ...config, weight_industry: e.target.value })}
                />
              </div>
              <div className="config-item">
                <label>Company Size Weight: {config.weight_size}%</label>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={config.weight_size}
                  onChange={(e) => setConfig({ ...config, weight_size: e.target.value })}
                />
              </div>
              <div className="config-item">
                <label>Ideal Org Size (Min - Max Employees)</label>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <input
                    type="number"
                    style={{ width: '80px' }}
                    value={config.min_company_size}
                    onChange={(e) => setConfig({ ...config, min_company_size: e.target.value })}
                  />
                  <span style={{ alignSelf: 'center', color: '#94a3b8' }}>to</span>
                  <input
                    type="number"
                    style={{ width: '90px' }}
                    value={config.max_company_size}
                    onChange={(e) => setConfig({ ...config, max_company_size: e.target.value })}
                  />
                </div>
              </div>
            </div>
          </div>
        )}

        <div className="input-area">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
            <span style={{ fontSize: '0.85rem', color: '#94a3b8' }}>
              Upload lead CSV from SaaSQuatch / scraper, or paste CSV rows below:
            </span>
            <input 
              type="file" 
              accept=".csv" 
              onChange={handleFileUpload} 
              style={{ fontSize: '0.8rem', color: '#94a3b8' }} 
            />
          </div>
          <textarea
            rows={4}
            value={csvText}
            onChange={(e) => setCsvText(e.target.value)}
            placeholder="Paste scraped CSV with columns: first_name, last_name, title, company, domain, email, industry, company_size..."
          />
        </div>
      </div>

      {/* Results Table Section */}
      {batchData && (
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">
              Prioritized & Cleaned Leads ({displayedLeads.length})
            </h2>
            
            {/* Export Controls */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
              <label style={{ fontSize: '0.8rem', color: '#cbd5e1', display: 'flex', alignItems: 'center', gap: '0.3rem', cursor: 'pointer' }}>
                <input 
                  type="checkbox" 
                  checked={excludeDuplicatesInExport} 
                  onChange={(e) => setExcludeDuplicatesInExport(e.target.checked)} 
                />
                Exclude Duplicates
              </label>
              <button className="btn btn-success btn-sm" onClick={() => handleExport('hubspot')}>
                📥 Export HubSpot CSV
              </button>
              <button className="btn btn-sm" onClick={() => handleExport('salesforce')}>
                📥 Export Salesforce CSV
              </button>
            </div>
          </div>

          {/* Table Filters & Search */}
          <div className="table-controls">
            <div className="filter-btn-group">
              <button 
                className={`filter-btn ${filterMode === 'unique' ? 'active' : ''}`}
                onClick={() => setFilterMode('unique')}
              >
                Unique Primary Leads ({batchData.unique_leads})
              </button>
              <button 
                className={`filter-btn ${filterMode === 'tier1' ? 'active' : ''}`}
                onClick={() => setFilterMode('tier1')}
              >
                Tier 1 High Fit ({batchData.high_fit_leads})
              </button>
              <button 
                className={`filter-btn ${filterMode === 'duplicates' ? 'active' : ''}`}
                onClick={() => setFilterMode('duplicates')}
              >
                Duplicates Only ({batchData.duplicate_leads})
              </button>
              <button 
                className={`filter-btn ${filterMode === 'issues' ? 'active' : ''}`}
                onClick={() => setFilterMode('issues')}
              >
                Data Hygiene Flags
              </button>
              <button 
                className={`filter-btn ${filterMode === 'all' ? 'active' : ''}`}
                onClick={() => setFilterMode('all')}
              >
                All Raw ({batchData.total_leads})
              </button>
            </div>

            <input
              type="text"
              className="search-input"
              placeholder="Search by name, company, title, domain..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>

          {/* Leads Table */}
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th onClick={() => toggleSort('icp_score')}>
                    ICP Score {sortBy === 'icp_score' ? (sortOrder === 'desc' ? '▼' : '▲') : ''}
                  </th>
                  <th onClick={() => toggleSort('name')}>
                    Contact & Title {sortBy === 'name' ? (sortOrder === 'desc' ? '▼' : '▲') : ''}
                  </th>
                  <th onClick={() => toggleSort('company')}>
                    Company & Domain {sortBy === 'company' ? (sortOrder === 'desc' ? '▼' : '▲') : ''}
                  </th>
                  <th>Contact Email</th>
                  <th>Industry & Scale</th>
                  <th onClick={() => toggleSort('data_quality_score')}>
                    Hygiene Health {sortBy === 'data_quality_score' ? (sortOrder === 'desc' ? '▼' : '▲') : ''}
                  </th>
                  <th>Deduplication / Status</th>
                </tr>
              </thead>
              <tbody>
                {displayedLeads.length === 0 ? (
                  <tr>
                    <td colSpan="7" style={{ textAlign: 'center', padding: '2rem', color: '#94a3b8' }}>
                      No leads match current filter criteria.
                    </td>
                  </tr>
                ) : (
                  displayedLeads.map((lead) => {
                    const tierClass = lead.icp_score >= 75 
                      ? 'score-tier-1' 
                      : (lead.icp_score >= 50 ? 'score-tier-2' : 'score-tier-3');

                    return (
                      <tr key={lead.id} className={lead.is_duplicate ? 'duplicate-row' : ''}>
                        {/* Score Column */}
                        <td>
                          <div className={`score-badge ${tierClass}`}>
                            {lead.icp_score} / 100
                          </div>
                          <div className="breakdown-hint" title={lead.score_rationale}>
                            {lead.icp_tier}
                          </div>
                        </td>

                        {/* Contact Name & Title */}
                        <td>
                          <div className="lead-name">
                            {lead.first_name} {lead.last_name || '(No Name)'}
                          </div>
                          <div className="lead-title">
                            {lead.title || 'Unknown Title'}
                          </div>
                        </td>

                        {/* Company & Domain */}
                        <td>
                          <div className="lead-company">{lead.company || 'Unknown Company'}</div>
                          {lead.domain ? (
                            <a 
                              href={`https://${lead.domain}`} 
                              target="_blank" 
                              rel="noreferrer" 
                              className="lead-domain"
                            >
                              {lead.domain}
                            </a>
                          ) : (
                            <span style={{ color: '#ef4444', fontSize: '0.75rem' }}>No domain</span>
                          )}
                        </td>

                        {/* Email with hygiene indicators */}
                        <td>
                          <div style={{ fontFamily: 'monospace', fontSize: '0.8rem', color: lead.email ? '#e2e8f0' : '#ef4444' }}>
                            {lead.email || 'missing@email.com'}
                          </div>
                          <div style={{ marginTop: '0.2rem' }}>
                            {lead.is_role_based_email && (
                              <span className="pill pill-role">Role Account</span>
                            )}
                            {!lead.is_valid_email && (
                              <span className="pill pill-issue">Invalid Email</span>
                            )}
                            {lead.is_valid_email && !lead.is_role_based_email && (
                              <span className="pill pill-clean">Verified</span>
                            )}
                          </div>
                        </td>

                        {/* Industry & Company Size */}
                        <td>
                          <div style={{ fontSize: '0.8rem', color: '#cbd5e1' }}>{lead.industry || 'General'}</div>
                          <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                            {lead.company_size ? `${lead.company_size} employees` : 'Size unlisted'}
                          </div>
                        </td>

                        {/* Quality Score */}
                        <td>
                          <div style={{ fontWeight: '600', color: lead.data_quality_score >= 80 ? '#34d399' : '#fbbf24' }}>
                            {lead.data_quality_score}%
                          </div>
                          {lead.quality_issues && lead.quality_issues.length > 0 ? (
                            <div className="breakdown-hint" style={{ color: '#f87171' }}>
                              {lead.quality_issues[0]}
                              {lead.quality_issues.length > 1 && ` (+${lead.quality_issues.length - 1} more)`}
                            </div>
                          ) : (
                            <div className="breakdown-hint" style={{ color: '#34d399' }}>Clean record</div>
                          )}
                        </td>

                        {/* Deduplication Status */}
                        <td>
                          {lead.is_duplicate ? (
                            <div>
                              <span className="pill pill-dup">Duplicate</span>
                              <div className="breakdown-hint" style={{ color: '#f87171' }}>
                                {lead.duplicate_reason || 'Duplicate contact'}
                              </div>
                            </div>
                          ) : (
                            <span className="pill pill-clean">Primary Lead</span>
                          )}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
