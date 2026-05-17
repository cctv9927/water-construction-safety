import { existsSync } from "fs";
import { globbySync } from "globby";
import { basename, dirname, join } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));

const inputDirectory = join(__dirname, "../../../Apps/Sandcastle/gallery");

const htmlFiles = globbySync([`${inputDirectory}/*.html`]);

for (const file of htmlFiles) {
  const name = basename(file);
  if (existsSync(join(inputDirectory, "development", name))) {
    console.log("duplicate", name);
  }
}
