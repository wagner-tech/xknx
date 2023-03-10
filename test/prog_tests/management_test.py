"""Unit test for xknx programming management."""
import asyncio
from unittest.mock import patch

import pytest

from xknx import XKNX
from xknx.prog.management import NM_EXISTS, NM_OK, NetworkManagement
from xknx.prog.device import ProgDevice
from xknx.telegram import IndividualAddress


@pytest.mark.asyncio
class TestProgrammingInterface:
    """Test class for programming interface test."""

    called = 0
    responder_result = []
    responder_result_idx = -1
    
    async def responder(self, *p):
        self.responder_result_idx += 1
        return self.responder_result[self.responder_result_idx]

    async def fake_progdevice_connect(self, *p):
        if self.called == 0:
            self.called = 1
            return False
        else:
            return True

#    async def fake_devicedescriptor_read_response(self, *p):
#        """Fake function for evicedescriptor_read_response."""
#        if self.called == 1:
#            return
#        self.called += 1
#        await self.time_travel(60.0)
    
    @patch("xknx.prog.device.ProgDevice.connect", autospec=True)
    @patch("xknx.prog.device.ProgDevice.individualaddress_read_response", autospec=True)
    @patch("xknx.prog.device.ProgDevice.propertyvalue_read", autospec=True)
    async def test_write_individual_address_success(
        self,
        mock_propertyvalue_read,
        mock_individualaddress_read_response,
        mock_progdevice_connect,
        #time_travel,
    ):
        """Test IndividualAddress_Write with success."""
        xknx = XKNX()
        #self.time_travel = time_travel
        mock_progdevice_connect.side_effect = (
            self.fake_progdevice_connect
        )
        network_management = NetworkManagement(xknx)
        return_code = await network_management.individualaddress_write(
            IndividualAddress("1.2.1")
        )
        assert return_code == NM_OK

    @patch("xknx.prog.device.ProgDevice.devicedescriptor_read_response", autospec=True)
    async def test_write_individual_address_exists(
        self, mock_devicedescriptor_read_response
    ):
        """Test IndividualAddress_Write with existing device."""
        xknx = XKNX()
        network_management = NetworkManagement(xknx)
        return_code = await network_management.individualaddress_write(
            IndividualAddress("1.2.1")
        )
        assert return_code == NM_EXISTS

    @patch("xknx.prog.device.ProgDevice.connect", autospec=True)
    @patch("xknx.prog.device.ProgDevice.memory_read_response", autospec=True)
    @patch("xknx.prog.device.ProgDevice.memory_write", autospec=True)
    async def test_switch_led(
        self,
        mock_memory_write,
        mock_memory_read_response,
        mock_progdevice_connect,
        ):
        # set mock procedures
        mock_progdevice_connect.side_effect = (self.responder)
        mock_memory_read_response.side_effect = (self.responder)
        mock_memory_write.side_effect = (self.responder)
        self.responder_result = [True, [0,0,b"\x00"], None]
        # start test
        xknx = XKNX()
        network_management = NetworkManagement(xknx)
        return_code = await network_management.switch_led(
            IndividualAddress("1.2.1"),
            1
        )
        assert return_code == NM_OK
