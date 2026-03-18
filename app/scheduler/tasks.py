"""
APScheduler task functions.

These are the concrete job coroutines registered with the scheduler engine.
They run in the background on a fixed schedule.

Each task creates its own database session — it does NOT reuse request-scoped sessions.
"""

import logging
from datetime import UTC
from typing import Any

logger = logging.getLogger(__name__)


async def poll_all_devices() -> None:
    """
    Fetch state for all active devices and write snapshots to DB.
    Registered: every 60 seconds.
    """
    from app.db.session import async_session_factory
    from app.dependencies import get_provider
    from app.devices.service import DeviceService

    try:
        provider = get_provider()
        async with async_session_factory() as session:
            service = DeviceService(session, provider)
            count = await service.poll_and_snapshot_all()
            await session.commit()
        logger.debug("poll_all_devices: wrote %d snapshots", count)
    except Exception as exc:
        logger.error("poll_all_devices failed: %s", exc)


async def evaluate_all_rules() -> None:
    """
    Evaluate all enabled automation rules and execute triggered actions.
    Registered: every 60 seconds.
    """
    from datetime import datetime

    from app.db.session import async_session_factory
    from app.dependencies import get_provider
    from app.scheduler.repository import AutomationRuleRepository

    try:
        provider = get_provider()
        async with async_session_factory() as session:
            repo = AutomationRuleRepository(session)
            rules = await repo.get_all(enabled_only=True)

            triggered = 0
            for rule in rules:
                try:
                    should_fire = await _evaluate_rule(rule, provider)
                    if should_fire:
                        await _execute_action(rule.action_config, provider)
                        rule.last_triggered = datetime.now(UTC)
                        triggered += 1
                except Exception as rule_exc:
                    logger.warning("Rule '%s' evaluation failed: %s", rule.name, rule_exc)

            await session.commit()

        if triggered > 0:
            logger.info("evaluate_all_rules: triggered %d rule(s)", triggered)

    except Exception as exc:
        logger.error("evaluate_all_rules failed: %s", exc)


async def refresh_weather_cache() -> None:
    """
    Force-refresh the weather cache from OpenWeatherMap.
    Registered: every 30 minutes.
    """
    from app.db.session import async_session_factory
    from app.weather.service import WeatherService

    try:
        async with async_session_factory() as session:
            service = WeatherService(session)
            await service.refresh()
            await session.commit()
        logger.debug("refresh_weather_cache: cache updated")
    except Exception as exc:
        logger.error("refresh_weather_cache failed: %s", exc)


async def _evaluate_rule(rule: Any, provider: Any) -> bool:
    """
    Evaluate whether an automation rule's conditions are met.

    Returns True if the rule should fire, False otherwise.
    """
    from datetime import datetime

    trigger_type = getattr(rule, "trigger_type", "")
    config = getattr(rule, "trigger_config", {})

    if trigger_type == "time":
        # Check if current time is within the specified window
        now = datetime.now(UTC)
        start_time_str = config.get("start_time", "00:00")
        end_time_str = config.get("end_time", "23:59")

        start_h, start_m = map(int, start_time_str.split(":"))
        end_h, end_m = map(int, end_time_str.split(":"))
        current_minutes = now.hour * 60 + now.minute
        start_minutes = start_h * 60 + start_m
        end_minutes = end_h * 60 + end_m

        return start_minutes <= current_minutes <= end_minutes

    elif trigger_type == "device_state":
        ain = config.get("ain")
        property_name = config.get("property")
        operator = config.get("operator", "eq")
        threshold = config.get("value")

        if not ain or not property_name:
            return False

        state = await provider.get_device_state(ain)
        current_value = getattr(state, property_name, None)

        if current_value is None or threshold is None:
            return False

        return _compare(current_value, operator, threshold)

    elif trigger_type == "weather":
        property_name = config.get("property")  # e.g. "temperature", "humidity"
        operator = config.get("operator", "lt")
        threshold = config.get("value")

        if not property_name or threshold is None:
            return False

        from app.db.session import async_session_factory
        from app.weather.service import WeatherService

        async with async_session_factory() as session:
            weather_service = WeatherService(session)
            cached = await weather_service.get_current()

        if cached is None:
            return False

        current_value = getattr(cached, property_name, None)
        if current_value is None:
            return False

        return _compare(float(current_value), operator, float(threshold))

    return False


def _compare(value: float, operator: str, threshold: float) -> bool:
    if operator == "lt":
        return value < threshold
    if operator == "lte":
        return value <= threshold
    if operator == "gt":
        return value > threshold
    if operator == "gte":
        return value >= threshold
    if operator == "eq":
        return value == threshold
    return False


async def _execute_action(action_config: dict[str, Any], provider: Any) -> None:
    """Execute a device_control action."""
    ain = action_config.get("ain")
    action = action_config.get("action")
    value = action_config.get("value")

    if not ain or not action:
        return

    if action == "on":
        await provider.set_switch(ain, True)
    elif action == "off":
        await provider.set_switch(ain, False)
    elif action == "temperature" and value is not None:
        await provider.set_temperature(ain, float(value))
    elif action == "brightness" and value is not None:
        await provider.set_dimmer(ain, int(value))
