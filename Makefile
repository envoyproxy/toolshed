SHELL:=/bin/bash

NPM_DIRS := $(shell find . -type f -name "package.json" -not -empty -exec dirname {} \; | sort -u | egrep  '^./' )

GITHUB_ACTIONS_DIRS := $(shell find . -type f -name "action.yml" -not -empty -exec grep -l "uses:" {} \; -exec dirname {} \; | grep -v "action.yml" | sort -u | egrep  '^./' )

PIP_DIRS := $(shell find . -type f -name "requirements.txt" -not -empty -exec dirname {} \; | sort -u | egrep  '^./' )

DEPENDABOT_PATH=".github/dependabot.yml"

# This target should run on /bin/bash since the syntax DIR=$${dir:1} is not supported by /bin/sh.
.PHONY: generate/dependabot
generate/dependabot:
	@echo "Recreating ${DEPENDABOT_PATH} file"
	@echo "version: 2" > ${DEPENDABOT_PATH}
	@echo "updates:" >> ${DEPENDABOT_PATH}
	$(MAKE) dependabot/update DIR="/" PACKAGE="github-actions"
	@set -e; for dir in $(GITHUB_ACTIONS_DIRS); do \
		$(MAKE) dependabot/update DIR=$${dir:1} PACKAGE="github-actions"; \
	done
	@set -e; for dir in $(NPM_DIRS); do \
		$(MAKE) dependabot/update DIR=$${dir:1} PACKAGE="npm"; \
	done
	@set -e; for dir in $(PIP_DIRS); do \
		$(MAKE) dependabot/update DIR=$${dir:1} PACKAGE="pip"; \
	done


.PHONY: dependabot/update
dependabot/update:
	@echo "Add update rule for \"${PACKAGE}\" in \"${DIR}\"";
	@echo "  - package-ecosystem: ${PACKAGE}" >> ${DEPENDABOT_PATH};
	@echo "    directory: ${DIR}" >> ${DEPENDABOT_PATH};
	@echo "    schedule:" >> ${DEPENDABOT_PATH};
	@echo "      interval: daily" >> ${DEPENDABOT_PATH};
	@if [ "${PACKAGE}" = "npm" ]; then echo "    groups:" >> ${DEPENDABOT_PATH}; $(MAKE) dependabot/update/group GROUP="eslint" PATTERNS="@typescript-eslint/* eslint* prettier"; fi

.PHONY: dependabot/update/group
dependabot/update/group:
	@echo "      ${GROUP}:" >> ${DEPENDABOT_PATH};
	@echo "        patterns:" >> ${DEPENDABOT_PATH};
	@set -e; for pattern in $(PATTERNS); do echo "          - \"$${pattern}\"" >> ${DEPENDABOT_PATH}; done
