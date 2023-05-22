"""This modul implements the management procedures as described in KNX-Standard 3.5.2."""
from __future__ import annotations

from contextlib import asynccontextmanager
import asyncio
from typing import TYPE_CHECKING

from xknx.prog.device import ProgDevice, create_and_connect, ConnectionState
from xknx.telegram.address import GroupAddress, IndividualAddress
from _operator import add

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
    
    async def connect_managed_device(self, ind_add: IndividualAddress) -> int:
        await self.set_managed_dev(ProgDevice(self.xknx, ind_add))
        if await self.managed_dev.connect():
            return NM_OK
        return NM_NOT_EXISTS

    async def disconnect_managed_device(self):
        await self.managed_dev.finish()

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
        await self.managed_dev.connect()
        await self.managed_dev.propertyvalue_read()
        await self.managed_dev.restart()
        await asyncio.sleep(1)
        await self.managed_dev.t_disconnect()

        return NM_OK

    async def switch_led(self, value: int) -> int:

        if value == 0:
            resp = await self.read_memory(96, 1)
            if resp == b"\x81":
                # LED on
                await self.write_memory(96, 1, b"\x00")
                print("LED ausgeschaltet.")
            else:
                print("LED brennt nicht.")
        elif value == 1:
            resp = await self.read_memory(96, 1)
            if resp == b"\x00":
                # LED off
                await self.write_memory(96, 1, b"\x81")
                print("LED eingeschaltet.")
            else:
                print("LED brennt schon.")
        else:
            raise RuntimeError("value parameter must be 0 or 1.")

        return NM_OK

    async def write_memory(self, offset:int, count:int, data:bytes) -> int:
        # check device state
        if self.managed_dev.connection_status == ConnectionState.NOT_CONNECTED:
            raise RuntimeError("Device not connected.")

        await self.managed_dev.memory_write(offset, count, data)
        return NM_OK

    async def read_memory(self, offset:int, count:int) -> bytes:
        # check device state
        if self.managed_dev.connection_status == ConnectionState.NOT_CONNECTED:
            raise RuntimeError("Device not connected.")

        (roffset,rcount,data) = await self.managed_dev.memory_read_response(offset, count)
        if roffset != offset:
            raise RuntimeError("Cound not read from address: "+str(offset))
        if rcount != count:
            raise RuntimeError("Cound not read number of bytes: "+str(count))
        return data

    @asynccontextmanager
    async def connect_device(self, address: IndividualAddress):
        """Provide a connected device."""
        rc = await self.connect_managed_device(address)
        if rc != NM_OK:
            raise RuntimeError("Could not connect device.")
        try:
            yield self
        finally:
            await self.disconnect_managed_device()

    
    
