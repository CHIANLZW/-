/** 合作单位名录 */
async function loadPartners() {
  const grid = document.getElementById('partners-grid');
  const intro = document.getElementById('partners-intro');
  const count = document.getElementById('partners-count');
  if (!grid) return;

  if (window.ClientDisplay) await ClientDisplay.load();

  try {
    const res = await fetch(typeof assetUrl === 'function' ? assetUrl('assets/data/partners.json') : 'assets/data/partners.json');
    const data = await res.json();
    if (intro) intro.textContent = data.intro || '';
    if (count) count.textContent = `${data.count || 0} 家`;

    const byRegion = {};
    (data.partners || []).forEach((p) => {
      const r = p.region || '其他';
      if (!byRegion[r]) byRegion[r] = [];
      byRegion[r].push(p);
    });

    const regionOrder = ['重庆', '四川', '广东', '浙江', '江苏', '湖北', '河北', '山东', '甘肃', '陕西', '北京', '其他'];
    const regions = Object.keys(byRegion).sort(
      (a, b) => (regionOrder.indexOf(a) === -1 ? 99 : regionOrder.indexOf(a)) - (regionOrder.indexOf(b) === -1 ? 99 : regionOrder.indexOf(b))
    );

    grid.innerHTML = regions
      .map(
        (region) => `
      <div class="partners-region">
        <h3 class="partners-region__title">${region}</h3>
        <ul class="partners-list">
          ${byRegion[region]
            .map(
              (p) => `
            <li class="partner-chip">
              <span class="partner-chip__name">${window.ClientDisplay ? ClientDisplay.format(p.name) : p.name}</span>
            </li>`
            )
            .join('')}
        </ul>
      </div>`
      )
      .join('');
  } catch (err) {
    console.error('Failed to load partners', err);
    grid.innerHTML = '<p class="accordion__lead">合作单位名录加载失败。</p>';
  }
}

document.addEventListener('DOMContentLoaded', loadPartners);
