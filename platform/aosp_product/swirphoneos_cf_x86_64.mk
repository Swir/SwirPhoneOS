# SwirPhoneOS developer product for the standard AOSP x86_64-only Cuttlefish phone.
# No security defaults, signing keys, root policy or device claims are weakened here.

$(call inherit-product, device/google/cuttlefish/vsoc_x86_64_only/phone/aosp_cf.mk)

PRODUCT_NAME := swirphoneos_cf_x86_64
PRODUCT_DEVICE := vsoc_x86_64_only
PRODUCT_BRAND := Swir
PRODUCT_MANUFACTURER := Swir
PRODUCT_MODEL := SwirPhoneOS Cuttlefish Developer

# First-beta HOME surface: keep exactly one reviewed launcher in the product so
# boot does not stop at a launcher chooser. AOSP SystemUI remains authoritative
# for the lock screen until a separately verified Swir lock-screen integration exists.
PRODUCT_PACKAGES := $(filter-out Launcher3 Launcher3QuickStep Launcher3QuickStepGo,$(PRODUCT_PACKAGES))

# Keep the full source-contract inventory visible to host source validation without
# installing these post-Beta modules into the frozen first-Beta image.
SWIR_POST_BETA_SOURCE_MODULES := \
    SwirPhone \
    SwirContacts \
    SwirMessages \
    SwirCamera \
    SwirGallery \
    SwirBrowser \
    SwirClock \
    SwirCalculator \
    SwirNotes \
    SwirRecorder \
    SwirCalendar \
    SwirWeather \
    SwirBackup \
    SwirApps

# FINISH FIRST: package only the six frozen registry-managed first-Beta apps plus
# SwirLauncher. The remaining source-ready apps stay available for post-Beta work
# but must not silently expand the first-Beta build/runtime acceptance surface.
PRODUCT_PACKAGES += \
    SwirLauncher \
    SwirSettings \
    SwirFiles \
    SwirDeviceCare \
    SwirUpdate \
    SwirPrivacy \
    SwirRoot
