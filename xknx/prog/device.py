"""This module implements the application layer functionality of a device."""
from __future__ import annotations

import asyncio
import logging

from enum import Enum
from typing import TYPE_CHECKING, Tuple

from xknx.exceptions import (
    CommunicationError,
    ConfirmationError,
    ManagementConnectionError,
    ManagementConnectionRefused,
    ManagementConnectionTimeout,
)
from xknx.management.management import Management
from xknx.management.management import MANAGAMENT_ACK_TIMEOUT
from xknx.management.procedures import nm_individual_address_check
from xknx.telegram import (
    IndividualAddress,
    Priority,
    Telegram,
    TelegramDirection,
    apci,
)
from xknx.telegram.address import GroupAddress, GroupAddressType
from xknx.telegram.apci import (
    APCIExtendedService,
    APCIService,
    DeviceDescriptorRead,
    IndividualAddressRead,
    IndividualAddressWrite,
    MemoryRead,
    MemoryResponse,
    MemoryWrite,
    PropertyValueRead,
    Restart,
)
from xknx.telegram.tpci import (
    TAck,
    TConnect,
    TDisconnect,
    TDataConnected,
    TNak,
)

if TYPE_CHECKING:
    from xknx.xknx import XKNX


logger = logging.getLogger("xknx.management.procedures")
logger = logging.getLogger("xknx.cemi")

class ConnectionState(Enum):
    """Connection State."""

    NOT_CONNECTED = 0
    A_CONNECTED = 1


class ProgDevice:
    """This Class defines a device as programming unit (A_Device)."""

    def __init__(
        self,
        xknx: XKNX,
        ind_add: IndividualAddress,
        group_address_type: GroupAddressType = GroupAddressType.LONG,
    ):
        """Init this class."""
        self.xknx = xknx
        self.ind_add = ind_add
        self.group_address_type = group_address_type
        self.last_telegram: Telegram|None = None
        self.sequence_number = 0
        self.connection_status = ConnectionState.NOT_CONNECTED
        self.p2p_connection = None

    async def connect(self) -> bool:
        """Try to establish a connection to device."""
        try:
            self.p2p_connection = await self.xknx.management.connect(
                address=IndividualAddress(self.ind_add))
            try:
                response = await self.p2p_connection.request(
                    payload=apci.DeviceDescriptorRead(descriptor=0),
                    expected=apci.DeviceDescriptorResponse,
                )

            except ManagementConnectionTimeout as ex:
                # if nothing is received (-> timeout) IA is free
                logger.debug("No device answered to connection attempt. %s", ex)
                await self.p2p_connection.disconnect()
                return False
            if isinstance(response.payload, apci.DeviceDescriptorResponse):
                # if response is received IA is occupied
                logger.debug("Device found at %s", self.ind_add)
                self.connection_status = ConnectionState.A_CONNECTED
                return True
            return False
        except ManagementConnectionRefused as ex:
            # if Disconnect is received immediately, IA is occupied
            logger.debug("Device does not support transport layer connections. %s", ex)
            self.connection_status = ConnectionState.A_CONNECTED
            return True

    async def finish(self):
        if self.connection_status == ConnectionState.A_CONNECTED:
            await self.t_disconnect()

    async def individualaddress_read_response(self) -> IndividualAddress | None:
        """Process a IndividualAddress_Read_Response."""
        special_connection = await self.xknx.management.register_special()
        while True:
            response = await special_connection.request(
                payload=IndividualAddressRead(),
                expected=apci.IndividualAddressResponse,
            )
            if response:
                return response
            
            await asyncio.sleep(2)
            

    async def individualaddress_write(self) -> None:
        """Perform a IndividualAddress_Write."""
        special_connection = await self.xknx.management.register_special()
        await special_connection._send_data(
            IndividualAddressWrite(self.ind_add)
        )

    async def memory_read_response(self, address: int = 0, count: int = 0) -> Tuple[int,int,bytes]:
        """Process a DeviceDescriptor_Read_Response."""
        response = await self.p2p_connection.request(
            payload=MemoryRead(address, count),
            expected=apci.MemoryResponse,
        )
        return (
            response.payload.address,
            response.payload.count,
            response.payload.data,
        )

    async def memory_write(
        self, address: int = 0, count: int = 0, data: bytes = bytes()
    ) -> None:

        await self.p2p_connection._send_data(
            MemoryWrite(address, data, count),
        )

    async def propertyvalue_read(self) -> None:
        """Perform a PropertyValue_Read."""
        await self.p2p_connection._send_data(
            PropertyValueRead(0, 0x0B, 1, 1),
        )

    async def restart(self) -> None:
        """Perform a Restart."""
        # A_Restart will not be ACKed by the device, so it is manually sent to avoid timeout and retry
        seq_num = next(self.p2p_connection.sequence_number)
        telegram = Telegram(
            destination_address=self.p2p_connection.address,
            source_address=self.xknx.current_address,
            payload=apci.Restart(),
            tpci=TDataConnected(sequence_number=seq_num),
        )
        await self.xknx.cemi_handler.send_telegram(telegram)
    
    async def t_disconnect(self) -> None:
        """Perform a T_Disconnect."""
        if self.p2p_connection:
            await self.p2p_connection.disconnect()

# static fabric method
async def create_and_connect(
    xknx: XKNX,
    ind_add: IndividualAddress,
    group_address_type: GroupAddressType = GroupAddressType.LONG,
):
    dev = ProgDevice(xknx, ind_add, group_address_type)
    if not await dev.connect():
        raise RuntimeError(f"Could not connect to device {ind_add}")
    return dev


