"""This modul implements the management procedures as described in KNX-Standard 3.5.2."""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from xknx.prog.device import ProgDevice
from xknx.telegram.address import GroupAddress, IndividualAddress

if TYPE_CHECKING:
    from xknx.telegram import Telegram
    from xknx.xknx import XKNX


NM_OK = 0
NM_EXISTS = 1
NM_TIME_OUT = 2
NM_NOT_EXISTS = 3


class NetworkManagement:
    """Class for network management functionality."""

    def __init__(self, xknx: XKNX):
        """Construct NM instance."""
        self.xknx = xknx
        xknx.telegram_queue.register_telegram_received_cb(self.telegram_received_cb)
        # map for registered devices
        self.reg_dev: dict[IndividualAddress, ProgDevice] = {}

    async def telegram_received_cb(self, telegram: Telegram) -> None:
        """Do something with the received telegram."""
        if telegram.source_address in self.reg_dev:
            await self.reg_dev[telegram.source_address].process_telegram(telegram)
        if telegram.destination_address == GroupAddress("0"):
            for reg_dev_val in self.reg_dev.values():
                await reg_dev_val.process_telegram(telegram)

    async def is_device_present(self, device: ProgDevice) -> bool:
        """Check if device is present on KNX bus."""
        try:
            await asyncio.wait_for(device.t_connect_response(), 0.5)
            return True
        except asyncio.TimeoutError:
            pass

        try:
            await asyncio.wait_for(device.devicedescriptor_read_response(0), 0.5)
            return True
        except asyncio.TimeoutError:
            pass
        return False

    async def individualaddress_write(self, ind_add: IndividualAddress) -> int:
        """Perform IndividualAdress_Write."""
        device = ProgDevice(self.xknx, ind_add)
        self.reg_dev[ind_add] = device

        # chech if IA is already present
        if await self.is_device_present(device):
            await device.t_disconnect()
            return NM_EXISTS

        # wait until PROG button is pressed
        try:
            await asyncio.wait_for(device.individualaddress_read_response(), 600)
        except asyncio.TimeoutError:
            return NM_TIME_OUT

        await device.individualaddress_write()

        # Addition from ETS reverse engeneering
        await device.t_connect()
        try:
            await asyncio.wait_for(device.devicedescriptor_read_response(0), 1.0)
        except asyncio.TimeoutError:
            raise RuntimeError(f"No device response from {ind_add}")

        await device.propertyvalue_read()
        await device.restart()
        await asyncio.sleep(1)
        await device.t_disconnect()
        return NM_OK
