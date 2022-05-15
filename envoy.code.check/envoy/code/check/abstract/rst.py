
import re
from functools import cached_property
from typing import List, Optional, Pattern

import abstracts

from envoy.code.check import interface


INVALID_REFLINK_RE = r"[^:]ref:`|^ref:`"
PUNCTUATION_RE = r".*\. <[^<]+>`$|.*\.$"

# Make sure backticks come in pairs.
# Exceptions: reflinks (ref:`` where the backtick won't be preceded by a space
#             links `title <link>`_ where the _ is checked for in the regex.
SINGLE_TICK_RE = r"[^`:]`[^`]+`[^`]"
REF_TICKS_RE = r":`[^`]+`"
LINK_TICKS_RE = r"[^`]`[^`]+`_"


@abstracts.implementer(interface.IRSTCheck)
class ABackticksCheck(metaclass=abstracts.Abstraction):
    error_message = "Single backticks found {single_ticks}"

    def __call__(self, text: str) -> Optional[str]:
        single_ticks = self._find_single_ticks(text)
        return (
            self.error_message.format(single_ticks=', '.join(single_ticks))
            if single_ticks
            else None)

    @cached_property
    def link_ticks_re(self) -> Pattern[str]:
        return re.compile(LINK_TICKS_RE)

    @cached_property
    def ref_ticks_re(self) -> Pattern[str]:
        return re.compile(REF_TICKS_RE)

    @cached_property
    def single_tick_re(self) -> Pattern[str]:
        return re.compile(SINGLE_TICK_RE)

    def _find_single_ticks(
            self,
            text: str) -> List[str]:
        return [
            bad_ticks[1:-1]
            for bad_ticks
            in self.single_tick_re.findall(
                self._strip_valid_refs(text))]

    def _strip_valid_refs(self, text: str) -> str:
        for reflink in self.ref_ticks_re.findall(text):
            text = text.replace(reflink, "")
        for extlink in self.link_ticks_re.findall(text):
            text = text.replace(extlink, "")
        return text


@abstracts.implementer(interface.IRSTCheck)
class AReflinksCheck(metaclass=abstracts.Abstraction):
    error_message = "Invalid ref link `ref:` should be `:ref:`"

    def __call__(self, text: str) -> Optional[str]:
        return (
            self.error_message
            if self.invalid_reflink_re.findall(text)
            else None)

    @cached_property
    def invalid_reflink_re(self) -> Pattern[str]:
        return re.compile(INVALID_REFLINK_RE)


@abstracts.implementer(interface.IRSTCheck)
class APunctuationCheck(metaclass=abstracts.Abstraction):
    error_message = "Missing punctuation \"...{snippet}\""

    def __call__(self, text: str) -> Optional[str]:
        return (
            self.error_message.format(snippet=text[-30:])
            if not self._check_punctuation(text)
            else None)

    @cached_property
    def punctuation_re(self) -> Pattern[str]:
        return re.compile(PUNCTUATION_RE, re.DOTALL)

    def _check_punctuation(
            self,
            text: str) -> bool:
        return bool(
            self.punctuation_re.match(text)
            # Ends with a list
            or text.split("\n")[-1].startswith("  *"))
