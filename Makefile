PYTHON ?= python3

.PHONY: check check-loose check-skills new-skill new-case install-skill

check:
	$(PYTHON) tools/check_structure.py --strict

check-loose:
	$(PYTHON) tools/check_structure.py

check-skills:
	$(PYTHON) tools/check_skills.py --strict

new-skill:
	@test -n "$(NAME)" || (echo "Usage: make new-skill NAME=my-skill [RESOURCES=scripts,references]" && exit 2)
	$(PYTHON) tools/init_skill.py "$(NAME)" $(if $(RESOURCES),--resources "$(RESOURCES)",)

new-case:
	@test -n "$(CASE)" || (echo "Usage: make new-case CASE=dev-daily/my-case" && exit 2)
	$(PYTHON) tools/init_bench_case.py "$(CASE)" $(if $(SKILLS),--skills "$(SKILLS)",) $(if $(WORK_TYPE),--work-type "$(WORK_TYPE)",) $(if $(ARTIFACT_TYPES),--artifact-types "$(ARTIFACT_TYPES)",) $(if $(PROMPT_TIER),--prompt-tier "$(PROMPT_TIER)",) $(if $(PROMPT_CHARS),--developer-prompt-chars "$(PROMPT_CHARS)",) $(if $(PROMPT_WORDS),--developer-prompt-words "$(PROMPT_WORDS)",) $(if $(INPUT_MIN_TOKENS),--full-input-min-tokens "$(INPUT_MIN_TOKENS)",) $(if $(INPUT_MAX_TOKENS),--full-input-max-tokens "$(INPUT_MAX_TOKENS)",)

install-skill:
	@test -n "$(NAME)" || (echo "Usage: make install-skill NAME=my-skill" && exit 2)
	$(PYTHON) tools/install_skill.py "$(NAME)"
