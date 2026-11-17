# Живая проверка адаптеров Qoder, Cursor, Codex

Kit version: 1.0.0 · Требование: AC-12, ADP-03, COMPATIBILITY-TESTS §3

Установщики этих адаптеров проверены на тестовых проектах, но не внутри самих приложений: на машине
автора нет их агентских CLI. Живую проверку выполняет агент самой среды. Откройте проект в приложении
и вставьте в его агентский чат один из промптов ниже.

Первичный путь установки — `uok init`: один раз выполните
`python3 UNIVERSAL-ORCHESTRATOR-KIT/uok bootstrap`, перезапустите сессию и напишите в чате
`uok init` (Codex: `$uok-init`). Промпты ниже — запасной путь и сами живые проверки;
пункт f) каждого промпта проверяет скилл-ярлык.

## Qoder

```text
Install and live-verify the Universal Orchestrator Kit in this project for Qoder.
1. Read UNIVERSAL-ORCHESTRATOR-KIT/START-HERE.md and adapters/qoder/README.md.
2. Check which model selectors this account really has and run
   python3 UNIVERSAL-ORCHESTRATOR-KIT/adapters/qoder/install.py --dry-run, then without --dry-run,
   passing --models with the real selectors.
3. Tell me to restart the session if the new agents are not visible yet.
4. Live checks, each with the actual output:
   a) use the uok-research-analyst subagent for a read-only task;
   b) have uok-implementation-engineer try to write .qoder/settings.json (must be denied by the G1 hook);
   c) try to read .env (must be denied);
   d) have uok-release-integration run `git push --force origin no-such-branch` (I must be asked; I will decline);
      NOTE: run this session in default permission mode, NOT Auto — in Auto the host classifier blocks
      the command before the G1 ask reaches me (observed 2026-11-17);
   e) check that .orchestrator/audit/g1.log has the matching lines with agent names;
   f) invoke /uok with a small read-only task (e.g. "summarize README.md") and confirm it runs
      the kit lifecycle (classification, routing, evidence-based report).
5. Write the results to UNIVERSAL-ORCHESTRATOR-KIT/handoff/INSTALLATION-REPORT-qoder-<date>.md from the template.
   Mark only what you actually ran as verified_live.
```

## Cursor

```text
Install and live-verify the Universal Orchestrator Kit in this project for Cursor.
1. Read UNIVERSAL-ORCHESTRATOR-KIT/START-HERE.md and adapters/cursor/README.md.
2. Run python3 UNIVERSAL-ORCHESTRATOR-KIT/adapters/cursor/install.py --dry-run, then without --dry-run.
3. If hooks or rules are not active yet, tell me to reload the window.
4. Live checks, each with the actual output:
   a) confirm the uok-orchestrator rule is applied and apply @uok-role-research-analyst for a read-only task;
   b) run the terminal command `git push --force origin no-such-branch` — G1 must DENY it with
      "requires human approval … the human must run it" (SEC-07). NOTE: Cursor documents hook `ask`,
      but live 3.27.22 executed the command without a prompt (2026-11-17), so G1 fails closed with
      deny; an interactive approval prompt is NOT expected on Cursor;
   c) try to read .env (must be denied by beforeReadFile). The file MUST exist first — beforeReadFile
      only fires for existing files; if .env is absent, ask me to create an inert fixture
      (e.g. `printf 'UOK_TEST_FIXTURE=1\n' > .env` in my own terminal) before probing;
   d) try to create a file outside the project, e.g. ../outside.txt (must be denied; preToolUse
      write-path fields were verified_live 2026-11-17 — this is a regression check);
   e) check .orchestrator/audit/g1.log for the matching lines;
   f) invoke /uok with a small read-only task in the same message and confirm it runs the kit lifecycle.
5. Write the results to UNIVERSAL-ORCHESTRATOR-KIT/handoff/INSTALLATION-REPORT-cursor-<date>.md from the template.
   Mark only what you actually ran as verified_live; if d) was not blocked, report it as a failure.
```

## Codex

```text
Install and live-verify the Universal Orchestrator Kit in this project for Codex.
1. Read UNIVERSAL-ORCHESTRATOR-KIT/START-HERE.md and adapters/codex/README.md.
2. Check which models this account has and run
   python3 UNIVERSAL-ORCHESTRATOR-KIT/adapters/codex/install.py --dry-run, then without --dry-run (with --models).
3. Tell me to trust the project .codex/ layer and to review and trust the hook with /hooks, then wait for me.
4. Live checks, each with the actual output:
   a) have uok_research_analyst do a read-only task;
   b) try to add a file ../outside.txt with apply_patch (must be denied by the G1 hook);
   c) try to create .env (must be denied);
   d) run `git push --force origin no-such-branch` (must be denied with "human must run it");
   e) check .orchestrator/audit/g1.log for the matching lines;
   f) invoke the $uok skill mention with a small read-only task in the same message and confirm
      it runs the kit lifecycle.
5. Write the results to UNIVERSAL-ORCHESTRATOR-KIT/handoff/INSTALLATION-REPORT-codex-<date>.md from the template.
   Mark only what you actually ran as verified_live.
```

## После проверки

Если все пункты прошли, зрелость адаптера в его README и в START-HERE поднимается до
`integration_tested`. Если что-то не прошло, это ошибка в адаптере: результат вместе с выводом стоит
передать для исправления.
