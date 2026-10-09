"""Create the portable Windows release and a SHA-256 manifest.

The ZIP contains a single VersaGeometryStudio folder, including all runtime
DLLs, so recipients can extract it and double-click the executable.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import zipfile

from versa_geometry_studio import __version__


def package_release(root: Path, version: str = __version__, build_dir: Path | None = None):
    source = build_dir.resolve() if build_dir else root / "dist" / "VersaGeometryStudio"
    if not (source / "VersaGeometryStudio.exe").is_file() or not (source / "_internal").is_dir():
        raise ValueError("Build the Windows application first using build-windows.ps1")
    target = root / "release"
    target.mkdir(exist_ok=True)
    archive = target / f"VersaGeometryStudio-v{version}-windows-x64.zip"
    prefix = "VersaGeometryStudio/"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as stream:
        for path in sorted(source.rglob("*")):
            if path.is_file():
                stream.write(path, prefix + path.relative_to(source).as_posix())
        for name in ("README.md", "LICENSE", "THIRD_PARTY_NOTICES.md", "requirements-tested.txt"):
            stream.write(root / name, prefix + name)
        for name in ("examples", "profiles", "third_party_licenses"):
            for path in sorted((root / name).rglob("*")):
                if path.is_file():
                    stream.write(path, prefix + path.relative_to(root).as_posix())
    checksum = hashlib.sha256()
    with archive.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(block)
    digest = checksum.hexdigest()
    manifest = target / "SHA256SUMS.txt"
    manifest.write_text(f"{digest}  {archive.name}\n", encoding="ascii")
    return archive, manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", default=__version__)
    parser.add_argument("--build-dir", type=Path, help="Application folder containing VersaGeometryStudio.exe")
    args = parser.parse_args()
    if args.version != __version__:
        parser.error("Release version must match versa_geometry_studio.__version__")
    archive, manifest = package_release(Path(__file__).resolve().parents[1], args.version, args.build_dir)
    print(f"Created {archive.name} ({archive.stat().st_size / 1024**2:.1f} MiB)")
    print(manifest.read_text(encoding="ascii").strip())


if __name__ == "__main__":
    main()
