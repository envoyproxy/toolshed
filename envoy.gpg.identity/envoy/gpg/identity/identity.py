import logging
import os
import pathlib
import pwd
import shutil
from functools import cached_property
from email.utils import formataddr, parseaddr
from typing import Iterable, Optional, Union

import gnupg  # type:ignore

from aio.core import log as _log


class GPGError(Exception):
    pass


class GPGIdentity(object):
    """A GPG identity with a signing key.

    The signing key is found either by matching provided name/email, or
    by retrieving the first private key.
    """

    def __init__(
            self,
            name: Optional[str] = None,
            email: Optional[str] = None,
            log: Optional[Union[logging.Logger, _log.StoppableLogger]] = None,
            gnupg_home: Optional[pathlib.Path] = None,
            gen_key: bool = False):
        self._provided_name = name
        self._provided_email = email
        self._log = log
        self._gen_key = gen_key
        self._gnupg_home = gnupg_home
        if gen_key:
            self.gen_key_if_missing()

    def __str__(self) -> str:
        return self.uid

    @cached_property
    def email(self) -> str:
        """Email parsed from the signing key."""
        return parseaddr(self.uid)[1]

    @property
    def fingerprint(self) -> str:
        """GPG key fingerprint."""
        return self.signing_key["fingerprint"]

    @property
    def gen_key(self) -> bool:
        """Flag to determine whether to generate missing key."""
        return self._gen_key

    @property
    def gen_key_data(self) -> str:
        """GPG data for generating a key."""
        if not (self.provided_name and self.provided_email):
            raise GPGError(
                "Both `name` and `email` must be provided to generate "
                f"a key. name: {self.provided_name}, "
                f"email: {self.provided_email}")
        return self.gpg.gen_key_input(
            name_real=self.provided_name,
            name_email=self.provided_email,
            key_type="RSA",
            key_length=2048,
            no_protection=True)

    @cached_property
    def gpg(self) -> gnupg.GPG:
        return gnupg.GPG(gnupghome=self.gnupg_home)

    @cached_property
    def gpg_bin(self) -> Optional[pathlib.Path]:
        gpg_bin = shutil.which("gpg2") or shutil.which("gpg")
        return pathlib.Path(gpg_bin) if gpg_bin else None

    @property
    def gnupg_home(self) -> pathlib.Path:
        home = (
            self._gnupg_home
            if self._gnupg_home
            else self.home.joinpath(".gnupg"))
        if not home.exists():
            home.mkdir()
        os.environ["GNUPGHOME"] = str(home)
        return home

    @cached_property
    def home(self) -> pathlib.Path:
        """Gets *and sets if required* the `HOME` env var."""
        home_dir = os.environ.get("HOME", pwd.getpwuid(os.getuid()).pw_dir)
        os.environ["HOME"] = home_dir
        return pathlib.Path(home_dir)

    @cached_property
    def log(self) -> Union[logging.Logger, _log.StoppableLogger]:
        return self._log or logging.getLogger(self.__class__.__name__)

    @property
    def provided_email(self) -> str:
        """Provided email for the identity."""
        return self._provided_email or ""

    @cached_property
    def provided_id(self) -> Optional[str]:
        """Provided name and/or email for the identity."""
        if not (self.provided_name or self.provided_email):
            return None
        return (
            formataddr((self.provided_name, self.provided_email))
            if (self.provided_name and self.provided_email)
            else (self.provided_name or self.provided_email))

    @property
    def provided_name(self) -> Optional[str]:
        """Provided name for the identity."""
        return self._provided_name

    @cached_property
    def name(self) -> str:
        """Name parsed from the signing key."""
        return parseaddr(self.uid)[0]

    @cached_property
    def signing_key(self) -> dict:
        """A `dict` representing the GPG key to sign with."""
        # if name and/or email are provided the list of keys is pre-filtered
        # but we still need to figure out which uid matched for the found key
        for key in self.gpg.list_keys(True, keys=self.provided_id):
            key = self.match(key)
            if key:
                return key
        raise GPGError(
            f"No key found for '{self.provided_id}'"
            if self.provided_id
            else "No available key")

    @property
    def uid(self) -> str:
        """UID of the identity's signing key."""
        return self.signing_key["uid"]

    def export_key(self) -> str:
        return self.gpg.export_keys(keyids=[self.signing_key["keyid"]])

    def gen_key_if_missing(self):
        try:
            self.signing_key
        except GPGError:
            key = self.gpg.gen_key(self.gen_key_data)
            if not key.fingerprint:
                raise GPGError("Failed to generate key")

    def match(self, key: dict) -> Optional[dict]:
        """Match a signing key.

        The key is found either by matching provided name/email
        or the first available private key

        the matching `uid` (or first) is added as `uid` to the dict
        """
        if self.provided_id:
            key["uid"] = self._match_key(key["uids"])
            return key if key["uid"] else None
        if self.gen_key:
            return None
        if self.log:
            self.log.warning(
                "No GPG name/email supplied, signing with first available key")
        key["uid"] = key["uids"][0]
        return key

    def _match_email(self, uids: Iterable) -> Optional[str]:
        """Match only the email."""
        for uid in uids:
            if parseaddr(uid)[1] == self.provided_email:
                return uid

    def _match_key(self, uids: Iterable) -> Optional[str]:
        """If either/both name or email are supplied it tries to match
        either/both."""
        if self.provided_name and self.provided_email:
            return self._match_uid(uids)
        elif self.provided_name:
            return self._match_name(uids)
        elif self.provided_email:
            return self._match_email(uids)

    def _match_name(self, uids: Iterable) -> Optional[str]:
        """Match only the name."""
        for uid in uids:
            if parseaddr(uid)[0] == self.provided_name:
                return uid

    def _match_uid(self, uids: Iterable) -> Optional[str]:
        """Match the whole uid - ie `Name <ema.il>`"""
        return self.provided_id if self.provided_id in uids else None
