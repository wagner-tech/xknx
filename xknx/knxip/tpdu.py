"""
TPDU is a more general KNX protocol frame for non T_DATA requests.
"""
from __future__ import annotations

from xknx.exceptions import UnsupportedCEMIMessage
from xknx.telegram import Telegram, TPDUType
from xknx.telegram.address import GroupAddress, IndividualAddress, InternalGroupAddress

from .knxip_enum import CEMIMessageCode


class TPDU:
    """Alternative class to CEMIFrame for non T_DATA requests."""

    def __init__(
        self,
        src_addr: IndividualAddress = IndividualAddress(None),
    ):
        """Initialize TPDU."""
        self.src_addr = src_addr
        self.destination_address: GroupAddress | IndividualAddress | InternalGroupAddress = IndividualAddress(
            None
        )
        self.tpdu_type: TPDUType | None = None
        self.code: CEMIMessageCode | None = None
        self.data = bytes()

    @staticmethod
    def init_from_telegram(
        telegram: Telegram,
        src_addr: IndividualAddress = IndividualAddress(None),
    ) -> TPDU:
        """Return TPDU from a Telegram."""
        tpdu = TPDU(src_addr)
        tpdu.telegram = telegram
        return tpdu

    @property
    def telegram(self) -> Telegram:
        """Return telegram."""
        return Telegram(
            destination_address=self.destination_address,
        )

    @telegram.setter
    def telegram(self, telegram: Telegram) -> None:
        """Set telegram."""
        self.destination_address = telegram.destination_address
        self.tpdu_type = telegram.tpdu_type

    def from_knx(self, raw: bytes) -> int:
        """Parse/deserialize from KNX/IP raw data."""
        try:
            self.code = CEMIMessageCode(raw[0])
        except ValueError:
            raise UnsupportedCEMIMessage(
                f"CEMIMessageCode not implemented: {raw[0]} in CEMI: {raw.hex()}"
            )
        self.destination_address = IndividualAddress((raw[6], raw[7]))
        if raw[9] == 0x80:
            self.tpdu_type = TPDUType.T_CONNECT
        elif raw[9] == 0x81:
            self.tpdu_type = TPDUType.T_DISCONNECT
        elif raw[9] == 0xC2:
            self.tpdu_type = TPDUType.T_ACK
        elif raw[9] == 0xC6:
            self.tpdu_type = TPDUType.T_ACK_NUMBERED
        else:
            raise RuntimeError("Invalid TPDUType-code: " + str(raw[9]))
        self.data = raw
        return 10

    def calculated_length(self) -> int:
        """Length of PDU."""
        # pylint: disable=no-self-use
        return 10

    def to_knx(self) -> bytes:
        """Convert PDU to KNX."""
        data = bytes((0x11, 0x00, 0xB0, 0x60, 0x00, 0x00))
        if not isinstance(self.destination_address, IndividualAddress):
            raise RuntimeError("IndividualAddress expected")
        data += bytes(self.destination_address.to_knx())
        if self.tpdu_type == TPDUType.T_CONNECT:
            return data + bytes((0x00, 0x80))
        if self.tpdu_type == TPDUType.T_DISCONNECT:
            return data + bytes((0x00, 0x81))
        if self.tpdu_type == TPDUType.T_ACK:
            return data + bytes((0x00, 0xC2))
        if self.tpdu_type == TPDUType.T_ACK_NUMBERED:
            return data + bytes((0x00, 0xC6))
        raise RuntimeError("Invalid TPDUType: " + str(self.tpdu_type))

    def __str__(self) -> str:
        """Return object as readable string."""
        return f'<TPDUFrame DestinationAddress="{self.destination_address.__repr__()}"'
