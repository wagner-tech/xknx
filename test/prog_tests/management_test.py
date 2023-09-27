"""Unit test for xknx programming management."""
import asyncio
from unittest.mock import patch

import pytest

from xknx import XKNX
from xknx.prog.dev_management import NM_EXISTS, NM_OK, NetworkManagement
from xknx.prog.device import ProgDevice
from xknx.telegram import IndividualAddress, apci
from xknx.telegram.apci import MemoryResponse

from xknx.exceptions import (
    ManagementConnectionRefused,
    ManagementConnectionTimeout,
)
from voluptuous.schema_builder import Self


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
    
    async def raise_ManagementConnectionTimeout(self, *pp, **np):
        raise ManagementConnectionTimeout("mock_P2PConnection_request")
    
#    async def fake_devicedescriptor_read_response(self, *p):
#        """Fake function for evicedescriptor_read_response."""
#        if self.called == 1:
#            return
#        self.called += 1
#        await self.time_travel(60.0)
    @patch("xknx.management.management.Management.connect", autospec=True)
    @patch("xknx.management.management.P2PConnection.disconnect", autospec=True)
    @patch("xknx.management.management.P2PConnection.request", autospec=True)
    @patch("xknx.management.management.SimpleSendResponse.request", autospec=True)
    @patch("xknx.management.management.SimpleSendResponse._send_data", autospec=True)
    @patch("xknx.cemi.cemi_handler.CEMIHandler.send_telegram", autospec=True)
    async def test_write_individual_address_success(
        self,
        mock_CEMIHandler_send_telegram,
        mock_SimpleSendResponse_send_data,
        mock_SimpleSendResponse_request,
        mock_P2PConnection_request,
        mock_disconnect,
        mock_connect,
    ):
        """Test IndividualAddress_Write with success."""
        xknx = XKNX()
        #self.time_travel = time_travel
        mock_P2PConnection_request.side_effect = ( self.raise_ManagementConnectionTimeout )
        
        network_management = NetworkManagement(xknx)
        return_code = await network_management.individualaddress_write(
            IndividualAddress("1.2.1")
        )
        assert return_code == NM_OK

    async def raise_ManagementConnectionRefused(self, *pp, **np):
        raise ManagementConnectionRefused("mock_connect")


    @patch("xknx.management.management.P2PConnection.connect", autospec=True)
    async def test_write_individual_address_exists(
        self, 
        mock_connect,
    ):
        """Test IndividualAddress_Write with existing device."""
        
        mock_connect.side_effect = ( self.raise_ManagementConnectionRefused )
                
        xknx = XKNX()
        network_management = NetworkManagement(xknx)
        return_code = await network_management.individualaddress_write(
            IndividualAddress("1.2.1")
        )
        assert return_code == NM_EXISTS
    
    async def request(self, *pp, **np):
        return self

    async def _send_data(self, *pp, **np):
        return None

    @patch("xknx.management.management.Management.connect", autospec=True)
    async def test_switch_led(
        self,
        mock_connect,
        ):
        # set mock procedures
        #mock_progdevice_connect.side_effect = (self.responder)
        #mock_memory_read_response.side_effect = (self.responder)
        #mock_memory_write.side_effect = (self.responder)
        #self.responder_result = [True, [0,0,b"\x00"], None]

        mock_connect.side_effect = lambda dummy, address: self
        
        
        # start test
        xknx = XKNX()
        network_management = NetworkManagement(xknx)

        self.payload = apci.DeviceDescriptorResponse()
        return_code = await network_management.connect_managed_device(IndividualAddress("1.2.1"))
        assert return_code == NM_OK
        
        self.payload = MemoryResponse(96, bytes([0]))
        return_code = await network_management.switch_led(1)
        assert return_code == NM_OK
        return_code = await network_management.switch_led(0)
        assert return_code == NM_OK
