PYTHON = python3
MAIN = main.py

.PHONY: install run run-visual debug clean lint lint-strict

install:
	sudo apt update && sudo apt install -y python3-tk
	$(PYTHON) -m pip install flake8 mypy --break-system-packages

run:
ifndef MAP
	$(error Missing map argument. Usage: make run MAP=<map_file>)
endif
	$(PYTHON) $(MAIN) $(MAP)

run-visual:
ifndef MAP
	$(error Missing map argument. Usage: make run MAP=<map_file>)
endif
	$(PYTHON) $(MAIN) $(MAP) --visual

debug:
ifndef MAP
	$(error Missing map argument. Usage: make run MAP=<map_file>)
endif
	$(PYTHON) -m pdb $(MAIN) $(MAP)

clean:
	rm -rf __pycache__ .mypy_cache .pytest_cache

lint:
	flake8 .
	mypy --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs .

lint-strict:
	flake8 .
	mypy --strict .