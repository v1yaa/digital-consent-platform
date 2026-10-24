/* app.js – ConsentVault front-end logic */

'use strict';

// -----------------------------------------------------------------------
// Sidebar toggle (mobile)
// -----------------------------------------------------------------------
(function () {
  const toggle = document.getElementById('sidebarToggle');
  const sidebar = document.getElementById('sidebar');
  if (!toggle || !sidebar) return;

  toggle.addEventListener('click', () => {
    sidebar.classList.toggle('open');
  });

  // Close sidebar when clicking outside on mobile
  document.addEventListener('click', (e) => {
    if (sidebar.classList.contains('open') &&
        !sidebar.contains(e.target) &&
        !toggle.contains(e.target)) {
      sidebar.classList.remove('open');
    }
  });
})();

// -----------------------------------------------------------------------
// Auto-dismiss flash alerts after 6 seconds
// -----------------------------------------------------------------------
(function () {
  document.querySelectorAll('.flash-alert').forEach((el) => {
    setTimeout(() => {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(el);
      bsAlert.close();
    }, 6000);
  });
})();

// -----------------------------------------------------------------------
// Dashboard charts (called from index.html script block)
// -----------------------------------------------------------------------
function initDashboardCharts(statusData, purposeData) {
  const COLORS = {
    active:  '#22c55e',
    expired: '#f59e0b',
    revoked: '#ef4444',
    denied:  '#6b7280',
  };

  // --- Donut chart ---
  const statusCtx = document.getElementById('statusChart');
  if (statusCtx) {
    new Chart(statusCtx, {
      type: 'doughnut',
      data: {
        labels: statusData.labels,
        datasets: [{
          data: statusData.values,
          backgroundColor: statusData.colors,
          borderWidth: 3,
          borderColor: '#fff',
          hoverBorderWidth: 4,
        }],
      },
      options: {
        cutout: '68%',
        plugins: {
          legend: {
            position: 'right',
            labels: {
              font: { family: "'Inter', sans-serif", size: 12 },
              padding: 16,
              usePointStyle: true,
              pointStyleWidth: 10,
            },
          },
          tooltip: {
            callbacks: {
              label: (ctx) => ` ${ctx.label}: ${ctx.parsed}`,
            },
          },
        },
        animation: { animateRotate: true, duration: 600 },
      },
    });
  }

  // --- Bar chart (purpose breakdown) ---
  const purposeCtx = document.getElementById('purposeChart');
  if (purposeCtx && purposeData.labels.length > 0) {
    new Chart(purposeCtx, {
      type: 'bar',
      data: {
        labels: purposeData.labels,
        datasets: [{
          label: 'Records',
          data: purposeData.values,
          backgroundColor: 'hsla(231,80%,60%,.75)',
          borderColor: 'hsl(231,80%,55%)',
          borderWidth: 1.5,
          borderRadius: 6,
        }],
      },
      options: {
        plugins: {
          legend: { display: false },
        },
        scales: {
          y: {
            beginAtZero: true,
            ticks: { precision: 0, font: { family: "'Inter', sans-serif", size: 11 } },
            grid: { color: 'rgba(0,0,0,.05)' },
          },
          x: {
            ticks: { font: { family: "'Inter', sans-serif", size: 11 } },
            grid: { display: false },
          },
        },
        animation: { duration: 500 },
      },
    });
  }
}
