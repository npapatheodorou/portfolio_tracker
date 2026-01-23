// ============== UTILITIES ==============

function formatNumber(num, dec = 2) {
    if (num === null || num === undefined || isNaN(num)) return '0.00';
    const abs = Math.abs(num);
    if (abs >= 1e9) return (num / 1e9).toFixed(2) + 'B';
    if (abs >= 1e6) return (num / 1e6).toFixed(2) + 'M';
    if (abs >= 1e3) return num.toLocaleString('en-US', { minimumFractionDigits: dec, maximumFractionDigits: dec });
    return num.toFixed(dec);
}

function formatDate(str) {
    if (!str) return 'N/A';
    return new Date(str).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function generateColors(n) {
    const c = ['#6366f1','#8b5cf6','#ec4899','#ef4444','#f59e0b','#10b981','#14b8a6','#06b6d4','#3b82f6','#84cc16','#f97316','#0ea5e9','#a855f7','#22c55e','#eab308'];
    return c.slice(0, Math.min(n, c.length));
}

// ============== TOAST ==============

function showToast(msg, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    const icons = { success: 'fa-check-circle', error: 'fa-exclamation-circle', info: 'fa-info-circle', warning: 'fa-exclamation-triangle' };
    toast.innerHTML = `<i class="fas ${icons[type] || icons.info}"></i><span>${msg}</span>`;
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// ============== MODAL ==============

function openModal(id) {
    const m = document.getElementById(id);
    if (m) { 
        m.classList.add('active'); 
        document.body.style.overflow = 'hidden'; 
    }
}

function closeModal(id) {
    const m = document.getElementById(id);
    if (m) { 
        m.classList.remove('active'); 
        document.body.style.overflow = ''; 
    }
}

document.addEventListener('click', function(e) {
    if (e.target.classList.contains('modal-overlay')) {
        const modal = e.target.closest('.modal');
        if (modal) {
            modal.classList.remove('active');
            document.body.style.overflow = '';
        }
    }
});

document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        document.querySelectorAll('.modal.active').forEach(m => m.classList.remove('active'));
        document.body.style.overflow = '';
    }
});

// ============== THEME ==============

document.addEventListener('DOMContentLoaded', function() {
    const themeBtn = document.getElementById('themeToggle');
    if (themeBtn) {
        const saved = localStorage.getItem('theme') || 'dark';
        document.documentElement.setAttribute('data-theme', saved);
        const icon = themeBtn.querySelector('i');
        if (icon) icon.className = saved === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
        
        themeBtn.addEventListener('click', function() {
            const current = document.documentElement.getAttribute('data-theme');
            const next = current === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', next);
            localStorage.setItem('theme', next);
            const icon = themeBtn.querySelector('i');
            if (icon) icon.className = next === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
            
            // Update chart colors when theme changes
            updateChartThemeColors(next);
        });
    }
    
    // Setup coin search
    setupCoinSearch();
    
    // Setup global buttons
    setupGlobalButtons();
});

// ============== CHART THEME COLORS ==============

function updateChartThemeColors(theme) {
    const textColor = theme === 'dark' ? '#f1f5f9' : '#0f172a';
    const gridColor = theme === 'dark' ? '#334155' : '#e2e8f0';
    
    // Update dashboard charts if they exist
    if (typeof allocationPieChart !== 'undefined' && allocationPieChart) {
        if (allocationPieChart.options.plugins.legend) {
            allocationPieChart.options.plugins.legend.labels.color = textColor;
        }
        allocationPieChart.update();
    }
    
    if (typeof allocationBarChart !== 'undefined' && allocationBarChart) {
        if (allocationBarChart.options.scales) {
            allocationBarChart.options.scales.x.ticks.color = textColor;
            allocationBarChart.options.scales.x.grid.color = gridColor;
            allocationBarChart.options.scales.y.ticks.color = textColor;
            allocationBarChart.options.scales.y.grid.color = gridColor;
        }
        allocationBarChart.update();
    }
    
    if (typeof valueChart !== 'undefined' && valueChart) {
        if (valueChart.options.plugins.legend) {
            valueChart.options.plugins.legend.labels.color = textColor;
        }
        if (valueChart.options.scales) {
            valueChart.options.scales.x.ticks.color = textColor;
            valueChart.options.scales.x.grid.color = gridColor;
            valueChart.options.scales.y.ticks.color = textColor;
            valueChart.options.scales.y.grid.color = gridColor;
        }
        valueChart.update();
    }
    
    // Update portfolio page charts if they exist
    if (typeof allocationChart !== 'undefined' && allocationChart) {
        if (allocationChart.options.plugins.legend) {
            allocationChart.options.plugins.legend.labels.color = textColor;
        }
        allocationChart.update();
    }
    
    if (typeof perfChart !== 'undefined' && perfChart) {
        if (perfChart.options.scales) {
            perfChart.options.scales.x.ticks.color = textColor;
            perfChart.options.scales.y.ticks.color = textColor;
            perfChart.options.scales.y.grid.color = gridColor;
        }
        perfChart.update();
    }
    
    // Update comparison chart if it exists
    if (typeof compChart !== 'undefined' && compChart) {
        if (compChart.options.plugins.legend) {
            compChart.options.plugins.legend.labels.color = textColor;
        }
        if (compChart.options.scales) {
            compChart.options.scales.x.ticks.color = textColor;
            compChart.options.scales.x.grid.color = gridColor;
            compChart.options.scales.y.ticks.color = textColor;
            compChart.options.scales.y.grid.color = gridColor;
        }
        compChart.update();
    }
}

