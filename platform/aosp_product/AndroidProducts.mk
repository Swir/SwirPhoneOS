# SwirPhoneOS Cuttlefish developer product registration.
# This file is intended to live under device/swir/phone in a pinned AOSP tree.

PRODUCT_MAKEFILES := \
    $(LOCAL_DIR)/swirphoneos_cf_x86_64.mk

COMMON_LUNCH_CHOICES := \
    swirphoneos_cf_x86_64-aosp_current-userdebug
