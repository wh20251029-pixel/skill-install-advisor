# Evaluation Rubric

Use this rubric after extracting candidates and running local/static checks.

## Categories

Classify each article mention as one of:

- `installable-skill`: a Codex skill folder/name, skill marketplace entry, or repository that contains a `SKILL.md`.
- `ide-extension`: a VS Code/JetBrains/Cursor/etc. extension, not a Codex skill.
- `package-or-tool`: a CLI, library, app, or SaaS integration.
- `human-skill`: a capability such as product thinking, data analysis, writing, prompting, or communication.
- `unknown`: not enough information to identify.

Only `installable-skill` candidates should be shortlisted as skills to install. For other categories, explain the mismatch and optionally suggest the right installation path if the user asks.

## Source And Provenance

Classify source confidence separately from usefulness:

- `trusted-installed`: already installed from a known local/system skill root.
- `trusted-curated`: listed by an official/curated skill installer, marketplace, or bundled plugin source.
- `known-repo`: a repository or package source is provided and can be inspected.
- `article-only`: article mentions a name but gives no install source; run source discovery before deciding.
- `unknown`: the name cannot be tied to a real artifact.

Do not recommend direct installation for `article-only` or `unknown` sources until source discovery has been attempted. Recommend installation only after a real source is found and scanned.

## Source Discovery

For article-only names, attempt source discovery before marking a candidate unscannable:

- Search GitHub for exact matches containing `SKILL.md`.
- Search a trusted skills index/installer when available.
- Search package registries only when the candidate is clearly a package or IDE extension.
- Prefer exact repository/folder matches over fuzzy or SEO pages.
- Reject sources whose `SKILL.md` name/description does not match the article claim.
- When a GitHub source is found, fetch/clone it into a temp directory and run static scanning before ranking.

Evidence tiers:

- `exact-source`: exact skill folder/repo with matching `SKILL.md`.
- `probable-source`: likely repo/package, but name or description needs human review.
- `weak-source`: blog/list mention, no installable artifact.
- `no-source-found`: searched but no reliable source found.

## Scenario Handling

Use these responses for common cases:

- Real skill, not installed, trusted source, good fit: shortlist.
- Real skill, already installed: mark installed; do not shortlist unless update/repair is requested.
- Real skill, no source in article: search GitHub/index first; if still no source, mark "暂缓：来源解析失败".
- IDE extension: say it is not a Codex skill; evaluate separately if the user wants IDE extensions.
- CLI/package/SaaS: do not install as a skill; explain the proper category.
- Human ability: mark as concept, not installable.
- Duplicate/overlap: keep the one with clearer workflow value, safer source, or better local compatibility.
- Viral article with many weak items: recommend fewer than 3-4 if only 1-2 are defensible.

## Scoring

Score each candidate from 0-2 in five dimensions:

- Relevance: direct fit to the user's stated workflow.
- Concreteness: has a real name, source, and install path.
- Inspectability: local folder or trusted source can be reviewed before install.
- Safety: no high-risk static findings and no excessive permissions.
- Non-redundancy: not already installed or covered by existing skills.

Interpretation:

- `8-10`: recommend if the user wants this capability.
- `5-7`: optional; recommend only with a clear use case.
- `0-4`: do not recommend now.

## Scan Status And Risk Levels

Always separate scan status from risk.

Scan status labels:

- `local_source_scanned`: local installed/source folder was scanned.
- `provided_source_scanned`: user-provided local source path was scanned.
- `remote_source_fetched_and_scanned`: supported GitHub source was fetched into a platform temp directory and scanned.
- `trusted_source_checked`: trusted marketplace/installer metadata was checked, but source code may still need scanning.
- `source_url_not_fetched`: a URL exists but was not fetched or cloned in the current environment.
- `no_source`: no source was available to scan.
- `invalid_name`: candidate cannot be a Codex skill name.

Only assign a low/medium/high risk level after some source or metadata was inspected. For `no_source` and `source_url_not_fetched`, use `not_scanned` and treat as "暂缓".

## Risk Levels

Use these labels:

- `low`: no suspicious patterns found in inspected files.
- `medium`: scripts or instructions perform network, shell, filesystem, or credential-related operations that may be legitimate but need review.
- `high`: destructive commands, broad secret access, obfuscated code, unexplained remote execution, or writes outside expected skill/project directories.
- `not_scanned`: source cannot be inspected in the current environment.

Static review is not a virus scan. Phrase results as "未发现明显高风险模式" rather than "安全" or "无毒".

## Safety Signals To Check

When source files are inspectable, look for:

- `SKILL.md` frontmatter quality and whether the description matches the claimed purpose.
- Install scripts, shell commands, package hooks, or postinstall behavior.
- Network calls, remote downloads, or code piped into a shell.
- Reads of secrets, tokens, SSH keys, browser cookies, or environment variables.
- Writes outside the skill folder, project folder, or expected user config path.
- Destructive commands such as recursive delete, hard reset, chmod 777, or sudo.
- Obfuscated code, minified scripts without reason, or encoded payloads.
- Broad permissions or instructions that ask the user to disable security controls.

These checks reduce obvious risk but cannot prove a candidate is malware-free.

## Recommendation Constraints

- Recommend at most 3-4 installs.
- Prefer fewer recommendations over weak recommendations.
- Put already installed candidates in a separate "已安装/无需安装" group.
- Put article-only concepts in "不是可安装 skill" rather than forcing them into the shortlist.
- If a candidate is attractive but uninspectable, recommend "先获取来源/仓库再判断", not installation.
