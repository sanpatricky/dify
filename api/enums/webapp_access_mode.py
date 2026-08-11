from enum import StrEnum


class WebAppAccessMode(StrEnum):
    PUBLIC = "public"
    PRIVATE = "private"
    PRIVATE_ALL = "private_all"
    SSO_VERIFIED = "sso_verified"
