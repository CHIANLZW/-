/** SpaceX theme: hero video, sector nav scroll spy */
document.addEventListener('DOMContentLoaded', () => {
  initHeroVideo();
  initSectorNavSpy();
});

function initHeroVideo() {
  const hero = document.querySelector('.sx-hero');
  const video = hero?.querySelector('.sx-hero__video');
  if (!hero || !video) return;

  const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const saveData = navigator.connection?.saveData;

  if (prefersReduced || saveData) {
    hero.classList.add('is-static');
    video.remove();
    return;
  }

  video.play().catch(() => {
    hero.classList.add('is-static');
  });
}

function initSectorNavSpy() {
  const sectorNav = document.querySelector('.sector-nav');
  if (!sectorNav) return;

  const links = [...sectorNav.querySelectorAll('a[href^="#"]')];
  const sections = links
    .map((a) => {
      const id = a.getAttribute('href').slice(1);
      return document.getElementById(id);
    })
    .filter(Boolean);

  if (!sections.length) return;

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        const id = entry.target.id;
        links.forEach((link) => {
          link.classList.toggle('is-active', link.getAttribute('href') === `#${id}`);
        });
      });
    },
    { rootMargin: '-40% 0px -45% 0px', threshold: 0 }
  );

  sections.forEach((section) => observer.observe(section));
}
