"""Python and PostgreSQL enum definitions used by GymFlow models."""

from enum import Enum, StrEnum

from sqlalchemy.dialects.postgresql import ENUM


class UserRole(StrEnum):
    CLIENT = "client"
    TRAINER = "trainer"
    ADMIN = "admin"


class MembershipStatus(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class PaymentStatus(StrEnum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


class PaymentMethod(StrEnum):
    CARD = "card"
    CASH = "cash"
    TRANSFER = "transfer"
    SIMULATED = "simulated"


class BookingStatus(StrEnum):
    CONFIRMED = "confirmed"
    WAITLIST = "waitlist"
    CANCELLED = "cancelled"
    ATTENDED = "attended"
    NO_SHOW = "no_show"


class CheckInMethod(StrEnum):
    QR = "qr"
    MANUAL = "manual"
    CARD = "card"


def _enum_values(enum_class: type[Enum]) -> list[str]:
    return [member.value for member in enum_class]


user_role_enum = ENUM(UserRole, name="user_role", values_callable=_enum_values, create_type=False)
membership_status_enum = ENUM(
    MembershipStatus, name="membership_status", values_callable=_enum_values, create_type=False
)
payment_status_enum = ENUM(
    PaymentStatus, name="payment_status", values_callable=_enum_values, create_type=False
)
payment_method_enum = ENUM(
    PaymentMethod, name="payment_method", values_callable=_enum_values, create_type=False
)
booking_status_enum = ENUM(
    BookingStatus, name="booking_status", values_callable=_enum_values, create_type=False
)
checkin_method_enum = ENUM(
    CheckInMethod, name="checkin_method", values_callable=_enum_values, create_type=False
)
