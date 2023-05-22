'''
Created on 22.02.2022

@author: sparky2021
'''
"""Example for LED on/off."""
import asyncio

import sys

from xknx import XKNX
from xknx.prog.dev_management import NM_EXISTS, NM_OK, NM_TIME_OUT, NetworkManagement
from xknx.telegram.address import IndividualAddress
from xknx.prog.device import ProgDevice

import logging


async def main():
    """Write inidividual address to device."""
    xknx = XKNX(log_directory="/home/sparky2021/tmp")
    #xknx = XKNX()
    await xknx.start()
    
    async with NetworkManagement(xknx).connect_device(
        address=IndividualAddress("1.1.2")
    ) as network_management:

        result = await network_management.read_memory(96, 1)
        print ("1st read", result)
        input("weiter ...")
        result = await network_management.read_memory(96, 1)
        print ("2st read", result)
        input("weiter ...")
        
        return_code = await network_management.switch_led(1)
        print("On: ", return_code)
        input("Zum Ausschalten ENTER drücken")
        return_code = await network_management.switch_led(0)
        print("off: ", return_code)

    await asyncio.sleep(5)
    await xknx.stop()


#logging.basicConfig(level=logging.INFO)
#logging.getLogger("xknx.log").level = logging.DEBUG
#logging.getLogger("xknx.knx").level = logging.DEBUG
logging.getLogger("xknx.cemi").level = logging.DEBUG
#logging.getLogger("xknx.raw_socket").level = logging.DEBUG
logging.getLogger("xknx.management.procedures").level = logging.DEBUG
logging.getLogger("xknx.management").level = logging.DEBUG

asyncio.run(main())

