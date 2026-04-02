# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=[],
    datas=[('codoll/assets', 'codoll/assets')],
    hiddenimports=['AppKit', 'Foundation', 'Quartz', 'objc', 'codoll', 'codoll.app', 'codoll.renderer', 'codoll.animator', 'codoll.state', 'codoll.bubble', 'codoll.schedule', 'codoll.schedule_manager', 'codoll.settings_window'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Codoll',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Codoll',
)
app = BUNDLE(
    coll,
    name='Codoll.app',
    icon=None,
    bundle_identifier=None,
)
