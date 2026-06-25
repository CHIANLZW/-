/**
 * 批量脱敏 studio 文字：HTML + JSON（不修改 JS 源码）
 * 用法：node studio/scripts/privacy-desensitize.mjs
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { desensitizeString, maskCompaniesInText, maskPersonsInText } from './lib/privacy.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const studioRoot = path.join(__dirname, '..');

function desensitizeHtml(html) {
  let t = html;
  t = t.replace(
    /<a[^>]+href="tel:[^"]*"[^>]*>[\s\S]*?<\/a>/gi,
    '<span class="contact-muted">电话已隐藏，请通过邮箱联系</span>'
  );
  t = t.replace(/1[3-9]\d{9}/g, '');
  t = t.replace(/(联系(?:我们)?\s*·\s*)\d*/g, '$1');
  t = maskCompaniesInText(t);
  t = maskPersonsInText(t);
  return t;
}

function walkDir(dir, files = []) {
  for (const name of fs.readdirSync(dir)) {
    const p = path.join(dir, name);
    const st = fs.statSync(p);
    if (st.isDirectory()) {
      if (name === 'node_modules') continue;
      walkDir(p, files);
    } else if (name.endsWith('.json')) files.push(p);
  }
  return files;
}

function processJson(filePath) {
  const data = JSON.parse(fs.readFileSync(filePath, 'utf8'));
  const walk = (obj, key = '') => {
    if (Array.isArray(obj)) return obj.map((v, i) => walk(v, String(i)));
    if (obj && typeof obj === 'object') {
      const o = {};
      for (const [k, v] of Object.entries(obj)) {
        o[k] = typeof v === 'string' ? desensitizeString(v, k) : walk(v, k);
      }
      return o;
    }
    return obj;
  };
  const out = JSON.stringify(walk(data), null, 2) + '\n';
  fs.writeFileSync(filePath, out, 'utf8');
  console.log('OK', path.relative(studioRoot, filePath));
}

const jsonFiles = walkDir(path.join(studioRoot, 'assets', 'data'));
for (const f of jsonFiles) processJson(f);

for (const sub of ['', 'classic']) {
  const d = sub ? path.join(studioRoot, sub) : studioRoot;
  for (const f of fs.readdirSync(d)) {
    if (!f.endsWith('.html')) continue;
    const p = path.join(d, f);
    const raw = fs.readFileSync(p, 'utf8');
    const out = desensitizeHtml(raw);
    if (out !== raw) {
      fs.writeFileSync(p, out, 'utf8');
      console.log('OK', path.relative(studioRoot, p));
    }
  }
}

const proj = path.join(studioRoot, 'projects', 'mazda323.html');
if (fs.existsSync(proj)) {
  const raw = fs.readFileSync(proj, 'utf8');
  fs.writeFileSync(proj, desensitizeHtml(raw), 'utf8');
  console.log('OK projects/mazda323.html');
}

console.log('Done (HTML + JSON only).');
