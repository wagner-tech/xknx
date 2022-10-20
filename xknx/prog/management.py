"""This modul implements the management procedures as described in KNX-Standard 3.5.2."""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from xknx.prog.device import ProgDevice, create_and_connect
from xknx.telegram.address import GroupAddress, IndividualAddress
from xknx.devices import device

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
        self._managed_dev: ProgDevice|None = None

    @property
    def managed_dev(self):
        return self._managed_dev

    async def set_managed_dev(self, dev):
        if self._managed_dev:
            await self._managed_dev.finish()
        self._managed_dev = dev

    async def telegram_received_cb(self, telegram: Telegram) -> None:
        """Do something with the received telegram."""
        if self.managed_dev:
            await self.managed_dev.process_telegram(telegram)

    async def individualaddress_write(self, ind_add: IndividualAddress) -> int:
        """Perform IndividualAdress_Write."""

        # try to connect to device
        await self.set_managed_dev(ProgDevice(self.xknx, ind_add))
        if await self.managed_dev.connect():
            await self.managed_dev.t_disconnect()
            return NM_EXISTS

        # wait until PROG button is pressed
        try:
            print("Press PROG button!")
            await asyncio.wait_for(
                self.managed_dev.individualaddress_read_response(), 600
            )
        except asyncio.TimeoutError:
            return NM_TIME_OUT

        await self.managed_dev.individualaddress_write()

        # Addition from ETS reverse engeneering
        await self.set_managed_dev(create_and_connect(self.xknx, ind_add))
        await self.managed_dev.propertyvalue_read()
        await self.managed_dev.restart()
        await asyncio.sleep(1)
        await self.managed_dev.t_disconnect()

        return NM_OK

    async def switch_led(self, ind_add, value):
        # define device
        await self.set_managed_dev(ProgDevice(self.xknx, ind_add))

        # check if device present
        if not await self.managed_dev.connect():
            return NM_NOT_EXISTS

        if value == 0:
            resp = await self.managed_dev.memory_read_response(96, 1)
            if resp[2] == b"\x81":
                # LED on
                await self.managed_dev.memory_write(96, 1, b"\x00", True)
                print("LED ausgeschaltet.")
            else:
                print("LED brennt nicht.")
        elif value == 1:
            resp = await self.managed_dev.memory_read_response(96, 1)
            if resp[2] == b"\x00":
                # LED off
                await self.managed_dev.memory_write(96, 1, b"\x81", True)
                print("LED eingeschaltet.")
            else:
                print("LED brennt schon.")
        else:
            raise RuntimeError("value parameter must be 0 or 1.")

        # await self.managed_dev.finish()

        return NM_OK
