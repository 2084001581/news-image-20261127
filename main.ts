// main.ts -- validate entry.png and copy it to the output directory.
//
// Node 22, standard library only. The entry is a single 1024x1024 PNG;
// this script checks the PNG magic bytes, the 1 MiB size cap and the
// dimensions read from the IHDR chunk, then copies the file unchanged.
// The copy is byte-for-byte, so repeated runs are identical.
//
// Usage:
//   MAKEFUN_OUTPUT_DIR=out node main.ts        # writes out/entry.png
//   node main.ts                               # writes /output/entry.png

import { copyFileSync, existsSync, mkdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

const PNG_MAGIC = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
const MAX_BYTES = 1024 * 1024;
const MAX_SIDE = 1024;

function fail(message: string): never {
  console.error(`error: ${message}`);
  process.exit(1);
}

// The entry lives next to this script; resolve it relative to the file
// instead of the working directory so the script works from anywhere.
const scriptDir = new URL(".", import.meta.url).pathname;
const sourcePath = join(scriptDir, "entry.png");

if (!existsSync(sourcePath)) {
  fail(`entry.png not found at ${sourcePath}`);
}

const bytes = readFileSync(sourcePath);

if (bytes.length > MAX_BYTES) {
  fail(`entry.png is ${bytes.length} bytes, over the ${MAX_BYTES} byte limit`);
}

if (bytes.length < 33 || !bytes.subarray(0, 8).equals(PNG_MAGIC)) {
  fail("entry.png is not a PNG file (bad magic bytes)");
}

// Parse the IHDR chunk: width and height are big-endian uint32s at
// offsets 16 and 20, right after the 8-byte signature and the 8-byte
// IHDR chunk header.
const width = bytes.readUInt32BE(16);
const height = bytes.readUInt32BE(20);
if (width > MAX_SIDE || height > MAX_SIDE) {
  fail(`entry.png is ${width}x${height}, larger than ${MAX_SIDE}x${MAX_SIDE}`);
}

const outDir = process.env.MAKEFUN_OUTPUT_DIR ?? "/output";
mkdirSync(outDir, { recursive: true });
const targetPath = join(outDir, "entry.png");
copyFileSync(sourcePath, targetPath);

const written = statSync(targetPath);
console.log(
  `ok: ${width}x${height} PNG, ${written.size} bytes -> ${targetPath}`,
);
