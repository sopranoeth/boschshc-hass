"""Platform for climate integration."""
import logging

from boschshcpy import SHCClimateControl, SHCSession
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    HVAC_MODE_AUTO,
    HVAC_MODE_HEAT,
    PRESET_BOOST,
    PRESET_ECO,
    PRESET_NONE,
    SUPPORT_PRESET_MODE,
    SUPPORT_TARGET_TEMPERATURE,
)
from homeassistant.const import ATTR_TEMPERATURE, TEMP_CELSIUS

from . import DOMAIN
from .entity import SHCEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the SHC climate platform."""

    entities = []
    session: SHCSession = hass.data[DOMAIN][config_entry.entry_id]

    for climate in session.device_helper.climate_controls:
        room_id = climate.room_id
        entities.append(
            ClimateControl(
                device=climate,
                parent_id=session.information.name,
                entry_id=config_entry.entry_id,
                name=f"Room Climate {session.room(room_id).name}",
            )
        )

    if entities:
        async_add_entities(entities)


class ClimateControl(SHCEntity, ClimateEntity):
    """Representation of a SHC room climate control."""

    def __init__(
        self,
        device: SHCClimateControl,
        parent_id: str,
        name: str,
        entry_id: str,
    ):
        """Initialize the SHC device."""
        super().__init__(device=device, parent_id=parent_id, entry_id=entry_id)
        self._name = name

    @property
    def name(self):
        return self._name

    @property
    def temperature_unit(self):
        return TEMP_CELSIUS

    @property
    def current_temperature(self):
        return self._device.temperature

    @property
    def max_temp(self):
        return 30.0

    @property
    def min_temp(self):
        return 5.0

    @property
    def target_temperature(self):
        return self._device.setpoint_temperature

    @property
    def target_temperature_step(self):
        return 0.5

    @property
    def hvac_mode(self):
        if (
            self._device.operation_mode
            == SHCClimateControl.RoomClimateControlService.OperationMode.AUTOMATIC
        ):
            return HVAC_MODE_AUTO
        if (
            self._device.operation_mode
            == SHCClimateControl.RoomClimateControlService.OperationMode.MANUAL
        ):
            return HVAC_MODE_HEAT
        # _LOGGER.warning(
        #     f"Unknown operation mode! {self._device.operation_mode} != {SHCClimateControl.RoomClimateControlService.OperationMode.MANUAL}"
        # )

    @property
    def hvac_modes(self):
        return [HVAC_MODE_AUTO, HVAC_MODE_HEAT]

    # @property
    # def hvac_action(self):
    #     if self.valve_tappet_position > 5:
    #         return CURRENT_HVAC_HEAT
    #     else:
    #         return CURRENT_HVAC_IDLE

    @property
    def preset_mode(self):
        if self._device.supports_boost_mode:
            if self._device.boost_mode:
                return PRESET_BOOST

        if self._device.low:
            return PRESET_ECO

        return PRESET_NONE

    @property
    def preset_modes(self):
        presets = [PRESET_NONE, PRESET_ECO]
        if self._device.supports_boost_mode:
            presets += [PRESET_BOOST]
        return presets

    @property
    def supported_features(self):
        return SUPPORT_TARGET_TEMPERATURE + SUPPORT_PRESET_MODE

    def set_temperature(self, **kwargs):
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return

        if self.min_temp <= temperature <= self.max_temp:
            self._device.setpoint_temperature = float(temperature)

    def set_hvac_mode(self, hvac_mode: str):
        if hvac_mode not in self.hvac_modes:
            return

        if hvac_mode == HVAC_MODE_AUTO:
            self._device.operation_mode = (
                SHCClimateControl.RoomClimateControlService.OperationMode.AUTOMATIC
            )
        elif hvac_mode == HVAC_MODE_HEAT:
            self._device.operation_mode = (
                SHCClimateControl.RoomClimateControlService.OperationMode.MANUAL
            )

    def set_preset_mode(self, preset_mode: str):
        if preset_mode not in self.preset_modes:
            return

        if preset_mode == PRESET_NONE:
            if self._device.supports_boost_mode:
                if self._device.boost_mode:
                    self._device.boost_mode = False

            if self._device.low:
                self._device.low = False

        elif preset_mode == PRESET_BOOST:
            if not self._device.boost_mode:
                self._device.boost_mode = True

            if self._device.low:
                self._device.low = False

        elif preset_mode == PRESET_ECO:
            if self._device.supports_boost_mode:
                if self._device.boost_mode:
                    self._device.boost_mode = False

            if not self._device.low:
                self._device.low = True
