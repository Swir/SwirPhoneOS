# Flash Studio Developer GUI

The GUI is a read-only desktop companion, not an OS installer or a beta release. Run from the repository root:

```sh
python -m swirphoneos.studio
```

Use Python 3.11 or newer with Tk and a graphical desktop. No third-party Python package is required at runtime. Some Linux Python installations package Tk separately. The existing CLI continues to work without opening a window.

## Workflow

Select the absolute path to your own trusted Android SDK ADB executable. Connect exactly one local USB phone with debugging explicitly authorized on the phone. Click **Inspect USB phone**. The GUI performs the same limited property reads as the CLI, with no arbitrary command interface. It does not download tools, install drivers, enable debugging, reboot, unlock or write the phone.

A worker thread performs the bounded ADB requests; only the main thread touches Tk. An elapsed-time indicator is shown instead of a fictional completion percentage. Duplicate scans are blocked. Starting another attempt clears the previous report, and failures never leave an old export enabled. Closing the window does not initiate any phone action; a daemon worker may finish its already-running read-only request without accessing Tk.

The report is device-reported information, not trusted hardware identification, a complete compatibility assessment or flashing authorization. Unknown values stay unknown. No phone has certified support yet.

## Local report export

Save a successful report to a **new** absolute `.json` path. The exporter refuses existing files and target symlinks rather than overwriting them. A save dialog confirmation cannot override that protection; choose a different name. Files request owner-only permissions on POSIX; Windows access follows the local filesystem security model. There is no automatic upload or persistent path history.

Only the known diagnostic schema is exportable. Extra fields such as serials or ADB paths are rejected, and safety/provenance fields cannot be altered. No serial or IMEI property is requested. Nevertheless, model/manufacturer and other values originate from the phone and can be spoofed or contain unexpected information. Review reports before public sharing. Raw exceptions, process output and local tool paths are not shown in GUI errors.

## Language and branding

Localization data lives in `swirphoneos/locales/catalogs.json` rather than Python UI logic. The GUI detects the Windows user UI language on Windows, or locale environment/native locale on other hosts. Current catalogs are English (`en`), Polish (`pl`), Norwegian Bokmal (`nb`, with `no` alias), German (`de`), Spanish (`es`), French (`fr`), Portuguese (`pt`) and Arabic (`ar`). Unsupported languages fall back to English. Catalog validation enforces source-key/placeholder compatibility and records text direction; Arabic is the first RTL metadata path. The current Tk layout is not yet a complete mobile RTL implementation.

The selector changes the current window language; the selection is not persisted yet. Runtime reports retain stable English machine-readable keys. Translation data is the deliberate exception to English repository-facing documentation.

The embedded PNG is a raster of the existing `branding/swirphoneos.svg`, so runtime does not require SVG libraries or network resources. The footer opens the project GitHub page only on a user click.

## Native smoke tests

General tests intentionally skip GUI tests without an explicit graphical-test opt-in. On a Windows desktop:

```powershell
$env:SWIR_GUI_TESTS = '1'
python -m unittest discover -s tests -p test_studio_gui.py -v
python -m swirphoneos.studio --smoke-test
```

On Linux with Xvfb installed:

```sh
SWIR_GUI_TESTS=1 xvfb-run -a python -m unittest discover -s tests -p test_studio_gui.py -v
xvfb-run -a python -m swirphoneos.studio --smoke-test
```

GUI tests use real Tk windows with synthetic inspection. They test launch/icon, success, stale-result removal, error privacy, language switching, minimum layout, unavailable export and closing while reading. They do not connect a physical phone. The `--smoke-test` entry point opens and closes the UI without invoking ADB.

## Windows developer packaging

`.github/workflows/package-studio.yml` defines the reproducible developer artifact path. It uses Windows x64, Python 3.14 and pinned PyInstaller 6.22.3, builds `packaging/SwirPhoneStudio.spec`, smoke-tests the frozen GUI, writes `SHA256SUMS.txt` and uploads the executable as a short-lived GitHub Actions artifact.

The spec explicitly bundles `swirphoneos/locales/catalogs.json`, because the localization runtime loads that file through Python package resources. The application window still uses the embedded SwirPhoneOS icon. This pipeline is not a Release channel, installer, driver bundle or evidence that USB diagnostics work on a real Windows machine with a phone attached.

To reproduce the developer build manually from the repository root on Windows:

```powershell
python -m pip install --disable-pip-version-check pyinstaller==6.22.3
pyinstaller --noconfirm --clean packaging/SwirPhoneStudio.spec
$env:SWIR_GUI_TESTS = '1'
.\dist\SwirPhoneStudio.exe --smoke-test
Get-FileHash -Algorithm SHA256 .\dist\SwirPhoneStudio.exe
```

## Outstanding

Real Windows/USB evidence, Fastboot/FastbootD/profile integration in the GUI, signed installer/release packaging, driver guidance and all image/install/restore functionality are unfinished. The packaged developer executable remains read-only and does not complete the desktop milestone or authorize beta publication. Consult `ROADMAP.md` and `BETA_RELEASE_GATE.md`.
