"""
Генератор mods.json для Red_Zone — и моды с Modrinth, и ваши собственные.

Что лежит рядом с этим скриптом:
  modrinth.txt  — названия модов с Modrinth, по одному в строке (строки с # игнорируются)
  own_mods/     — ваши собственные .jar

Что сделать:
  1) впишите BASE_URL (ниже) — адрес папки own_mods в вашем GitHub-репозитории
  2) запустите:  python make_mods_json.py
  3) загрузите в репозиторий получившийся mods.json и папку own_mods

Моды с Modrinth скрипт «фиксирует»: записывает точные файлы, версии и контрольные суммы,
поэтому у всех игроков будут одинаковые моды (даже если на Modrinth выйдет новая версия).
Чтобы обновить мод — запустите скрипт заново.
"""
import hashlib
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

MC_VERSION = "1.20.1"
LOADER = "forge"
BASE_URL = "https://raw.githubusercontent.com/Karilkai/redzone-mods/main/own_mods/"

HERE = Path(__file__).resolve().parent
OWN_DIR = HERE / "own_mods"
OUT = HERE / "mods.json"


def http_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "RedZone-ModsGenerator/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def sha1(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def resolve(slug, seen, out, errors):
    if slug in seen:
        return
    seen.add(slug)
    q = urllib.parse.quote
    url = (f"https://api.modrinth.com/v2/project/{q(slug)}/version"
           f"?loaders={q(json.dumps([LOADER]))}&game_versions={q(json.dumps([MC_VERSION]))}")
    try:
        versions = http_json(url)
    except Exception as e:
        errors.append(f"{slug}: не удалось связаться с Modrinth ({e})")
        return
    if not versions:
        errors.append(f"{slug}: нет версии под {LOADER} {MC_VERSION} (проверьте название)")
        return
    v = versions[0]
    f = next((x for x in v["files"] if x.get("primary")), v["files"][0])
    out[f["filename"]] = {"name": f["filename"], "url": f["url"], "sha1": f.get("hashes", {}).get("sha1", "")}
    print(f"  Modrinth: {f['filename']}")
    for d in v.get("dependencies", []):
        if d.get("dependency_type") == "required" and d.get("project_id"):
            resolve(d["project_id"], seen, out, errors)


def main():
    entries, errors, seen = {}, [], set()

    txt = HERE / "modrinth.txt"
    slugs = []
    if txt.exists():
        slugs = [l.strip() for l in txt.read_text(encoding="utf-8").splitlines()
                 if l.strip() and not l.strip().startswith("#")]
    for slug in slugs:
        resolve(slug, seen, entries, errors)

    OWN_DIR.mkdir(exist_ok=True)
    own = sorted(OWN_DIR.glob("*.jar"))
    if own and "ВАШ_НИК" in BASE_URL:
        errors.append("Впишите BASE_URL в начале скрипта (адрес папки own_mods в вашем репозитории)")
    for p in own:
        entries[p.name] = {"name": p.name, "url": BASE_URL + urllib.parse.quote(p.name), "sha1": sha1(p)}
        print(f"  Свой мод: {p.name}")

    if errors:
        print("\nОШИБКИ — mods.json НЕ изменён:")
        for e in errors:
            print("  -", e)
        sys.exit(1)

    remove = []
    if OUT.exists():
        try:
            remove = json.loads(OUT.read_text(encoding="utf-8")).get("remove", [])
        except Exception:
            pass
    OUT.write_text(json.dumps({"modrinth": [], "direct": list(entries.values()), "remove": remove},
                              indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nГотово: {len(entries)} мод(ов) записано в {OUT.name}")


if __name__ == "__main__":
    main()
