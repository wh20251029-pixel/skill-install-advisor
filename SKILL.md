---
name: skill-install-advisor
description: Analyze pasted articles, uploaded article screenshots, Xiaohongshu notes, WeChat posts, blog lists, URLs, or recommendation roundups that mention many "skills"; extract the mentioned skill candidates, check whether they are already installed or locally inspectable, run static risk and suitability screening, then produce a ranked shortlist of 3-4 skills with reasons and ask the user which one to install. Use implicitly or explicitly when a user provides a social-media/blog article about "必备 skills", asks which recommended skills are worth installing, wants recommendations from an article screenshot, or wants help choosing and then installing one selected skill.
---

# Skill Install Advisor

## Goal

Turn broad "必备 skills" articles into an installation decision aid. The first pass recommends; installation happens only after the user chooses a shortlisted item.

Use this skill to:

- Read article content from reachable URLs, pasted notes, uploaded screenshots, local files, or browser-accessible pages.
- Extract all mentioned skill names and normalize duplicates.
- Check local install state and inspectable source folders.
- Run static risk screening on inspectable skill folders.
- Judge fit for the user's actual workflow and return at most 3-4 install candidates.
- After the user chooses one shortlisted candidate, help install it using the appropriate installer workflow.

## Core Requirements

Treat this skill as an installation advisor, not as a content summarizer and not as antivirus software.

It must handle varied real-world cases:

- Article mentions real Codex skills: verify install state, inspect source when available, rank by fit.
- Article mixes Codex skills, IDE extensions, CLI tools, SaaS products, and human abilities: classify them separately and do not force everything into the "skill to install" bucket.
- Article is social-media hype with vague claims: downgrade candidates without concrete names, sources, or repeated user value.
- Candidate is already installed: mark "已安装/无需安装" unless update or repair is requested.
- Candidate source is not in the article: actively search GitHub, curated skill indexes, package registries, and marketplace pages before declaring the source missing.
- Candidate source remains missing or uninspectable after source discovery: do not recommend direct installation; ask for source, repository, marketplace page, or package identity.
- Candidate is useful but risky: explain the risk and recommend a safer alternative, manual review, or sandboxed trial.
- User has a stated role or workflow: prioritize direct fit over the article's ranking.
- User has no stated goal: infer likely goal from the article category, then keep recommendations conservative.
- Multiple candidates overlap: recommend the narrower or more mature one, not all of them.

The value of this skill is to reduce bad installs before they happen:

- Separate installable tools from article buzzwords.
- Avoid redundant installs.
- Surface untrusted or unverifiable sources.
- Catch obvious risky instructions and permission requests.
- Match recommendations to the user's actual workflow.
- Limit choices to a small shortlist the user can act on.
- Require user selection before installation.

## Mandatory Risk Scanning

For every concrete installable candidate, call available tools to perform a risk scan before recommending installation.

Use this order:

1. Scan local installed/source folders with `scripts/audit_skill_candidates.py`.
2. If the article provides a repository, marketplace page, package path, or local folder, inspect that source and run the audit script against it.
3. If the article only gives a name, actively resolve a source before giving up:
   - Search GitHub for the exact name plus `SKILL.md`.
   - Search curated skill installers or indexes when available, such as `npx skills find <name>`.
   - Search package registries or marketplace pages only when the candidate is clearly a package or extension.
   - Prefer exact-name repositories/folders that contain `SKILL.md`; do not treat random blog mentions as source.
4. For supported GitHub blob/tree URLs, fetch and scan the source with `--fetch-remote`.
5. If local security tools are available, run the relevant one for the source type: secret scanners, dependency audit tools, malware scanners, or package audit commands.
6. If no source can be found or fetched after discovery attempts, mark the candidate as `未扫描：来源解析失败`; do not label it as safe or unsafe, and do not recommend direct installation.

The report must include a short "扫描情况" line or column that says what was scanned:

- `已扫描本地源码`: local installed/source folder was scanned.
- `已扫描提供的来源`: user-provided source folder/repo checkout was scanned.
- `已拉取并扫描 GitHub 源码`: supported GitHub source was fetched into a temp directory and scanned.
- `未扫描：缺少来源`: no source artifact was available.
- `未扫描：来源解析失败`: GitHub/index/search attempts did not find a reliable source.
- `未扫描：需要联网/授权`: source exists but cannot be fetched in the current environment.

