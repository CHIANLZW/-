/** 从 videos-manifest.json 渲染经典项目视频 */
async function loadShowreel() {
  const roots = document.querySelectorAll('[data-showreel]');
  if (!roots.length) return;

  try {
    const res = await fetch('assets/data/videos-manifest.json');
    const data = await res.json();

    roots.forEach((root) => {
      const scope = root.dataset.showreel;
      let items = [];
      if (scope === 'home') {
        items = data.home || [];
      } else if (scope === 'fpv') {
        items = (data.portfolio && data.portfolio.fpv) || [];
      } else if (scope === 'film') {
        items = (data.portfolio && data.portfolio.film) || [];
      }

      if (!items.length) {
        root.innerHTML = `
          <div class="showreel-placeholder">
            <p>经典项目视频正在筛选更新。</p>
            <p class="showreel-placeholder__hint">请查看桌面 <strong>经典项目-视频清单.txt</strong>，勾选要上线的条目后告诉我编号或路径。</p>
          </div>`;
        return;
      }

      root.innerHTML = items
        .filter((v) => v.published !== false && v.file)
        .map(
          (v) => `
        <div class="video-card">
          <video controls preload="metadata" poster="${v.poster || ''}">
            <source src="${v.file}" type="video/mp4">
          </video>
          <p class="video-card__caption">${v.title}</p>
        </div>`
        )
        .join('');
    });
  } catch (err) {
    console.error('Failed to load videos manifest', err);
  }
}

document.addEventListener('DOMContentLoaded', loadShowreel);
