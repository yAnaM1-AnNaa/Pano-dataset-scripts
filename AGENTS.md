# Repository Guidelines
Always ask before doing any changes in code.
## Project Structure & Module Organization
- Pipeline entry: `pipeline.py` runs json-shrink -> json-convert -> json-png -> mask-viz.
- Core processing scripts live in `util/` (`shrink_polygon.py`, `convert_polygon_to_points.py`, `generate_gaussian_mask.py`, `visualize_mask.py`).
- Convenience wrapper: `data.sh` calls the pipeline with positional args.
- Utilities and one-off helpers live in `others/` (e.g., `batch_rename.py`, `compare_directories.py`).
- No dedicated tests or package structure; scripts are executed directly.

## Build, Test, and Development Commands
- `python pipeline.py run --input <in> --output <out> --distance 50 --spacing 2` runs the full pipeline.
- `python pipeline.py json-shrink --input <in> --output <out> --distance 50 --config <config.json>` shrinks Labelme polygons.
- `python pipeline.py json-convert --input <in> --output <out> --spacing 2` densifies polygons into point sets.
- `python pipeline.py json-png --input <in> --output <out> --config <config.json>` produces Gaussian masks.
- `python pipeline.py mask-viz --image <img_dir> --mask <mask_dir> --output <out_dir>` renders overlays for QA.
- `bash data.sh <input_dir> <output_dir> <distance> <spacing>` wraps `pipeline.py run`.

## Coding Style & Naming Conventions
- Python scripts use 4-space indentation and standard library-style imports.
- Keep filenames and CLI flags in `snake_case` (e.g., `--input`, `--output`).
- Favor small, focused scripts with clear CLI arguments.
- Dependencies are imported directly (not vendored). At minimum, Python 3 with `numpy` and `Pillow` is required.

## Testing Guidelines
- There is no automated test suite in this repo.
- Validate changes by running the pipeline on a small sample and checking output images in the visualization step.

## Commit & Pull Request Guidelines
- Commit history uses short, present-tense summaries; some commits follow Conventional Commit prefixes (e.g., `feat:`).
- Prefer clear, single-purpose commits like `feat: add gaussian mask tuning` or `fix: handle missing image size`.

PRs should include the following:
- A concise summary of what changed.
- Example commands run and a note about sample input/output paths.
- Screenshots or sample output images when visual outputs change.

## Data & Configuration Notes
- Do not commit large datasets or generated outputs; keep them in local folders or ignored paths.
- When changing CLI defaults, update `data.sh` and mention the new defaults in the PR description.
