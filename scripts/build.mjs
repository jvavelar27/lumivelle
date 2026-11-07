import { copyFile, mkdir, readdir, rm } from 'node:fs/promises';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const dist = join(root, 'dist');
await rm(dist, { recursive: true, force: true });
await mkdir(join(dist, 'assets'), { recursive: true });
for (const name of ['index.html', 'privacy.html', 'terms.html', 'favicon.svg']) {
  await copyFile(join(root, name), join(dist, name));
}
let assets = 0;
for (const name of await readdir(join(root, 'assets'))) {
  if (!/\.(webp|woff2)$/.test(name)) continue;
  await copyFile(join(root, 'assets', name), join(dist, 'assets', name));
  assets++;
}
console.log(`Built dist: 4 site files, ${assets} optimized assets. Source notes and tests are excluded.`);
