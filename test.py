from pathlib import Path

workdir = Path.cwd()

print(workdir)

p = workdir / "README.md"
print(p.resolve())

print(p.is_relative_to(workdir))
print(p.is_relative_to(Path("/Users/xxx")))

print(p.read_text())