// ============== COIN SEARCH ==============

function setupCoinSearch() {
    const coinSearchInput = document.getElementById('coinSearch');
    const coinSearchResults = document.getElementById('coinSearchResults');
    
    if (!coinSearchInput || !coinSearchResults) return;
    
    let searchTimeout;
    
    coinSearchInput.addEventListener('input', function(e) {
        clearTimeout(searchTimeout);
        const q = e.target.value.trim();
        
        if (q.length < 2) {
            coinSearchResults.classList.remove('active');
            return;
        }
        
        coinSearchResults.innerHTML = '<div class="search-result-item"><i class="fas fa-spinner fa-spin"></i> Searching...</div>';
        coinSearchResults.classList.add('active');
        
        searchTimeout = setTimeout(async function() {
            try {
                const res = await fetch(`/api/coins/search?q=${encodeURIComponent(q)}`);
                
                if (res.status === 429) {
                    coinSearchResults.innerHTML = '<div class="search-result-item error"><i class="fas fa-exclamation-triangle"></i> Rate limited. Wait and retry.</div>';
                    return;
                }
                
                const data = await res.json();
                
                if (data.error) {
                    coinSearchResults.innerHTML = `<div class="search-result-item error"><i class="fas fa-exclamation-circle"></i> ${data.error}</div>`;
                    return;
                }
                
                if (!Array.isArray(data) || data.length === 0) {
                    coinSearchResults.innerHTML = '<div class="search-result-item">No results</div>';
                    return;
                }
                
                coinSearchResults.innerHTML = data.map(c => `
                    <div class="search-result-item" onclick="selectCoin('${c.id}','${c.symbol}','${(c.name || '').replace(/'/g,"\\'")}','${c.thumb || ''}')">
                        <img src="${c.thumb || ''}" onerror="this.src='https://via.placeholder.com/24'">
                        <div><strong>${c.name}</strong> <span style="color:var(--text-muted)">${(c.symbol || '').toUpperCase()}</span></div>
                    </div>
                `).join('');
            } catch (e) {
                coinSearchResults.innerHTML = '<div class="search-result-item error"><i class="fas fa-exclamation-circle"></i> Error</div>';
            }
        }, 500);
    });
    
    document.addEventListener('click', function(e) {
        if (!e.target.closest('.search-wrapper')) {
            coinSearchResults.classList.remove('active');
        }
    });
}

function selectCoin(id, symbol, name, thumb) {
    document.getElementById('selectedCoinId').value = id;
    document.getElementById('selectedCoinImage').src = thumb || 'https://via.placeholder.com/40';
    document.getElementById('selectedCoinName').textContent = name;
    document.getElementById('selectedCoinSymbol').textContent = (symbol || '').toUpperCase();
    document.getElementById('selectedCoin').style.display = 'flex';
    document.getElementById('coinSearch').value = '';
    document.getElementById('coinSearchResults').classList.remove('active');
}

function clearSelectedCoin() {
    document.getElementById('selectedCoinId').value = '';
    document.getElementById('selectedCoin').style.display = 'none';
}

// ============== GLOBAL BUTTONS ==============

