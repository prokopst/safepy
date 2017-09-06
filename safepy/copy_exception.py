from copy import copy


def copy_exception_with_traceback(exception):
    return copy(exception).with_traceback(exception.__traceback__)
