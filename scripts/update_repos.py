#!/usr/bin/env python3
"""Atualiza a tabela "Cada vídeo = 1 repositório grátis" do README.

Lê os repositórios públicos do usuário na API do GitHub (só GITHUB_TOKEN padrão da Action),
cruza com scripts/planned.json e reescreve o bloco entre <!-- REPOS:START --> e <!-- REPOS:END -->.
Roda sem dependências fora da stdlib.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
PLANNED = ROOT / "scripts" / "planned.json"
USER = os.environ.get("GH_USER", "brunodelatea")
START, END = "<!-- REPOS:START -->", "<!-- REPOS:END -->"


def api(url: str):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "profile-readme"})
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def public_repos() -> dict[str, dict]:
    repos, page = {}, 1
    while True:
        batch = api(f"https://api.github.com/users/{USER}/repos?type=owner&per_page=100&page={page}")
        if not batch:
            break
        for r in batch:
            if not r.get("private") and not r.get("fork") and not r.get("archived"):
                repos[r["name"]] = r
        if len(batch) < 100:
            break
        page += 1
    return repos


def esc(s: str) -> str:
    return (s or "").replace("|", "\\|").strip()


def build_table(planned: dict, pub: dict[str, dict]) -> str:
    rows = ["| Repositório | O que é | Comenta no vídeo | Status |", "|---|---|:---:|:---:|"]
    seen = set()
    for p in planned["repos"]:
        name = p["name"]
        seen.add(name)
        r = pub.get(name)
        if r:
            desc = esc(r.get("description") or p["pt"])
            stars = f" · ⭐ {r['stargazers_count']}" if r.get("stargazers_count") else ""
            rows.append(f"| [**{name}**]({r['html_url']}) | {desc} | `{p['word']}` | ✅ público{stars} |")
        else:
            rows.append(f"| **{name}** | {esc(p['pt'])} | `{p['word']}` | 🔒 em breve |")
    # repositórios públicos que não estavam na lista planejada
    for name, r in sorted(pub.items(), key=lambda kv: kv[1].get("pushed_at", ""), reverse=True):
        if name in seen or name in planned.get("exclude", []):
            continue
        rows.append(f"| [**{name}**]({r['html_url']}) | {esc(r.get('description') or '')} | | ✅ público |")
    n_pub = sum(1 for p in planned["repos"] if p["name"] in pub)
    head = f"**{n_pub} de {len(planned['repos'])} no ar** · atualizado automaticamente todo dia"
    return head + "\n\n" + "\n".join(rows)


def main() -> int:
    planned = json.loads(PLANNED.read_text(encoding="utf-8"))
    pub = public_repos()
    table = build_table(planned, pub)
    text = README.read_text(encoding="utf-8")
    if START not in text or END not in text:
        print("marcadores REPOS não encontrados no README", file=sys.stderr)
        return 1
    new = re.sub(rf"{re.escape(START)}.*?{re.escape(END)}", f"{START}\n{table}\n{END}", text, flags=re.S)
    if new != text:
        README.write_text(new, encoding="utf-8")
        print("README atualizado")
    else:
        print("sem mudanças")
    return 0


if __name__ == "__main__":
    sys.exit(main())
