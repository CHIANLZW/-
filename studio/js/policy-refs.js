/** 政策与申报材料 — 仅展示文件名、出处与链接，不内嵌影像 */

const POLICY_ROOTS = {
  training_laws: 'policy-refs-training-laws',
  training: 'policy-refs-training',
  airspace: 'policy-refs-airspace',
  operation: 'policy-refs-operation',
  airworthiness: 'policy-refs-airworthiness',
};

function renderRefList(items) {
  if (!items.length) return '<p class="sector-note">暂无参考文件。</p>';
  return `<ul class="ref-list">${items
    .map((item) => {
      const primary = item.url
        ? `<a class="ref-list__title" href="${item.url}" target="_blank" rel="noopener noreferrer">${item.title}</a>`
        : item.local
          ? `<a class="ref-list__title" href="${item.local}" target="_blank" rel="noopener noreferrer">${item.title}</a>`
          : `<span class="ref-list__title">${item.title}</span>`;
      const local =
        item.local && item.url
          ? `<a class="ref-list__local" href="${item.local}" target="_blank" rel="noopener noreferrer">本地存档</a>`
          : '';
      const note = item.note ? `<p class="ref-list__note">${item.note}</p>` : '';
      return `<li class="ref-list__item">
        ${primary}
        <p class="ref-list__source">出处：${item.source}</p>
        ${local}
        ${note}
      </li>`;
    })
    .join('')}</ul>`;
}

async function loadPolicyRefs() {
  const hasRoot = Object.values(POLICY_ROOTS).some((id) => document.getElementById(id));
  if (!hasRoot) return;

  try {
    const res = await fetch(typeof assetUrl === 'function' ? assetUrl('assets/data/policy-references.json') : 'assets/data/policy-references.json');
    const data = await res.json();

    Object.entries(POLICY_ROOTS).forEach(([key, rootId]) => {
      const root = document.getElementById(rootId);
      if (!root) return;
      root.innerHTML = renderRefList(data[key] || []);
    });
  } catch (err) {
    console.error('Failed to load policy references', err);
  }
}

document.addEventListener('DOMContentLoaded', loadPolicyRefs);