Never leave a candidate with an unexplained `unknown` risk label. If scanning was not possible, explain the blocker and treat installation as "暂缓".

## Invocation Model

Trigger this skill automatically when the user uploads or pastes a "skills recommendation" article, even if they do not name `$skill-install-advisor`.

Supported inputs:

- Pasted article text or markdown.
- Uploaded screenshots of article pages or note cards.
- Xiaohongshu, WeChat, blog, GitHub, marketplace, or article URLs.
- A manually typed list of recommended skills.

When screenshots are provided, read visible text directly from the image. If important names are cut off, obscured, or too low-resolution, ask for a clearer screenshot or pasted text before making installation recommendations.

When only a URL is provided, try to inspect it before asking the user for manual text. If the page is login-gated, anti-scraped, image-only, or blocked in the current environment, report the blocker and offer the lowest-friction fallback.

## Link Reading Policy

Treat Xiaohongshu and WeChat links as first-class inputs, but do not assume they are readable.

Use this order:

1. Try direct URL reading with the available browsing/fetching tool.
2. If direct reading fails and a user-authenticated browser tool is available, offer to use it for pages that require the user's logged-in session.
3. If the page renders but text is image-based, try browser text extraction, reader mode, page accessibility text, or OCR if image access is available.
4. If the platform blocks access, ask for an alternative artifact rather than pasted body text first: saved HTML/MHTML, exported PDF, copied share card text, browser "print to PDF", or the original source/installation links mentioned in the article.
5. If none of those are available, ask the user to type only the visible skill names and source links, not the entire article.

In the report, include "内容获取情况":

- `链接已读取`: direct link content was read.
- `登录页/反爬阻断`: link exists but the platform blocked access.
- `页面可见但文字不可提取`: article appears image-based or inaccessible to text extraction.
- `用户提供替代内容`: analysis is based on pasted names, saved file, PDF, or manually typed candidates.

When content extraction is incomplete, make conservative recommendations and clearly say which candidates may be OCR/link-extraction uncertain.

## Workflow

1. Collect the source content.
   - Try direct URL reading first when the user gives a link.
   - If only a URL is provided and it cannot be accessed, follow the Link Reading Policy fallbacks.
   - If the user's goal or IDE is unclear, infer from the article category first; ask only when it materially changes the recommendation.

2. Extract candidate skills.
   - List every named skill/package/extension mentioned.
   - Normalize names to lowercase hyphen-case when they look like Codex skill names.
   - Preserve display names when the article uses non-Codex names, product names, or IDE extension names.
   - Merge duplicates and obvious aliases.
   - Mark vague items such as "数据分析能力", "产品思维", or "AI 提效" as concepts, not installable skills, unless the article gives a concrete package/repo/extension name.

3. Inspect local state.
   - Run `scripts/audit_skill_candidates.py` with the candidate names.
   - Search likely local roots if needed: current workspace, `$CODEX_HOME/skills`, `~/.codex/skills`, and any user-provided path.
   - Treat "already installed" as a reason to avoid reinstalling unless the user asks for update/repair.

4. Resolve missing sources.
   - For every promising candidate not found locally, search GitHub or a trusted skill index before marking source missing.
   - Use exact names and aliases from the article. Example queries: `site:github.com <skill-name> SKILL.md`, `"<skill-name>" "SKILL.md"`, and `npx skills find <skill-name>`.
   - If a GitHub source is found, fetch/clone to a temporary directory and run static scanning before recommending installation.
   - If several sources match, prefer the source with an exact folder/name match, recent maintenance, clear install instructions, and lower permission surface.

5. Evaluate install suitability.
   - Read `references/evaluation_rubric.md` when ranking candidates or explaining borderline cases.
   - Favor skills that are concrete, inspectable, directly useful to the user's stated workflow, narrowly scoped, and non-overlapping with installed capabilities.
   - Penalize candidates that are vague, redundant, uninspectable, stale, require broad system permissions, or ask for secrets without a clear need.
   - Be explicit that static screening is not a malware or virus guarantee.

6. Produce the decision report.
   - Start with the conclusion: "建议安装", "可选", "不建议", and "已安装/无需安装".
   - Include content acquisition status before the candidate table.
   - Include a compact table with: candidate, source mention, source discovery status, installed state, scan status, risk level, fit, decision, reason.
   - Shortlist no more than 3-4 skills as install candidates. If fewer are suitable, recommend fewer.
   - End by asking the user to choose one shortlisted skill to install, or say what extra source is needed to verify an uninspectable candidate.

