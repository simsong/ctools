tags:
	etags *.py */*py

awsome_demo:
	/bin/rm -f tydoc_awsome_demo.html
	python3 tydoc_awsome_demo.py tydoc_awsome_demo.html
	cp tydoc_awsome_demo.html $$HOME/public_html/

check:
	python -m pytest

# These are used by the CI pipeline:
install-dependencies:
	if [ -r requirements.txt ]; then pip3 install --user -r requirements.txt ; fi

pytest:
	python -m pytest . -v --log-cli-level=INFO

coverage:
	python -m --debug -v --cov=. --cov-report=xml tests/ || echo pytest failed
