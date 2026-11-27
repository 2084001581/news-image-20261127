// news-image-20261127 entry (Node 22, standard library only).
// The front page is the entry.png beside this file: a newspaper-style
// infographic summing up the world news of Friday 27 November 2026.
// The program validates the image against the competition gate
// (PNG, at most 1 MiB, at most 1024 x 1024) and copies it to
// /output/entry.png (or $MAKEFUN_OUTPUT_DIR outside the grader).
//
//   mkdir -p out && MAKEFUN_OUTPUT_DIR=out node main.ts

import { copyFileSync, existsSync, mkdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';

const source = new URL('./entry.png', import.meta.url);
const outDir = process.env.MAKEFUN_OUTPUT_DIR ?? '/output';
const target = join(outDir, 'entry.png');

if (!existsSync(source)) {
  throw new Error('entry.png is missing next to main.ts');
}
const bytes = readFileSync(source);
if (bytes.length > 1048576) {
  throw new Error(`entry.png is ${bytes.length} bytes, over the 1 MiB limit`);
}
// PNG signature: 89 50 4E 47 0D 0A 1A 0A
const pngMagic = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
if (!bytes.subarray(0, 8).equals(pngMagic)) {
  throw new Error('entry.png is not a PNG file');
}
// IHDR width/height are big-endian uint32 at offsets 16 and 20.
const width = bytes.readUInt32BE(16);
const height = bytes.readUInt32BE(20);
if (width > 1024 || height > 1024) {
  throw new Error(`entry.png is ${width}x${height}, over the 1024x1024 limit`);
}

mkdirSync(outDir, { recursive: true });
copyFileSync(source, target);
const written = statSync(target).size;
console.log(`wrote ${target}: ${width}x${height} PNG, ${written} bytes`);
