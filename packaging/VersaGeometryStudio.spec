# Reproducible native Windows one-folder build. Run from the repository root.
from pathlib import Path

root = Path(SPECPATH).parent
a = Analysis(
    [str(root / 'packaging' / 'entrypoint.py')],
    pathex=[str(root)],
    binaries=[],
    datas=[(str(root / 'profiles'), 'profiles'), (str(root / 'examples'), 'examples'),
           (str(root / 'README.md'), '.'), (str(root / 'LICENSE'), '.'),
           (str(root / 'THIRD_PARTY_NOTICES.md'), '.'),
           (str(root / 'third_party_licenses'), 'third_party_licenses')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'scipy', 'PyQt5', 'PyQt6'],
    noarchive=False,
)
# Qt's general GUI hook collects optional image/input plugins. This Widgets
# application does not use PDF, Qt Virtual Keyboard, QML, or Quick. Exclude
# those plugins together with their otherwise-unused runtime dependencies.
unused = {
    'qpdf.dll', 'qtvirtualkeyboardplugin.dll', 'Qt6Pdf.dll',
    'Qt6VirtualKeyboard.dll', 'Qt6Qml.dll', 'Qt6QmlMeta.dll',
    'Qt6QmlModels.dll', 'Qt6QmlWorkerScript.dll', 'Qt6Quick.dll',
}
a.binaries = [entry for entry in a.binaries if Path(entry[0]).name not in unused]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='VersaGeometryStudio',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          console=False, disable_windowed_traceback=False,
          version=str(root / 'packaging' / 'version_info.txt'))
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='VersaGeometryStudio')
