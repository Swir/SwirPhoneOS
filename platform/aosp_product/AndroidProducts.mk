# SwirPhoneOS developer product registration.
# These sources are intended to live under vendor/swir/products in a pinned AOSP tree.

PRODUCT_MAKEFILES := \
    $(LOCAL_DIR)/swirphoneos_cf_x86_64.mk \
    $(LOCAL_DIR)/swirphoneos_gsi_arm64.mk

COMMON_LUNCH_CHOICES := \
    swirphoneos_cf_x86_64-aosp_current-userdebug \
    swirphoneos_gsi_arm64-aosp_current-userdebug