function setupGlobalButtons() {
    // Refresh prices
    const refreshBtn = document.getElementById('refreshPricesBtn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', async function() {
            const icon = refreshBtn.querySelector('i');
            if (icon) icon.classList.add('fa-spin');
            refreshBtn.disabled = true;
            
            try {
                const res = await fetch('/api/refresh-prices', { method: 'POST' });
                const data = await res.json();
                
                if (res.status === 429 || data.rate_limited) {
                    showToast('Rate limited. Wait and retry.', 'warning');
                } else if (data.success) {
                    showToast('Prices refreshed', 'success');
                    // Reload page data if functions exist
                    if (typeof loadPortfolios === 'function') loadPortfolios();
                    if (typeof loadPortfolioData === 'function') loadPortfolioData();
                } else {
                    showToast(data.error || 'Error', 'error');
                }
            } catch (e) {
                showToast('Error', 'error');
            } finally {
                if (icon) icon.classList.remove('fa-spin');
                refreshBtn.disabled = false;
            }
        });
    }
    
    // Take snapshot
    const snapBtn = document.getElementById('takeSnapshotBtn');
    if (snapBtn) {
        snapBtn.addEventListener('click', async function() {
            snapBtn.disabled = true;
            try {
                const res = await fetch('/api/trigger-all-snapshots', { method: 'POST' });
                const data = await res.json();
                if (data.success) {
                    showToast('Snapshots created', 'success');
                } else {
                    showToast(data.error || 'Error', 'error');
                }
            } catch (e) {
                showToast('Error', 'error');
            } finally {
                snapBtn.disabled = false;
            }
        });
    }
}

// ============== CREATE PORTFOLIO ==============

async function submitCreatePortfolio() {
    const nameEl = document.getElementById('portfolioName');
    const descEl = document.getElementById('portfolioDescription');
    const btn = document.getElementById('createPortfolioBtn');
    
    const name = (nameEl.value || '').trim();
    const desc = (descEl.value || '').trim();
    
    if (!name) {
        showToast('Enter portfolio name', 'error');
        return;
    }
    
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creating...';
    
    try {
        const res = await fetch('/api/portfolios', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: name, description: desc })
        });
        
        if (res.ok) {
            const p = await res.json();
            showToast('Portfolio created', 'success');
            closeModal('createPortfolioModal');
            nameEl.value = '';
            descEl.value = '';
            
            if (typeof loadPortfolios === 'function') {
                loadPortfolios();
            } else {
                location.href = `/portfolio/${p.id}`;
            }
        } else {
            const err = await res.json();
            showToast(err.error || 'Error creating', 'error');
        }
    } catch (e) {
        showToast('Error', 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-plus"></i> Create';
    }
}

// ============== ADD HOLDING ==============

async function submitAddHolding() {
    const portfolioId = window.currentPortfolioId;
    const coinId = document.getElementById('selectedCoinId').value;
    const amountEl = document.getElementById('holdingAmount');
    const avgEl = document.getElementById('averageBuyPrice');
    
    const amount = parseFloat(amountEl.value);
    const avg = parseFloat(avgEl.value) || null;
    
    if (!coinId) { 
        showToast('Select a coin', 'error'); 
        return; 
    }
    if (isNaN(amount) || amount <= 0) { 
        showToast('Enter valid amount', 'error'); 
        return; 
    }
    
    try {
        const res = await fetch(`/api/portfolios/${portfolioId}/holdings`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                coin_id: coinId,
                symbol: document.getElementById('selectedCoinSymbol').textContent.toLowerCase(),
                name: document.getElementById('selectedCoinName').textContent,
                amount: amount,
                average_buy_price: avg,
                image_url: document.getElementById('selectedCoinImage').src
            })
        });
        
        const data = await res.json();
        
        if (res.ok && data.success) {
            if (data.rate_limited || data.warning) {
                showToast('Added! ' + (data.warning || 'Price updates later.'), 'warning');
            } else {
                showToast('Holding added', 'success');
            }
            
            closeModal('addHoldingModal');
            clearSelectedCoin();
            amountEl.value = '';
            avgEl.value = '';
            
            if (typeof loadPortfolioData === 'function') loadPortfolioData();
            if (typeof loadPortfolios === 'function') loadPortfolios();
        } else {
            showToast(data.error || 'Error', 'error');
        }
    } catch (e) {
        showToast('Error', 'error');
    }
}