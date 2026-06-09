 # Skill Install Advisor

  Analyze social-media or blog posts that recommend many AI/Codex skills, then help decide which ones are actually worth
  installing.

  This skill extracts mentioned candidates, checks local install state, resolves sources, runs static risk screening
  when source is available, and returns a shortlist of 3-4 install candidates.

  ## Usage

  Use the skill with an article, screenshot, or link:

  ```text
  Use $skill-install-advisor to evaluate the skills mentioned in this article and recommend which ones to install.

  ## Files

  - SKILL.md: main skill instructions
  - scripts/audit_skill_candidates.py: local/static risk screening helper
  - references/evaluation_rubric.md: scoring and risk rubric
  - agents/openai.yaml: UI metadata
