let companies = [];
let selected = new Set();

const ICONS = {
  xiaomi: '米',
  alibaba: '阿',
  tencent: '腾',
  ant: '蚂',
  apple: '',
  nvidia: 'N',
  amd: 'D',
  luxshare: '立'
};

function reportUrl(id) {
  return 'report.html?id=' + encodeURIComponent(id);
}

function compareUrl() {
  return 'compare.html?ids=' + [...selected].map(encodeURIComponent).join(',');
}

async function init() {
  const grid = document.getElementById('companyGrid');
  try {
    const res = await fetch('data/companies.json');
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const data = await res.json();
    companies = data.companies || [];
    if (!companies.length) throw new Error('empty');
    renderGrid();
    bindActions();
    const params = new URLSearchParams(location.search);
    if (params.get('select') === 'all') {
      companies.forEach((c) => selected.add(c.id));
      renderGrid();
      updateButtons();
    }
  } catch (err) {
    console.error(err);
    grid.innerHTML =
      '<div class="section"><p class="hint" style="color:var(--neg);margin-bottom:8px">公司数据加载失败</p>' +
      '<p class="hint">请通过网站服务器访问（如 <code>npx serve</code> 或 GitHub Pages），不要直接双击本地 HTML 文件。</p></div>';
    document.getElementById('openCompare').disabled = true;
  }
}

function renderGrid() {
  const grid = document.getElementById('companyGrid');
  grid.innerHTML = companies
    .map(
      (c) => `
    <div class="company-card ${selected.has(c.id) ? 'selected' : ''}" data-id="${c.id}">
      <label class="company-card__check" title="加入对比">
        <input type="checkbox" ${selected.has(c.id) ? 'checked' : ''} aria-label="对比：${c.name}" />
      </label>
      <a class="company-card__link" href="${reportUrl(c.id)}">
        <div class="logo" style="background:${c.color}">${ICONS[c.id] || c.name[0]}</div>
        <h3>${c.name}</h3>
        <div class="ticker">${c.ticker} · ${c.exchange}</div>
        <div class="brief">${c.tagline || ''}</div>
        <div class="company-card__cta">查看完整分析报告 →</div>
        ${c.aliasNote ? `<div class="brief" style="color:#92400e">⚠ ${c.aliasNote}</div>` : ''}
        ${!c.listed ? '<div class="brief" style="color:#92400e">非上市公司</div>' : ''}
      </a>
    </div>
  `
    )
    .join('');

  grid.querySelectorAll('.company-card').forEach((card) => {
    const id = card.dataset.id;
    const cb = card.querySelector('input[type="checkbox"]');
    const label = card.querySelector('.company-card__check');

    label.addEventListener('click', (e) => {
      e.stopPropagation();
    });

    cb.addEventListener('change', () => {
      if (cb.checked) selected.add(id);
      else selected.delete(id);
      card.classList.toggle('selected', cb.checked);
      updateButtons();
    });
  });
}

function updateButtons() {
  const n = selected.size;
  const selCount = document.getElementById('selCount');
  const openCompare = document.getElementById('openCompare');
  if (selCount) selCount.textContent = `已选 ${n} 家（用于对比）`;
  if (openCompare) openCompare.disabled = n < 2;
}

function bindActions() {
  document.getElementById('selectAll').onclick = () => {
    companies.forEach((c) => selected.add(c.id));
    renderGrid();
    updateButtons();
  };
  document.getElementById('clearAll').onclick = () => {
    selected.clear();
    renderGrid();
    updateButtons();
  };
  document.getElementById('openCompare').onclick = () => {
    if (selected.size >= 2) location.href = compareUrl();
  };
}

init();
