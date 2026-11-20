import phonenumbers
from phonenumbers.phonenumberutil import NumberParseException, PhoneNumberFormat


def normalize_phone_number(phone_number: str) -> str:
    """Validate an international phone number and return its E.164 representation."""
    try:
        parsed_phone_number = phonenumbers.parse(phone_number.strip(), None)
    except NumberParseException as exc:
        raise ValueError("Enter a valid international phone number.") from exc

    if not phonenumbers.is_possible_number(parsed_phone_number) or not phonenumbers.is_valid_number(
        parsed_phone_number
    ):
        raise ValueError("Enter a valid international phone number.")

    return phonenumbers.format_number(parsed_phone_number, PhoneNumberFormat.E164)
