/** 合作单位分布地图（SVG） */
const MAP_BOUNDS = { minLng: 73, maxLng: 136, minLat: 17, maxLat: 54 };

function project(lng, lat, width, height) {
  const x = ((lng - MAP_BOUNDS.minLng) / (MAP_BOUNDS.maxLng - MAP_BOUNDS.minLng)) * width;
  const y = height - ((lat - MAP_BOUNDS.minLat) / (MAP_BOUNDS.maxLat - MAP_BOUNDS.minLat)) * height;
  return [x, y];
}

function aggregatePoints(partners) {
  const buckets = new Map();
  partners.forEach((p) => {
    if (p.lng == null || p.lat == null) return;
    const key = `${p.lng.toFixed(2)},${p.lat.toFixed(2)}`;
    if (!buckets.has(key)) {
      buckets.set(key, { lng: p.lng, lat: p.lat, region: p.region, names: [] });
    }
    buckets.get(key).names.push(p.name);
  });
  return [...buckets.values()];
}

async function loadPartnersMap() {
  const root = document.getElementById('partners-map');
  const legend = document.getElementById('partners-map-legend');
  if (!root) return;

  try {
    const res = await fetch(typeof assetUrl === 'function' ? assetUrl('assets/data/partners.json') : 'assets/data/partners.json');
    const data = await res.json();
    const partners = data.partners || [];
    const points = aggregatePoints(partners);
    const width = 960;
    const height = 720;

    const dots = points
      .map((pt) => {
        const [x, y] = project(pt.lng, pt.lat, width, height);
        const title = `${pt.region} · ${pt.names.length} 家\n${pt.names.slice(0, 6).join('\n')}${pt.names.length > 6 ? '\n…' : ''}`;
        return `<circle class="partners-map__dot" cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${Math.min(10, 4 + pt.names.length)}" data-region="${pt.region}">
          <title>${title.replace(/</g, '&lt;')}</title>
        </circle>`;
      })
      .join('');

    root.innerHTML = `
      <svg class="partners-map__svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="全国合作单位分布示意">
        <defs>
          <linearGradient id="mapBg" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stop-color="rgba(56,189,248,0.08)"/>
            <stop offset="100%" stop-color="rgba(15,23,42,0.4)"/>
          </linearGradient>
        </defs>
        <rect width="100%" height="100%" fill="url(#mapBg)" rx="12"/>
        <path class="partners-map__outline" d="M120,420 L180,380 L260,360 L340,320 L420,300 L500,280 L580,260 L660,250 L740,260 L820,280 L880,320 L900,380 L880,440 L820,500 L740,540 L660,560 L580,570 L500,580 L420,570 L340,550 L260,520 L180,480 Z"/>
        ${dots}
      </svg>`;

    if (legend) {
      const regions = [...new Set(partners.map((p) => p.region))].sort();
      legend.textContent = `已标注 ${partners.length} 家合作单位，覆盖 ${regions.length} 个省份/直辖市。悬停圆点可查看当地机构。`;
    }
  } catch (err) {
    console.error('Failed to load partners map', err);
    root.innerHTML = '<p class="accordion__lead">合作地图加载失败。</p>';
  }
}

document.addEventListener('DOMContentLoaded', loadPartnersMap);
