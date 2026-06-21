/** 根据 body[data-page] 高亮导航 */
document.addEventListener('DOMContentLoaded', () => {
  const page = document.body.dataset.page;
  if (!page) return;
  document.querySelectorAll('.nav__links a[data-nav], .footer__links a[data-nav]').forEach((a) => {
    if (a.dataset.nav === page) a.classList.add('active');
  });
});
