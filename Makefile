.PHONY: install-local

install-local:
	uv tool install --force --reinstall --editable .
