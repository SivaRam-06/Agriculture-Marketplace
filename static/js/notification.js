document.addEventListener('DOMContentLoaded', () => {
  fetch('/api/notifications').then((res) => res.json()).then((data) => {
    if (data.length) {
      const bell = document.querySelector('[href="/notifications"]');
      if (bell) {
        bell.setAttribute('title', `${data.length} new notifications`);
      }
    }
  });
});
