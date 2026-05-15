(() => {
  const slides = Array.from(document.querySelectorAll('.slide'));
  const progress = document.querySelector('#deck-progress span');
  const counter = document.querySelector('#deck-counter');
  const prevButton = document.querySelector('#deck-prev');
  const nextButton = document.querySelector('#deck-next');
  let current = 0;
  function clamp(index) { return Math.max(0, Math.min(slides.length - 1, index)); }
  function updateHash(index) {
    const target = `#/${index + 1}`;
    if (window.location.hash !== target) history.replaceState(null, '', target);
  }
  function render() {
    slides.forEach((slide, index) => {
      slide.classList.toggle('active', index === current);
      slide.setAttribute('aria-hidden', index === current ? 'false' : 'true');
    });
    if (progress) progress.style.width = `${((current + 1) / Math.max(slides.length, 1)) * 100}%`;
    if (counter) counter.textContent = `${current + 1} / ${slides.length}`;
    updateHash(current);
  }
  function goTo(index) { current = clamp(index); render(); }
  function next() { goTo(current + 1); }
  function prev() { goTo(current - 1); }
  function fromHash() {
    const match = window.location.hash.match(/^#\/(\d+)$/);
    if (match) current = clamp(Number(match[1]) - 1);
  }
  function toggleFullscreen() {
    if (!document.fullscreenElement) document.documentElement.requestFullscreen?.();
    else document.exitFullscreen?.();
  }
  document.addEventListener('keydown', (event) => {
    const key = event.key;
    if (['ArrowRight', ' ', 'PageDown'].includes(key)) { event.preventDefault(); next(); }
    else if (['ArrowLeft', 'PageUp'].includes(key)) { event.preventDefault(); prev(); }
    else if (key === 'Home') { event.preventDefault(); goTo(0); }
    else if (key === 'End') { event.preventDefault(); goTo(slides.length - 1); }
    else if (key.toLowerCase() === 'f') { event.preventDefault(); toggleFullscreen(); }
  });
  document.addEventListener('click', (event) => {
    const selection = window.getSelection?.().toString();
    if (selection) return;
    if (event.target.closest('a, button, input, textarea, select')) return;
    if (event.clientX < window.innerWidth * 0.33) prev();
    else next();
  });
  prevButton?.addEventListener('click', (event) => { event.stopPropagation(); prev(); });
  nextButton?.addEventListener('click', (event) => { event.stopPropagation(); next(); });
  window.addEventListener('hashchange', () => { fromHash(); render(); });
  fromHash();
  render();
})();
