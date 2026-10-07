#!/usr/bin/env python3
from pathlib import Path
import re
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "dokumentasi"
DIAGRAM = OUT / "diagram"
EXCLUDE = {".git", "node_modules", "vendor", "storage", "bootstrap/cache", "public/build"}
FENCE = chr(96) * 3

def read(p):
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""

def rel(p):
    return p.relative_to(ROOT).as_posix()

def source_files(exts):
    result = []
    for p in ROOT.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in exts:
            continue
        r = rel(p)
        if any(r == x or r.startswith(x.rstrip("/") + "/") for x in EXCLUDE):
            continue
        result.append(p)
    return result

php = source_files({".php"})
blade = [p for p in ROOT.rglob("*.blade.php") if "vendor" not in p.parts and "node_modules" not in p.parts]
route_files = [p for p in php if "rute" in p.parts]
controllers = [p for p in php if "pengendali" in p.parts]
models = [p for p in php if "model" in p.parts]
migrations = [p for p in php if "migrasi" in p.parts]
middleware = [p for p in php if "penengah" in p.parts]
services = [p for p in php if "layanan" in p.parts]

route_re = re.compile(r"Route::(get|post|put|patch|delete|resource|match|any)\s*\(\s*[\"\']([^\"\']+)")
routes = []
for p in route_files:
    for method, path in route_re.findall(read(p)):
        routes.append((method.upper(), path, rel(p)))

tables = []
for p in migrations:
    tables += re.findall(r"(?:Schema::create|Schema::table)\s*\(\s*[\"\']([^\"\']+)", read(p))

roles = Counter()
for p in php:
    for role in re.findall(r"[\"\'](admin|staf|guru|kepala-sekolah|kepala_sekolah|superadmin)[\"\']", read(p), re.I):
        roles[role.lower()] += 1

OUT.mkdir(exist_ok=True)
DIAGRAM.mkdir(exist_ok=True)

(OUT / "README.md").write_text(f"""# Dokumentasi Otomatis

Dibuat dari source code repository pada commit saat workflow berjalan.

| Komponen | Jumlah |
|---|---:|
| File PHP | {len(php)} |
| Blade | {len(blade)} |
| Route file | {len(route_files)} |
| Controller | {len(controllers)} |
| Model | {len(models)} |
| Migration | {len(migrations)} |
| Middleware/Penengah | {len(middleware)} |
| Service/Layanan | {len(services)} |
| Route terdeteksi | {len(routes)} |
| Tabel terdeteksi | {len(set(tables))} |

## Diagram
- diagram/arsitektur.md
- diagram/workflow.md
- diagram/use-case.md
- diagram/erd.md
- ROLE-DAN-AKSES.md

Analisis bersifat statis dan tidak menganggap fitur yang tidak ditemukan sebagai fitur sistem.
""", encoding="utf-8")

architecture = f"""# Arsitektur Sistem

{FENCE}mermaid
flowchart LR
    U[Pengguna] --> R[Route]
    R --> MW[Middleware / Penengah]
    MW --> C[Controller / Pengendali]
    C --> S[Service / Layanan]
    C --> M[Model]
    S --> M
    M --> DB[(Database)]
    C --> V[Blade / Tampilan]
{FENCE}
"""
(DIAGRAM / "arsitektur.md").write_text(architecture, encoding="utf-8")

workflow = f"""# Workflow Sistem

Jumlah route terdeteksi: **{len(routes)}**

{FENCE}mermaid
flowchart TD
    A[Pengguna] --> B[Route]
    B --> C{{Middleware}}
    C --> D[Controller]
    D --> E[Validasi dan proses]
    E --> F[Service / Model]
    F --> G[(Database)]
    D --> H[Blade / Response]
{FENCE}

## Route terdeteksi

| Metode | Path | File |
|---|---|---|
"""
for method, path, src in routes[:300]:
    workflow += f"| {method} | {path} | {src} |\n"
if len(routes) > 300:
    workflow += f"\nMenampilkan 300 dari {len(routes)} route.\n"
(DIAGRAM / "workflow.md").write_text(workflow, encoding="utf-8")

use_case = f"""# Use Case Terindikasi

{FENCE}mermaid
flowchart LR
    A[Pengguna] --> B[Login / Akses]
    A --> C[Modul melalui Route]
    C --> D[Controller]
    D --> E[Proses Data]
    E --> F[Model / Database]
{FENCE}

Aktor dan use case bisnis final harus divalidasi terhadap kebutuhan sebenarnya.
"""
(DIAGRAM / "use-case.md").write_text(use_case, encoding="utf-8")

unique_tables = sorted(set(tables))
erd = "# ERD / Tabel Terdeteksi\n\n" + FENCE + "mermaid\nerDiagram\n"
for table in unique_tables[:120]:
    safe = re.sub(r"[^A-Za-z0-9_]", "_", table)
    erd += f"    {safe} {{\n        string id\n    }}\n"
erd += FENCE + "\n\nRelasi foreign key tidak ditebak oleh versi awal generator ini.\n"
(DIAGRAM / "erd.md").write_text(erd, encoding="utf-8")

role_doc = "# Role yang Terindikasi\n\n"
if roles:
    for role, count in roles.most_common():
        role_doc += f"- {role}: {count} referensi terdeteksi\n"
else:
    role_doc += "Tidak ada role yang terdeteksi dengan pola sederhana.\n"
(OUT / "ROLE-DAN-AKSES.md").write_text(role_doc, encoding="utf-8")

print("Analisis selesai.")
