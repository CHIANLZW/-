/** 案例库：默认折叠，OC 仅展示运营合格证批件（不含合同） */

function extractClient(source) {
  const parts = source.replace(/\\/g, '/').split('/');
  const skip = new Set([
    'caac培训资质', '已获证', '未获证', '其他', '运营合格证', '空域文件',
    '合格证', '培训手册', '训练大纲', '训练手册', '运营合格证、',
    '已批复', '公司申请空域基础文件', '空域申请要求', '申报资料', '申请文件',
    '电子保函', '证件整理', '01_培训资质', '02_空域批复', '03_运营合格证', '04_其他材料',
  ]);
  const orgIdx = parts.indexOf('01_培训资质');
  if (orgIdx >= 0 && parts[orgIdx + 1]) return parts[orgIdx + 1];
  const ocIdx = parts.indexOf('03_运营合格证');
  if (ocIdx >= 0 && parts[ocIdx + 1]) return parts[ocIdx + 1];
  const licensedIdx = parts.indexOf('已获证');
  if (licensedIdx >= 0 && parts[licensedIdx + 1]) {
    return parts[licensedIdx + 1].replace(/资料$/, '');
  }
  for (const part of parts) {
    const t = part.trim();
    if (!t || skip.has(t)) continue;
    if (/\.(pdf|jpg|jpeg|png|webp)$/i.test(t)) continue;
    if (t.length < 4) continue;
    if (/^[\d._\-]+$/.test(t)) continue;
    return t.replace(/\s*资料$/, '').replace(/\s*运营合格证$/, '');
  }
  return '其他案例';
}

function normalizeClient(name) {
  return name
    .replace(/^[\d._\-]+/, '')
    .replace(/\s*运营合格证$/, '')
    .replace(/\s*资料$/, '')
    .trim();
}

function isOcCertificate(item) {
  const src = (item.source || '').replace(/\\/g, '/');
  if (/合同|租赁协议|场地合同|培训手册|训练大纲/.test(src)) return false;
  return /\/运营合格证\//.test(src) || /03_运营合格证\//.test(src);
}

function dedupeByClient(items, preferPath = '证件整理') {
  const best = new Map();
  items.forEach((item) => {
    const client = clientKey(item.source);
    const score =
      (item.source.includes(preferPath) ? 4 : 0) +
      (item.source.includes('03_运营合格证') ? 3 : 0) +
      (item.file.endsWith('.jpg') ? 1 : 0);
    const prev = best.get(client);
    if (!prev || score > prev.score) best.set(client, { item, score });
  });
  return [...best.values()].map((v) => v.item).sort((a, b) =>
    clientKey(a.source).localeCompare(clientKey(b.source), 'zh-CN')
  );
}

function groupByMatcher(items, matchers) {
  const buckets = matchers.map((m) => ({ ...m, items: [] }));
  const fallback = buckets[buckets.length - 1];
  items.forEach((item) => {
    const hit = buckets.find((b) => b.match && b.match.test(item.title + item.source));
    (hit || fallback).items.push(item);
  });
  return buckets.filter((b) => b.items.length);
}

function clientKey(source) {
  const raw = normalizeClient(extractClient(source));
  return window.ClientDisplay ? ClientDisplay.resolveAlias(raw) : raw;
}

function clientLabel(source) {
  const raw = normalizeClient(extractClient(source));
  return window.ClientDisplay ? ClientDisplay.format(raw) : raw;
}

function renderGallery(items, tag) {
  return `<div class="doc-gallery">${items
    .map(
      (item) => {
        const label = clientLabel(item.source);
        return `
    <article class="doc-item">
      <div class="doc-item__frame">
        <img src="${item.file}" alt="${label}" loading="lazy" data-lightbox>
      </div>
      <div class="doc-item__meta">
        <span class="doc-item__tag">${tag}</span>
        <h4 class="doc-item__title">${label}</h4>
      </div>
    </article>`;
      }
    )
    .join('')}</div>`;
}