7. Install after user selection.
   - Treat the user's selection from the shortlist as explicit installation intent.
   - Reconfirm only when installation requires network access, writing outside allowed directories, elevated privileges, secrets, or an untrusted/uninspectable source.
   - For Codex skills from a curated list or GitHub repo path, use the `skill-installer` workflow when available.
   - For a local skill folder, copy or install according to the user's Codex skill location conventions, usually `${CODEX_HOME:-$HOME/.codex}/skills`.
   - For IDE extensions or non-Codex packages, explain that they are not Codex skills and use the appropriate IDE/package installation path only if the user explicitly wants that category installed.
   - After installation, verify the installed folder/package exists and report the result.

## Running The Audit Script

For pasted article text:

```bash
python3 skill-install-advisor/scripts/audit_skill_candidates.py --article /path/to/article.txt
```

For candidates already extracted by the agent:

```bash
python3 skill-install-advisor/scripts/audit_skill_candidates.py --skills "pdf,spreadsheets,skill-installer"
```

For additional scan roots:

```bash
python3 skill-install-advisor/scripts/audit_skill_candidates.py --skills "my-skill" --scan-root /path/to/skills
```

For a provided source folder:

```bash
python3 skill-install-advisor/scripts/audit_skill_candidates.py --skills "my-skill" --source my-skill=/path/to/my-skill
```

For a supported GitHub `tree` or `blob` URL:

```bash
python3 skill-install-advisor/scripts/audit_skill_candidates.py --skills "my-skill" --source my-skill=https://github.com/owner/repo/tree/main/path/to/my-skill --fetch-remote
```

Use `--json` when the result will be post-processed. The script is a local static helper; combine its output with judgment about relevance, redundancy, and user goals.

## Decision Rules

Recommend installation only when all are true:

- The candidate is a concrete installable skill, extension, package, or repo.
- Its source can be inspected or comes from a trusted curated source.
- It is not already installed or already covered by an equivalent installed skill.
- Static screening finds no high-risk pattern, or the risk is understood and justified.
- It maps to a repeated user workflow, not a one-off curiosity.

Do not recommend installation when:

- The article uses "skill" to mean a human ability rather than a package.
- The candidate cannot be found, inspected, or tied to a real install source.
- The recommended behavior requires excessive permissions, destructive commands, or secret exfiltration risk.
- It duplicates built-in Codex capability or an installed skill without adding a clear advantage.
- The user would need to install many items just to maybe use one.

## Safety Boundary

Never claim a candidate is "无毒", "安全", or "已通过病毒扫描" unless an actual antivirus or trusted security scanner was run and its output is shown. In normal Codex use, describe the result as static risk screening:

- "未发现明显高风险模式" for low-risk inspected candidates.
- "存在需要复核的风险点" for medium-risk candidates.
- "不建议安装" for high-risk candidates.
- "未扫描：来源解析失败，暂不建议安装" for candidates whose source cannot be found after GitHub/index/source discovery attempts.

If a user specifically asks for virus scanning, explain that this skill can perform source/provenance/static-pattern review and can run available local scanners only if they are installed and permitted. Do not invent scanner results.

## Output Shape

Use concise Chinese by default for Chinese articles.

Recommended structure:

```text
结论：这篇文章提到 N 个候选项，其中 X 个是具体可安装项。已对可获取来源的候选做风险扫描；建议最多先装 A、B、C。

内容获取情况：链接已读取 / 登录页或反爬阻断 / 页面可见但文字不可提取 / 用户提供替代内容。
来源解析：GitHub/索引命中 X 个；未找到可靠来源 Y 个；需要联网/授权 Z 个。
扫描情况：已扫描本地源码 X 个；已拉取并扫描 GitHub 源码 Y 个；未扫描来源解析失败 Z 个。

| 候选 | 来源解析 | 状态 | 扫描情况 | 风险 | 适配度 | 结论 | 原因 |
| --- | --- | --- | --- | --- | --- | --- | --- |

建议安装：
1. ...
2. ...

暂缓/需要来源：
- ...

不建议安装/暂缓：
- ...

下一步：请从 A/B/C 中选一个；你选定后我会进入安装流程并验证结果。
```

Keep the final answer decision-oriented. Do not let social-media ranking language override the actual local risk and fit assessment.
