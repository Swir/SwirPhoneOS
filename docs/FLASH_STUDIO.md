# Flash Studio Developer GUI

The GUI is a read-only desktop companion, not an OS installer or a beta release. Run from the repository root:

```sh
python -m swirphoneos.studio
```

Use Python 3.11 or newer with Tk and a graphical desktop. No third-party Python package is required at runtime. Some Linux Python installations package Tk separately. The CLI continues to work without opening a window.

## Workflow

Choose **ADB** or **Fastboot** in the transport selector, then select the absolute path to your own trusted Android SDK executable matching that mode. Connect exactly one local USB phone in the appropriate state. The GUI invokes only the same strict read-only command allowlists as the CLI. It does not download tools, install drivers, enable debugging, reboot, unlock, erase, change slots, boot an image, flash, format, root, relock or restore the phone.

ADB mode reads the bounded property set used by `python -m swirphoneos inspect`. Fastboot mode queries only the bounded Fastboot/FastbootD `getvar` set used by `python -m swirphoneos inspect-fastboot`. Switching transport clears the selected tool and stale report/export state.

A worker thread performs the bounded transport requests; only the main thread touches Tk. An elapsed-time indicator is shown instead of a fictional completion percentage. Duplicate scans are blocked. Starting another attempt clears the previous report, and failures never leave an old export enabled. Closing the window does not initiate any phone action; a daemon worker may finish its already-running read-only request without accessing Tk.

## Device profile hints

Successful scans are combined with the local metadata registry under `device_packs/`. Matching device-reported codename/model/product values can produce a profile **hint**, but a hint is never trusted hardware identity and never authorizes installation. Unified reports enforce:

- `identity_verified: false`
- `swirphoneos_support: NOT_VALIDATED`
- `flash_allowed: false`

Ambiguous matches expose no candidate. The current OnePlus Nord AC2003 (`avicii`) profile remains `PLANNED_NOT_SUPPORTED`. Firmware baseline, partition map, recovery and physical-device evidence are required before support can be claimed.

The equivalent CLI surface is:

```powershell
python -m swirphoneos inspect-device --transport adb --tool "C:\Android\platform-tools\adb.exe"
python -m swirphoneos inspect-device --transport fastboot --tool "C:\Android\platform-tools\fastboot.exe"
```

## Local report export

Save a successful report to a **new** absolute `.json` path. The exporter refuses existing files and target symlinks rather than overwriting them. Files request owner-only permissions on POSIX; Windows access follows the local filesystem security model. There is no automatic upload or persistent path history.

Both the legacy ADB schema and the unified transport/profile schema are revalidated before export. Safety/provenance fields cannot be promoted to supported/flashable state. No serial or IMEI property is intentionally requested. Nevertheless, model/manufacturer/product values originate from the phone and can be spoofed or contain unexpected information. Review reports before public sharing. Raw exceptions, process output and local tool paths are not shown in GUI errors.

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

GUI tests use real Tk windows with synthetic inspection and never contact a phone unless the owner explicitly launches a diagnostic with a trusted Android SDK tool. Portable tests also cover unified ADB/Fastboot state and fail-closed profile assessment.

## Windows developer packaging

`.github/workflows/package-studio.yml` defines the developer artifact path. It uses Windows x64, Python 3.14 and pinned PyInstaller 6.22.3, builds `packaging/SwirPhoneStudio.spec`, smoke-tests the frozen GUI, writes `SHA256SUMS.txt` and uploads the executable as a short-lived GitHub Actions artifact.

The spec bundles both `swirphoneos/locales/catalogs.json` and the `device_packs` metadata registry. The latter is required so the frozen GUI can produce the same local profile hints as source execution without downloading anything. The application window still uses the embedded SwirPhoneOS icon. This pipeline is not a Release channel, installer, driver bundle or evidence that USB diagnostics work on a real Windows machine with a phone attached.

To reproduce the developer build manually from the repository root on Windows:

```powershell
python -m pip install --disable-pip-version-check pyinstaller==6.22.3
pyinstaller --noconfirm --clean packaging/SwirPhoneStudio.spec
$env:SWIR_GUI_TESTS = '1'
.\dist\SwirPhoneStudio.exe --smoke-test
Get-FileHash -Algorithm SHA256 .\dist\SwirPhoneStudio.exe
```

## Outstanding

Real Windows/USB evidence, signed installer/release packaging, driver guidance, backup/restore and every write-capable installation path remain unfinished. Fastboot/profile integration is now present only as **read-only diagnostics plus metadata hints**; it is not a supported-device or flashing implementation. The packaged developer executable does not complete the desktop milestone or authorize beta publication. Consult `ROADMAP.md` and `BETA_RELEASE_GATE.md`.
