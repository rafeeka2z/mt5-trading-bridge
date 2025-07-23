// Dashboard JavaScript for real-time updates and charts

document.addEventListener('DOMContentLoaded', function() {
    // Initialize activity chart
    initActivityChart();
    
    // Load initial connection status
    updateConnectionStatus();
    
    // Update dashboard data every 30 seconds
    setInterval(function() {
        updateDashboard();
        updateConnectionStatus();
    }, 30000);
});

function initActivityChart() {
    const ctx = document.getElementById('activityChart');
    if (!ctx) return;
    
    // Initialize with empty data
    const chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Alerts',
                data: [],
                borderColor: 'rgb(75, 192, 192)',
                backgroundColor: 'rgba(75, 192, 192, 0.1)',
                tension: 0.1,
                fill: true
            }, {
                label: 'Trades',
                data: [],
                borderColor: 'rgb(255, 99, 132)',
                backgroundColor: 'rgba(255, 99, 132, 0.1)',
                tension: 0.1,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                },
                title: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                }
            },
            interaction: {
                intersect: false,
                mode: 'index'
            }
        }
    });
    
    // Load initial data
    loadChartData(chart);
}

function loadChartData(chart) {
    fetch('/api/stats?hours=24')
        .then(response => response.json())
        .then(data => {
            updateChart(chart, data);
        })
        .catch(error => {
            console.error('Error loading chart data:', error);
        });
}

function updateChart(chart, data) {
    const hours = [];
    const alertCounts = [];
    const tradeCounts = [];
    
    // Generate last 24 hours
    for (let i = 23; i >= 0; i--) {
        const hour = new Date();
        hour.setHours(hour.getHours() - i, 0, 0, 0);
        const hourStr = hour.toISOString().slice(0, 13) + ':00';
        const displayHour = hour.getHours().toString().padStart(2, '0') + ':00';
        
        hours.push(displayHour);
        alertCounts.push(data.alerts_by_hour[hourStr] || 0);
        
        // Count trades for this hour (simplified - in real implementation you'd get this from API)
        tradeCounts.push(Math.floor((data.alerts_by_hour[hourStr] || 0) * 0.8)); // Assume 80% alert-to-trade conversion
    }
    
    chart.data.labels = hours;
    chart.data.datasets[0].data = alertCounts;
    chart.data.datasets[1].data = tradeCounts;
    chart.update();
}

function updateDashboard() {
    // This function would typically fetch updated stats and refresh parts of the dashboard
    // For now, we'll just update the connection status
    updateConnectionStatus();
}

function updateConnectionStatus() {
    fetch('/api/connection-status')
        .then(response => response.json())
        .then(data => {
            const statusElement = document.getElementById('connection-status');
            const accountInfoElement = document.getElementById('account-info');
            const loginElement = document.getElementById('account-login');
            const serverElement = document.getElementById('account-server');
            const balanceElement = document.getElementById('account-balance');
            
            if (data.connected) {
                statusElement.innerHTML = '<span class="badge bg-success">Connected</span>';
                if (data.account_info) {
                    accountInfoElement.style.display = 'block';
                    loginElement.textContent = data.account_info.login;
                    serverElement.textContent = data.account_info.server;
                    balanceElement.textContent = data.account_info.balance.toFixed(2);
                } else {
                    accountInfoElement.style.display = 'none';
                }
            } else {
                statusElement.innerHTML = '<span class="badge bg-danger">Disconnected</span>';
                accountInfoElement.style.display = 'none';
            }
        })
        .catch(error => {
            console.error('Error updating connection status:', error);
            const statusElement = document.getElementById('connection-status');
            statusElement.innerHTML = '<span class="badge bg-warning">Error</span>';
        });
}

// Utility function to format numbers
function formatNumber(num, decimals = 2) {
    return Number(num).toFixed(decimals);
}

// Utility function to format currency
function formatCurrency(amount, currency = 'USD') {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: currency
    }).format(amount);
}

// Real-time notifications (if WebSocket is implemented)
function initWebSocket() {
    // This would connect to a WebSocket for real-time updates
    // Implementation depends on whether you want real-time features
    console.log('WebSocket connection would be initialized here for real-time updates');
}
