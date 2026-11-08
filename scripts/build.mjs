import { copyFile, mkdir, readdir, rm } from 'node:fs/promises';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const dist = join(root, 'dist');
await rm(dist, { recursive: true, force: true });
await mkdir(join(dist, 'assets'), { recursive: true });
for (const name of ['index.html', 'privacy.html', 'terms.html', 'favicon.svg', 'campaign.js', 'vsl.html']) {
  await copyFile(join(root, name), join(dist, name));
}
let assets = 0;
for (const name of await readdir(join(root, 'assets'))) {
  if (!/\.(webp|woff2)$/.test(name)) continue;
  await copyFile(join(root, 'assets', name), join(dist, 'assets', name));
  assets++;
}
const vslAssets = ['vsl-kit.css', 'style.css', 'vsl-player.js', 'fox-news.webp', 'abc-news.webp', 'cbs-news.webp'];
await mkdir(join(dist, 'assets', 'vsl'), { recursive: true });
for (const name of vslAssets) {
  await copyFile(join(root, 'assets', 'vsl', name), join(dist, 'assets', 'vsl', name));
}
console.log(`Built dist: 6 site files, ${assets} optimized assets, ${vslAssets.length} VSL assets. Source notes and tests are excluded.`);
