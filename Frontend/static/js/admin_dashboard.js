/* Charts for the admin sales dashboard (CV57).

   The data arrives in two <script type="application/json"> blocks rendered
   by the view, so this file holds no figures of its own - the previous
   version had a hard-coded 7-day series and a fixed 45/35/12/8 donut that
   never changed no matter what was in the database. */

document.addEventListener('DOMContentLoaded', function () {
  if (typeof Chart === 'undefined') return;

  var GRID = '#e5e7eb';
  var TEXT = '#6b7280';
  var PALETTE = ['#1435c3', '#0a8a3c', '#e39b00', '#a855f7', '#0ea5e9', '#e30019'];

  function readJson(id) {
    var el = document.getElementById(id);
    if (!el) return null;
    try {
      return JSON.parse(el.textContent);
    } catch (e) {
      return null;
    }
  }

  function compactVnd(value) {
    if (value >= 1000000) return (value / 1000000).toFixed(1).replace(/\.0$/, '') + 'M';
    if (value >= 1000) return Math.round(value / 1000) + 'K';
    return value;
  }

  function fullVnd(value) {
    return new Intl.NumberFormat('vi-VN').format(value) + ' ₫';
  }

  var revenue = readJson('revenue-data');
  var revenueCanvas = document.getElementById('revenueChart');
  if (revenue && revenueCanvas) {
    new Chart(revenueCanvas, {
      type: 'line',
      data: {
        labels: revenue.labels,
        datasets: [{
          label: 'Revenue',
          data: revenue.values,
          borderColor: PALETTE[0],
          backgroundColor: 'rgba(20, 53, 195, 0.10)',
          borderWidth: 2,
          fill: true,
          tension: 0.35,
          pointBackgroundColor: PALETTE[0],
          pointHoverRadius: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function (ctx) { return fullVnd(ctx.parsed.y); }
            }
          }
        },
        scales: {
          x: { grid: { color: GRID }, ticks: { color: TEXT } },
          y: {
            beginAtZero: true,
            grid: { color: GRID },
            ticks: { color: TEXT, callback: compactVnd }
          }
        }
      }
    });
  }

  var category = readJson('category-data');
  var categoryCanvas = document.getElementById('categoryChart');
  if (category && categoryCanvas && category.labels.length) {
    new Chart(categoryCanvas, {
      type: 'doughnut',
      data: {
        labels: category.labels,
        datasets: [{
          data: category.values,
          backgroundColor: category.labels.map(function (_, i) { return PALETTE[i % PALETTE.length]; }),
          borderWidth: 0
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '68%',
        plugins: {
          legend: { position: 'bottom', labels: { color: TEXT, padding: 14, font: { size: 11 } } },
          tooltip: {
            callbacks: {
              label: function (ctx) { return ctx.label + ': ' + fullVnd(ctx.parsed); }
            }
          }
        }
      }
    });
  }
});