function renderNestedAccordions(items, tag) {
  if (!items.length) return '<p class="sector-note">暂无案例。</p>';
  const byClient = {};
  items.forEach((item) => {
    const key = clientKey(item.source);
    if (!byClient[key]) byClient[key] = { label: clientLabel(item.source), items: [] };
    byClient[key].items.push(item);
  });
  return Object.entries(byClient)
    .sort((a, b) => a[1].label.localeCompare(b[1].label, 'zh-CN'))
    .map(
      ([, { label, items: list }]) => `
    <details class="accordion__item accordion__item--nested">
      <summary class="accordion__summary">
        <span class="accordion__title">${label}</span>
        <span class="accordion__meta">${list.length} 份</span>
      </summary>
      <div class="accordion__body">${renderGallery(list, tag)}</div>
    </details>`
    )
    .join('');
}

function renderAccordionGroup({ id, title, count, body }) {
  return `
  <details class="accordion__item" id="${id}">
    <summary class="accordion__summary">
      <span class="accordion__title">${title}</span>
      <span class="accordion__meta">${count} 项</span>
    </summary>
    <div class="accordion__body"><div class="accordion">${body}</div></div>
  </details>`;
}

const SECTOR_LOADERS = {
  training: {
    root: 'credentials-training-root',
    tag: 'Training',
    matchers: [
      { id: 'train-cert', title: '培训合格证', match: /培训合格证|合格证申请书|合格证/ },
      { id: 'train-outline', title: '训练大纲', match: /训练大纲/ },
      { id: 'train-manual', title: '培训 / 训练手册', match: /培训手册|训练手册/ },
      { id: 'train-other', title: '其他培训材料', match: null },
    ],
  },
  operation: {
    root: 'credentials-operation-root',
    tag: 'OC',
    layout: 'folder',
  },
  airspace: {
    root: 'credentials-airspace-root',
    tag: 'Airspace',
    flat: true,
  },
};

async function loadCredentials() {
  const needsLoad = Object.values(SECTOR_LOADERS).some((c) => document.getElementById(c.root));
  if (!needsLoad) return;

  if (window.ClientDisplay) await ClientDisplay.load();

  try {
    const res = await fetch(typeof assetUrl === 'function' ? assetUrl('assets/data/credentials-manifest.json') : 'assets/data/credentials-manifest.json');
    const data = await res.json();

    Object.entries(SECTOR_LOADERS).forEach(([key, cfg]) => {
      const root = document.getElementById(cfg.root);
      if (!root || !data[key]) return;

      if (cfg.layout === 'folder') {
        const items = dedupeByClient(data[key].filter(isOcCertificate));
        root.innerHTML = renderNestedAccordions(items, cfg.tag);
        const meta = document.getElementById('credentials-operation-meta');
        if (meta) meta.textContent = `${items.length} 家`;
      } else if (cfg.flat) {
        root.innerHTML = renderNestedAccordions(data[key], cfg.tag);
      } else {
        const groups = groupByMatcher(data[key], cfg.matchers);
        root.innerHTML = groups
          .map((g) =>
            renderAccordionGroup({
              id: g.id,
              title: g.title,
              count: g.items.length,
              body: renderNestedAccordions(g.items, cfg.tag),
            })
          )
          .join('');
      }

      root.querySelectorAll('.accordion__item, .doc-item').forEach((el) => {
        el.classList.add('fade-in', 'visible');
      });
    });

    initLightbox();
  } catch (err) {
    console.error('Failed to load credentials manifest', err);
  }
}

function initLightbox() {
  let lightbox = document.getElementById('doc-lightbox');
  if (!lightbox) {
    lightbox = document.createElement('div');
    lightbox.id = 'doc-lightbox';
    lightbox.className = 'lightbox';
    lightbox.innerHTML =
      '<button class="lightbox__close" aria-label="关闭">&times;</button><img class="lightbox__img" alt="">';
    document.body.appendChild(lightbox);

    lightbox.addEventListener('click', (e) => {
      if (e.target === lightbox || e.target.classList.contains('lightbox__close')) {
        lightbox.classList.remove('open');
      }
    });
  }

  const img = lightbox.querySelector('.lightbox__img');
  document.querySelectorAll('[data-lightbox]').forEach((thumb) => {
    if (thumb.dataset.lbBound) return;
    thumb.dataset.lbBound = '1';
    thumb.addEventListener('click', () => {
      img.src = thumb.src;
      img.alt = thumb.alt;
      lightbox.classList.add('open');
    });
  });
}

document.addEventListener('DOMContentLoaded', loadCredentials);
