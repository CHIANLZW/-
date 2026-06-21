/** 空域板块：材料清单与客户名录（区域 + 状态） */
async function loadAirspaceOverview() {
  const materialsRoot = document.getElementById('airspace-materials');
  const approvedRoot = document.getElementById('airspace-approved-list');
  const progressRoot = document.getElementById('airspace-progress-list');
  const metaApproved = document.getElementById('airspace-approved-meta');
  const metaProgress = document.getElementById('airspace-progress-meta');
  if (!materialsRoot && !approvedRoot) return;

  if (window.ClientDisplay) await ClientDisplay.load();

  try {
    const res = await fetch(typeof assetUrl === 'function' ? assetUrl('assets/data/airspace-companies.json') : 'assets/data/airspace-companies.json');
    const data = await res.json();

    if (materialsRoot && data.materials) {
      materialsRoot.innerHTML = data.materials.map((item) => `<li>${item}</li>`).join('');
    }

    if (approvedRoot) {
      approvedRoot.innerHTML = renderCompanyTable(data.approved || []);
      if (metaApproved) metaApproved.textContent = `${(data.approved || []).length} 家`;
    }

    if (progressRoot) {
      progressRoot.innerHTML = renderCompanyTable(data.inProgress || []);
      if (metaProgress) metaProgress.textContent = `${(data.inProgress || []).length} 家`;
    }
  } catch (err) {
    console.error('Failed to load airspace companies', err);
  }
}

function renderCompanyTable(items) {
  if (!items.length) return '<p class="sector-note">暂无记录</p>';
  const label = (name) => (window.ClientDisplay ? ClientDisplay.format(name) : name);
  const rows = items
    .map(
      (item) => `
    <tr>
      <td>${label(item.company)}</td>
      <td><span class="company-table__region">${item.region}</span></td>
      <td><span class="company-table__status company-table__status--${statusClass(item.status)}">${item.status}</span></td>
    </tr>`
    )
    .join('');

  return `
  <div class="company-table-wrap">
    <table class="company-table company-table--simple">
      <thead>
        <tr>
          <th>企业 / 机构全称</th>
          <th>区域</th>
          <th>状态</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  </div>`;
}

function statusClass(status) {
  if (status === '已批复') return 'done';
  if (status.includes('齐备')) return 'ready';
  return 'pending';
}

document.addEventListener('DOMContentLoaded', loadAirspaceOverview);
