/** 报告页 UI 交互：阅读进度、目录高亮、区块进入动画 */
(function () {
  function initReadingProgress() {
    const bar = document.querySelector('.read-progress__bar');
    if (!bar) return;
    const onScroll = () => {
      const doc = document.documentElement;
      const scrollTop = doc.scrollTop || document.body.scrollTop;
      const height = doc.scrollHeight - doc.clientHeight;
      bar.style.width = (height > 0 ? (scrollTop / height) * 100 : 0) + '%';
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  function initTocSpy() {
    const links = document.querySelectorAll('.report-toc a[href^="#"]');
    if (!links.length) return;
    const sections = [...links]
      .map((a) => {
        const id = a.getAttribute('href').slice(1);
        const el = document.getElementById(id);
        return el ? { link: a, el } : null;
      })
      .filter(Boolean);

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const id = entry.target.id;
            links.forEach((l) => l.classList.toggle('is-active', l.getAttribute('href') === '#' + id));
          }
        });
      },
      { rootMargin: '-20% 0px -65% 0px', threshold: 0 }
    );
    sections.forEach(({ el }) => observer.observe(el));
  }

  function initReveal() {
    const nodes = document.querySelectorAll('.section, .chief-bar');
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            e.target.classList.add('is-visible');
            io.unobserve(e.target);
          }
        });
      },
      { threshold: 0.06 }
    );
    nodes.forEach((n) => {
      n.classList.add('reveal');
      io.observe(n);
    });
  }

  window.GuandianReportUI = {
    init() {
      initReadingProgress();
      initTocSpy();
      initReveal();
    }
  };
})();
