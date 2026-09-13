import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { pool } from "./db.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const dir = path.join(__dirname, "..", "migrations");

const files = (await fs.readdir(dir)).filter((f) => f.endsWith(".sql")).sort();
for (const f of files) {
  console.log(`Aplicando ${f}...`);
  const sql = await fs.readFile(path.join(dir, f), "utf8");
  await pool.query(sql);
}
await pool.end();
console.log("Migrations aplicadas.");
