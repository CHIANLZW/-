/** 个人简历 — 导航与移动端菜单 */
document.addEventListener('DOMContentLoaded', () => {
  const toggle = document.querySelector('.cv-nav__toggle');
  const links = document.querySelector('.cv-nav__links');

  if (toggle && links) {
    const setOpen = (open) => {
      toggle.classList.toggle('active', open);
      links.classList.toggle('open', open);
      document.body.classList.toggle('nav-open', open);
    };

    toggle.addEventListener('click', () => setOpen(!links.classList.contains('open')));
    links.querySelectorAll('a').forEach((a) => a.addEventListener('click', () => setOpen(false)));
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') setOpen(false);
    });
  }
});
