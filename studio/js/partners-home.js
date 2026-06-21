/** 首页合作单位：默认展示部分，折叠展开更多 */
const HOME_PARTNERS_VISIBLE = 18;

async function loadHomePartners() {
  const visibleRoot = document.getElementById('partners-preview-visible');
  const moreRoot = document.getElementById('partners-preview-more');
  const intro = document.getElementById('partners-intro-home');
  const fold = document.querySelector('.partners-preview__fold');
  if (!visibleRoot) return;

  await ClientDisplay.load();

  try {
    const res = await fetch(assetUrl('assets/data/partners.json'));
    const data = await res.json();
    const partners = data.partners || [];

    if (intro) {
      intro.innerHTML = `${data.intro || ''}（共 <strong>${data.count || partners.length} 家</strong>，以下为部分展示）`;
    }

    const chips = partners.map(
      (p) =>
        `<span class="partner-chip partner-chip--compact"><span class="partner-chip__name">${ClientDisplay.format(p.name)}</span><span class="partner-chip__region">${p.region || ''}</span></span>`
    );

    visibleRoot.innerHTML = chips.slice(0, HOME_PARTNERS_VISIBLE).join('');
    if (moreRoot) moreRoot.innerHTML = chips.slice(HOME_PARTNERS_VISIBLE).join('');

    if (fold) {
      const rest = partners.length - HOME_PARTNERS_VISIBLE;
      fold.hidden = rest <= 0;
      if (rest > 0) {
        const summary = fold.querySelector('.partners-preview__summary');
        if (summary) summary.textContent = `展开更多（还有 ${rest} 家）`;
      }
    }
  } catch (err) {
    console.error('Failed to load home partners', err);
    visibleRoot.innerHTML = '<p class="sector-note">合作单位加载失败</p>';
  }
}

document.addEventListener('DOMContentLoaded', loadHomePartners);
