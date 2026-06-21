/** 加载 site-materials-manifest.json，按板块注入补充素材 */

const SECTION_ROOTS = {
  training: 'site-materials-training',
  operation: 'site-materials-operation',
  airspace: 'site-materials-airspace',
  airworthiness: 'site-materials-airworthiness',
};

function renderGallery(items) {
  return `<div class="doc-gallery">${items
    .map((item) => {
      if (item.media_type === 'video') {
        return `
        <article class="doc-item">
          <div class="doc-item__frame">
            <video src="${item.file}" controls muted playsinline preload="metadata"></video>
          </div>
          <div class="doc-item__meta">
            <span class="doc-item__tag">${item.doc_type || 'Video'}</span>
            <h4 class="doc-item__title">${item.title}</h4>
          </div>
        </article>`;
      }
      if (item.media_type === 'text') {
        return `
        <article class="doc-item doc-item--text">
          <div class="doc-item__meta">
            <span class="doc-item__tag">${item.doc_type || '政策'}</span>
            <h4 class="doc-item__title">${item.title}</h4>
            <p class="doc-item__source">文字素材已入库，见法规条目。</p>
          </div>
        </article>`;
      }
      return `
      <article class="doc-item">
        <div class="doc-item__frame">
          <img src="${item.file}" alt="${item.title}" loading="lazy" data-lightbox>
        </div>
        <div class="doc-item__meta">
          <span class="doc-item__tag">${item.doc_type || 'Material'}</span>
          <h4 class="doc-item__title">${item.title}</h4>
        </div>
      </article>`;
    })
    .join('')}</div>`;
}

function renderRegulations(items) {
  return items
    .map(
      (item) => `
    <div class="doc-card">
      <p class="doc-card__tag">${item.doc_type || '政策解读'}</p>
      <h4 class="doc-card__title">${item.title}</h4>
      <p class="doc-card__desc">${(item.body || '').slice(0, 180)}${(item.body || '').length > 180 ? '…' : ''}</p>
    </div>`
    )
    .join('');
}

async function loadSiteMaterials() {
  const roots = Object.values(SECTION_ROOTS).map((id) => document.getElementById(id));
  if (!roots.some(Boolean)) return;

  try {
    const res = await fetch('assets/data/site-materials-manifest.json');
    const data = await res.json();
    const byCat = {};
    (data.items || []).forEach((item) => {
      if (!byCat[item.category]) byCat[item.category] = [];
      byCat[item.category].push(item);
    });

    Object.entries(SECTION_ROOTS).forEach(([cat, rootId]) => {
      const root = document.getElementById(rootId);
      if (!root) return;
      const items = byCat[cat] || [];
      if (!items.length) {
        root.closest('details')?.remove();
        return;
      }

      const visuals = items.filter((i) => i.media_type !== 'text');
      const texts = items.filter((i) => i.media_type === 'text');

      root.innerHTML = `
        ${visuals.length ? renderGallery(visuals) : ''}
        ${texts.length ? `<div class="doc-grid" style="margin-top:1.5rem">${texts
          .map(
            (t) => `<div class="doc-card"><p class="doc-card__tag">${t.doc_type}</p><h4 class="doc-card__title">${t.title}</h4><p class="doc-card__desc">${(t.body || '').replace(/\s+/g, ' ').slice(0, 220)}${(t.body || '').length > 220 ? '…' : ''}</p></div>`
          )
          .join('')}</div>` : ''}`;

      root.querySelectorAll('.doc-item, .doc-card').forEach((el) => el.classList.add('fade-in', 'visible'));
    });

    if (typeof initLightbox === 'function') initLightbox();
  } catch (err) {
    console.error('Failed to load site materials', err);
  }
}

document.addEventListener('DOMContentLoaded', loadSiteMaterials);
