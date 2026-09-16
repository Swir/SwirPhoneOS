# SwirPhoneOS developer product for the standard AOSP x86_64-only Cuttlefish phone.
# No security defaults, signing keys, root policy or device claims are weakened here.

$(call inherit-product, device/google/cuttlefish/vsoc_x86_64_only/phone/aosp_cf.mk)

PRODUCT_NAME := swirphoneos_cf_x86_64
PRODUCT_DEVICE := vsoc_x86_64_only
PRODUCT_BRAND := Swir
PRODUCT_MANUFACTURER := Swir
PRODUCT_MODEL := SwirPhoneOS Cuttlefish Developer

# Source-ready first-party apps. Runtime status remains unverified until an AOSP build/boot succeeds.
PRODUCT_PACKAGES += \
    SwirCalculator \
    SwirSettings \
    SwirFiles \
    SwirDeviceCare \
    SwirUpdate \
    SwirPrivacy \
    SwirClock
