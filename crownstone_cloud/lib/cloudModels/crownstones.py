from crownstone_cloud._RequestHandlerInstance import RequestHandler
from typing import Optional
import logging
import asyncio

_LOGGER = logging.Logger(__name__)


class Crownstones:
    """Handler for the crownstones of a sphere"""

    def __init__(self, loop: asyncio.AbstractEventLoop, sphere_id: str) -> None:
        """Init"""
        self.loop = loop
        self.crownstones: Optional[dict] = None
        self.sphere_id = sphere_id

    def __iter__(self):
        """Iterate over crownstones"""
        return iter(self.crownstones.values())

    async def update(self) -> None:
        """
        Update all cloud data
        The requests are done separately for testing.
        """
        # get all data first
        await self.update_crownstone_data()
        # get the other data concurrently
        await asyncio.gather(
            self.update_state(),
            self.update_abilities()
        )

    async def update_crownstone_data(self) -> None:
        """
        Get the crownstones data from the cloud
        This will replace all current data from the cloud with new data
        """
        self.crownstones = {}
        crownstone_data = await RequestHandler.get('Spheres', 'ownedStones', model_id=self.sphere_id)
        for crownstone in crownstone_data:
            self.crownstones[crownstone['id']] = Crownstone(self.loop, crownstone)

    async def update_state(self) -> None:
        """Replaces the switch state of all crownstones with that of the cloud."""
        for crownstone in self.crownstones.values():
            crownstone_state = await RequestHandler.get('Stones', 'currentSwitchState', model_id=crownstone.cloud_id)
            crownstone.state = crownstone_state['switchState']

    async def update_abilities(self) -> None:
        """Get the abilities for all crownstones"""
        # only dimming is requested for now
        for crownstone in self.crownstones.values():
            abilities = await RequestHandler.get('Stones', 'abilities', model_id=crownstone.cloud_id)
            for ability in abilities:
                if ability['type'] == 'dimming':
                    crownstone.dimming_enabled = ability['enabled']
                    crownstone.dimming_synced_to_crownstone = ability['syncedToCrownstone']

    def update_sync(self) -> None:
        """Sync function for updating the crownstone data"""
        self.loop.run_until_complete(self.update())

    def find(self, crownstone_name: str) -> object or None:
        """Search for a crownstone by name and return crownstone object if found"""
        for crownstone in self.crownstones.values():
            if crownstone_name == crownstone.name:
                return crownstone

        return None

    def find_by_id(self, crownstone_id) -> object or None:
        """Search for a crownstone by id and return crownstone object if found"""
        return self.crownstones[crownstone_id]


class Crownstone:
    """Represents a Crownstone"""

    def __init__(self, loop: asyncio.AbstractEventLoop, data: dict) -> None:
        self.loop = loop
        self.data = data
        self.state: Optional[float] = None
        self.dimming_enabled: Optional[bool] = None
        self.dimming_synced_to_crownstone: Optional[bool] = None

    @property
    def name(self) -> str:
        return self.data['name']

    @property
    def unique_id(self) -> int:
        return self.data['uid']

    @property
    def cloud_id(self) -> str:
        return self.data['id']

    @property
    def type(self) -> str:
        return self.data['type']

    @property
    def sw_version(self) -> str:
        return self.data['firmwareVersion']

    async def turn_on(self) -> None:
        """Async turn this crownstone on"""
        await RequestHandler.put('Stones', 'setSwitchStateRemotely', model_id=self.cloud_id,
                                 command='switchState', value=1)

    def turn_on_sync(self) -> None:
        """Sync turn on this crownstone"""
        self.loop.run_until_complete(self.turn_on())

    async def turn_off(self) -> None:
        """Async turn this crownstone off"""
        await RequestHandler.put('Stones', 'setSwitchStateRemotely', model_id=self.cloud_id,
                                 command='switchState', value=0)

    def turn_off_sync(self) -> None:
        """Sync turn off this crownstone"""
        self.loop.run_until_complete(self.turn_off())

    async def set_brightness(self, percentage: int) -> None:
        """
        Set the brightness of this crownstone, if dimming enabled

        :param percentage: the brightness percentage (0 - 100)
        """
        if self.dimming_enabled:
            if self.dimming_synced_to_crownstone:
                if percentage < 0 or percentage > 100:
                    raise ValueError("Enter a percentage between 0 and 100")
                else:
                    brightness = percentage / 100
                    await RequestHandler.put('Stones', 'setSwitchStateRemotely', model_id=self.cloud_id,
                                             command='switchState', value=brightness)
            else:
                _LOGGER.error("Dimming is enabled but not synced to crownstone yet. Make sure to be in your sphere "
                              "and have Bluetooth enabled")
        else:
            _LOGGER.error("Dimming is not enabled for this crownstone. Go to the crownstone app to enable it")

    def set_brightness_sync(self, percentage: int) -> None:
        """
        Sync set the brightness of this crownstone, if dimming enabled

        :param percentage: the brightness percentage (0 - 100)
        """
        self.loop.run_until_complete(self.set_brightness(percentage))
