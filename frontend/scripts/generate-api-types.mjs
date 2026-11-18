import { execFileSync } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { resolve } from "node:path";
import openapiTS, { astToString } from "openapi-typescript";
const root = fileURLToPath(new URL("../../", import.meta.url));
const python =
  process.env.KG_PYTHON ??
  resolve(
    root,
    process.platform === "win32"
      ? ".venv/Scripts/python.exe"
      : ".venv/bin/python",
  );
const source = process.env.KG_OPENAPI_URL
  ? await (await fetch(process.env.KG_OPENAPI_URL)).json()
  : JSON.parse(
      execFileSync(
        python,
        [
          "-B",
          "-c",
          "import json; from backend.app.main import app; print(json.dumps(app.openapi()))",
        ],
        { cwd: root, encoding: "utf8" },
      ),
    );
const directory = new URL("../src/types/generated/", import.meta.url);
mkdirSync(directory, { recursive: true });
writeFileSync(
  new URL("openapi.ts", directory),
  astToString(await openapiTS(source)),
);
mkdirSync(new URL("../docs/", import.meta.url), { recursive: true });
writeFileSync(
  new URL("../docs/openapi.json", import.meta.url),
  JSON.stringify(source, null, 2) + "\n",
);
console.log(
  "Generated frontend contracts from",
  Object.keys(source.paths).length,
  "API paths.",
);
