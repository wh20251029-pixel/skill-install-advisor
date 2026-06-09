# Skill Install Advisor

Analyze social-media or blog posts that recommend many AI/Codex skills, then help decide which ones are actually worth installing.

This skill extracts mentioned candidates, checks local install state, resolves sources, runs static risk screening when source is available, and returns a shortlist of 3-4 install candidates.

## Usage

Use the skill with an article, screenshot, or link:

```text
Use $skill-install-advisor to evaluate the skills mentioned in this article and recommend which ones to install.
```

Example:

```text
Use $skill-install-advisor to analyze this Xiaohongshu post and recommend which skills are worth installing.
```

## What It Checks

- Whether mentioned items are real installable skills
- Whether each candidate is already installed locally
- Whether a source repository, `SKILL.md`, or trusted index entry exists
- Static risk patterns such as destructive commands, remote shell execution, secret exfiltration, and broad network access
- Scenario fit, redundancy, and whether the skill is worth installing now

## Safety Note

This skill performs static risk screening. It does not prove that a skill is malware-free and should not be described as antivirus scanning.

## Files

- `SKILL.md`: main skill instructions
- `scripts/audit_skill_candidates.py`: local/source risk screening helper
- `references/evaluation_rubric.md`: scoring and risk rubric
- `agents/openai.yaml`: UI metadata
