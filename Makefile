.PHONY: all build fetch model test serve
all:            ## fetch live data and rebuild everything
	python3 -m pipeline all
build:          ## rebuild from committed snapshots (offline)
	python3 -m pipeline build
fetch:
	python3 -m pipeline fetch
model:          ## re-run bear/base/bull after editing model/assumptions.yaml
	python3 -m pipeline model
test:
	python3 -m unittest discover -s tests -v
serve:          ## open http://localhost:8000
	cd docs && python3 -m http.server 8000
