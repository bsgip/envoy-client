import enum
from functools import reduce

from pydantic import validators


# Pydantic doesn't have a validator for IntFlags. So we will create our own validated
# type.
#
# Checking the range of values will probably become superfluous in Python 3.11
# since the IntFlag in that version has the ability to use STRICT boundary conditions
# that raise errors when values fall outside the permissible range. For more info see:
# https://docs.python.org/3.11/library/enum.html#enum.FlagBoundary
#
# Based on code from: https://github.com/samuelcolvin/pydantic/issues/1841
class StrictIntFlag(enum.IntFlag):
    @classmethod
    def __get_validators__(cls):
        yield validators.int_validator
        yield cls.validate

    @classmethod
    def validate(cls, value):
        if not isinstance(value, cls):
            if isinstance(value, int):
                max_value = 1 + reduce(lambda a, b: a + 2 ** b, range(len(cls)))
                if value >= 0 and value <= max_value:
                    return value
                raise ValueError(
                    f"{value} outside permitted range of IntFlag (0-{max_value})"
                )
            raise TypeError(f"{value!r} should be a {cls.__name__} value")
        return value
