# Dependency update process

`requirements.txt` pins the direct runtime and test dependencies. To update a
package:

1. Check the package's release history and security advisories on PyPI.
2. Update only the intended direct pin in `requirements.txt`.
3. Create a fresh Python 3.10+ virtual environment and run
   `python -m pip install -r requirements.txt`.
4. Run `python -m pytest` and `git diff --check`.
5. Record the reviewed versions, date, and test result in `BACKLOG.md`.

Do not use an unbounded upgrade command in deployment. Review transitive
dependency changes from the fresh install before merging a pin update.
