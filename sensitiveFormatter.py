import logging
import re


class SensitiveFormatter(logging.Formatter):
    """Formatter that removes sensitive information in urls."""
    @staticmethod
    def _filter(s):
        return re.sub(r':\/\/(.*?)\@', r'://', s)

    def format(self, record):
        original = logging.Formatter.format(self, record)
        return self._filter(original)

        