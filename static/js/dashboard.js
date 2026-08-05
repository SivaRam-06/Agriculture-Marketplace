document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-chart]').forEach((chart) => {
    chart.textContent = 'Chart ready';
  });
});
