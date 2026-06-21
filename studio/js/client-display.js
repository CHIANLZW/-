/** 经典版在 /classic/ 子目录，静态资源需回退一级 */
window.assetUrl = function assetUrl(path) {
  const clean = String(path).replace(/^\//, '');
  const inClassic = /\/classic(?:\/|$)/i.test(location.pathname.replace(/\\/g, '/'));
  return (inClassic ? '../' : '') + clean;
};

/** 客户名称：别名归一 + 敏感信息打码 */
window.ClientDisplay = (() => {
  let config = { aliases: {}, sensitive: [], sensitiveMask: '***' };

  async function load() {
    try {
      const res = await fetch(assetUrl('assets/data/client-display.json'));
      config = await res.json();
    } catch {
      /* 使用默认空配置 */
    }
  }

  function normalize(raw) {
    if (!raw) return '';
    return String(raw)
      .replace(/^[\d._\-]+/, '')
      .replace(/\s*运营合格证$/, '')
      .replace(/\s*资料$/, '')
      .trim();
  }

  function resolveAlias(name) {
    const n = normalize(name);
    if (config.aliases[n]) return config.aliases[n];
    return n;
  }

  function isSensitive(name) {
    const resolved = resolveAlias(name);
    return (config.sensitive || []).some(
      (s) => resolved === s || resolved.includes('苍凌信息技术')
    );
  }

  function format(name) {
    const resolved = resolveAlias(name);
    if (!resolved) return '其他案例';
    if (isSensitive(resolved)) return config.sensitiveMask || '***';
    return resolved;
  }

  return { load, normalize, resolveAlias, isSensitive, format };
})();
