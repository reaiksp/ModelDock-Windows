# Third-party software

ModelDock 0.1.0 uses the following components. These projects are not the publisher of ModelDock.

| Component | Version | License / source |
|---|---|---|
| Python | 3.12 (build runtime) | PSF license, https://www.python.org/downloads/source/ |
| PySide6 / Shiboken6 | 6.8.3 | LGPL-3.0 / GPL / commercial alternatives, https://code.qt.io/pyside/pyside-setup.git/tree/?h=v6.8.3 |
| Qt Core / Gui / Widgets | 6.8.3 | LGPL-3.0 / GPL / commercial alternatives, https://download.qt.io/archive/qt/6.8/6.8.3/submodules/ |
| psutil | 7.0.0 | BSD-3-Clause, https://github.com/giampaolo/psutil/tree/release-7.0.0 |
| PyInstaller bootloader | 6.12.0 | GPL with bootloader exception, https://pyinstaller.org/en/v6.12.0/license.html |

License texts and relevant installed distribution notices are copied into `licenses/` during the build. Qt and PySide6 are dynamically linked in the `_internal` directory; this distribution does not prohibit reverse engineering for debugging modifications to LGPL components, and users may replace those libraries with compatible modified versions. The ModelDock application source and build instructions are included in `source/` in the portable distribution to support rebuilding against replacements. No changes are made to Qt or PySide6.

Ollama is downloaded separately from https://ollama.com/download and is governed by its own terms and notices (source: https://github.com/ollama/ollama, MIT license). Model weights are downloaded separately on user request. Model licenses and upstream notices can be found at https://ollama.com/library/qwen3 and https://ollama.com/library/qwen2.5-coder and their linked upstream repositories. No model weights are bundled with ModelDock.

PySide6 package metadata includes a commercial-license text describing an alternative license option; its presence does not grant a commercial Qt license. This distribution uses the available LGPL terms for the imported Qt modules.
