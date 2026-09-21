# SwirPhoneOS developer ARM64 Generic System Image product.
# This is a build target only. It does not claim universal phone compatibility,
# Treble/VTS compliance, a safe install path, or support for any physical device.
# Platform security/signing defaults remain intact.

# The standard AOSP ARM64 product provides the generic ARM64 system/product/vendor
# configuration. Its GSI release block is guarded by TARGET_PRODUCT=aosp_arm64,
# so the custom SwirPhoneOS product explicitly inherits gsi_release as well.
$(call inherit-product, $(SRC_TARGET_DIR)/product/aosp_arm64.mk)
$(call inherit-product, $(SRC_TARGET_DIR)/product/gsi_release.mk)

PRODUCT_NAME := swirphoneos_gsi_arm64
PRODUCT_DEVICE := generic_arm64
PRODUCT_BRAND := Swir
PRODUCT_MANUFACTURER := Swir
PRODUCT_MODEL := SwirPhoneOS ARM64 GSI Developer

# Keep one reviewed HOME surface in the first-beta GSI image. This does not
# claim compatibility with any physical device; AOSP SystemUI remains the
# authoritative lock-screen implementation for the beta baseline.
PRODUCT_PACKAGES := $(filter-out Launcher3 Launcher3QuickStep Launcher3QuickStepGo,$(PRODUCT_PACKAGES))

# Source-ready first-party apps. A built system.img still requires Treble/VTS and
# exact-device validation before it can be described as compatible or installable.
PRODUCT_PACKAGES += \
    SwirLauncher \
    SwirPhone \
    SwirMessages \
    SwirCamera \
    SwirCalculator \
    SwirSettings \
    SwirFiles \
    SwirBrowser \
    SwirDeviceCare \
    SwirUpdate \
    SwirPrivacy \
    SwirClock \
    SwirNotes \
    SwirCalendar \
    SwirWeather \
    SwirGallery \
    SwirRecorder \
    SwirContacts \
    SwirBackup \
    SwirApps \
    SwirRoot
