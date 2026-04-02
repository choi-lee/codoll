"""py2app build configuration for Codoll desktop pet."""
from setuptools import setup

APP = ["run.py"]
OPTIONS = {
    "argv_emulation": False,
    "plist": {
        "CFBundleName": "Hamzzi",
        "CFBundleDisplayName": "Hamzzi",
        "CFBundleIdentifier": "com.codoll.desktoppet",
        "CFBundleVersion": "0.1.0",
        "CFBundleShortVersionString": "0.1.0",
        "LSUIElement": True,  # Hide from Dock (accessory app)
    },
    "packages": ["codoll"],
    "includes": [
        "AppKit",
        "Foundation",
        "Quartz",
        "objc",
    ],
}

setup(
    app=APP,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
