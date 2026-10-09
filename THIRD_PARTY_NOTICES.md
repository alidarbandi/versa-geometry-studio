# Third-party components

Versa Geometry Studio's own source code is distributed under the MIT license in `LICENSE`. The Windows build contains unmodified, dynamically linked third-party runtime libraries. Their licenses and copyright notices continue to apply independently of the application's MIT license.

## Qt, PySide6 and Shiboken 6.11.1

Copyright The Qt Company Ltd. and other contributors. PySide6 and the Qt modules used by this application are available under their upstream open-source licenses, including LGPLv3. Copies of LGPLv3 and GPLv3 are in `third_party_licenses/`. The DLLs remain separate in `_internal/PySide6` and `_internal/shiboken6`; recipients may replace or rebuild those libraries. This application imposes no restriction on modifying them or reverse engineering for debugging such modifications. No Qt/PySide6 source changes were made.

Upstream source corresponding to the shipped version and build instructions are available at no charge:

* [PySide6 and Shiboken source, v6.11.1](https://github.com/qt/pyside-setup/tree/v6.11.1) — [source archive](https://github.com/qt/pyside-setup/archive/refs/tags/v6.11.1.tar.gz).
* [Qt Base source, v6.11.1](https://github.com/qt/qtbase/tree/v6.11.1) — [source archive](https://github.com/qt/qtbase/archive/refs/tags/v6.11.1.tar.gz). Contains Qt Core, Gui, Widgets, Network and OpenGL and their third-party component sources/notices.
* [Qt SVG source, v6.11.1](https://github.com/qt/qtsvg/tree/v6.11.1) — [source archive](https://github.com/qt/qtsvg/archive/refs/tags/v6.11.1.tar.gz).
* [Qt Image Formats source, v6.11.1](https://github.com/qt/qtimageformats/tree/v6.11.1) — [source archive](https://github.com/qt/qtimageformats/archive/refs/tags/v6.11.1.tar.gz).
* [Qt for Python build instructions](https://doc.qt.io/qtforpython-6/building_from_source/index.html).

The [PySide6 distribution page](https://pypi.org/project/PySide6/6.11.1/) describes its open-source licensing. [Qt licensing and third-party attributions](https://doc.qt.io/qt-6.11/licensing.html) and [Qt for Python third-party attributions](https://doc.qt.io/qtforpython-6/licenses.html) describe individual component terms. Bundled HTML attribution pages in `third_party_licenses/qt-attributions/` retain the upstream details. Unused Qt PDF and virtual-keyboard plugins and their QML/Quick dependencies are excluded from this desktop build.

## NumPy 2.2.6 and OpenBLAS

Copyright NumPy Developers and other contributors. NumPy is distributed under the BSD license. Its bundled OpenBLAS and other third-party notices are included in `third_party_licenses/numpy-LICENSE.txt` and the original package's license material.

Source: [NumPy v2.2.6](https://github.com/numpy/numpy/tree/v2.2.6); [source archive](https://github.com/numpy/numpy/archive/refs/tags/v2.2.6.tar.gz). OpenBLAS build information is available from `numpy.show_config()` in the recorded environment; the tested wheel uses OpenBLAS 0.3.29. [OpenBLAS source](https://github.com/OpenMathLib/OpenBLAS/tree/v0.3.29).

## Python 3.12.13

Copyright Python Software Foundation and contributors. The PSF license and bundled third-party terms are reproduced in `third_party_licenses/python-LICENSE.txt`. Source: [CPython v3.12.13](https://github.com/python/cpython/tree/v3.12.13). The local build uses the unmodified CPython distribution supplied by [python-build-standalone](https://github.com/astral-sh/python-build-standalone).

## PyInstaller 6.22.3

The bootloader is distributed under the GPL with the PyInstaller bootloader exception. The exception permits distribution of the application under its own license. See `third_party_licenses/pyinstaller-COPYING.txt` and [upstream source](https://github.com/pyinstaller/pyinstaller/tree/v6.22.3).

## Platform runtime and trademarks

Microsoft Visual C++ runtime components supplied with the Python/Qt packages retain Microsoft's applicable redistributable terms. Windows is a Microsoft trademark. ZEISS and Xradia are trademarks of their respective owners. This project is independent of those organizations.
