# Versa Geometry Studio v1.0.0

An offline desktop planner and teaching tool for two-stage X-ray microscopy geometry.

## Download and run

1. Download **VersaGeometryStudio-v1.0.0-windows-x64.zip** below.
2. Right-click the ZIP in File Explorer and choose **Extract All**.
3. Open the extracted **VersaGeometryStudio** folder.
4. Double-click **VersaGeometryStudio.exe**.

No Python installation or terminal command is required. Keep `_internal` beside the executable. The archive also includes example plans, instrument profiles, the README, and third-party license notices. GitHub's automatic source-code ZIP is for developers and does not contain the Windows executable.

## Included

* Linked top/side ray diagrams, finite-sample perspective projection and synthetic transmission preview.
* Exact or no-coarser acquisition sampling and coverage planning with explicit full/half and horizontal/vertical/diagonal angle conventions.
* Source and scintillator sliders, direct dragging, magnification/separation locks, undo/redo, and dark/light themes.
* Objective-specific profiles, calibration provenance, configurable physical constraints, interior ROI and sampled rotation coverage.
* Full-precision plan JSON, geometry PNG/SVG, detector PNG, parameter CSV/JSON and Markdown summary exports.

## Validation and compatibility

All **67 automated tests** pass. The native GUI was exercised at 1366 × 768 and 1920 × 1080. The Windows x64 build was built and launched on Windows 11 build 26100 with CPython 3.12.13, PySide6/Qt 6.11.1 and NumPy 2.2.6. The extracted release ZIP was also smoke-tested before upload.

Qt 6.11 supports Windows 10 1809+ and Windows 11. Windows 10 was not tested for this delivery; Windows 10 LTSB 1607 is outside the supported range. The executable is unsigned.

Hardware travel, clearances, objective availability and calibration, and stage-coordinate mapping require local instrument data. The demonstration profile and synthetic attenuation preview do not claim manufacturer validation or predict real spatial resolution or exposure.

`SHA256SUMS.txt` contains the SHA-256 checksum for the Windows ZIP. Source code and build instructions are available in the repository at tag **v1.0.0**.
