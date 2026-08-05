The following lint errors were found:
- F401 [*] `pytest` imported but unused
- F401 [*] `re` imported but unused
- PLW1510 `subprocess.run` without explicit `check` argument

Fixed them by removing unused imports and by adding check=false param