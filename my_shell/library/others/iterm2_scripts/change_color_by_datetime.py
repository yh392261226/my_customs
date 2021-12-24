#!/usr/bin/env python3
import asyncio
import datetime
import iterm2

# Clock time to change colors.
LIGHT_TIME = (7, 0)
DARK_TIME = (17, 0)

# Color presets to use
LIGHT_PRESET_NAME = "material"
DARK_PRESET_NAME = "ENCOM"

# Profiles to update
PROFILES = ["Default"]

def get_datetime(t, time):
    return datetime.datetime(t.year, t.month, t.day, time[0], time[1])

def datetime_after(t, time):
    today = get_datetime(t, time)
    if today > t:
        return today
    # Same time tomorrow
    return today + datetime.timedelta(1)


def next_deadline_after(t):
    light_deadline = datetime_after(t, LIGHT_TIME)
    dark_deadline = datetime_after(t, DARK_TIME)
    if light_deadline < dark_deadline:
        return (LIGHT_PRESET_NAME, light_deadline)
    return (DARK_PRESET_NAME, dark_deadline)


def get_duration():
    now = datetime.datetime.now()
    preset_name, deadline = next_deadline_after(now)
    duration = (deadline - now).seconds
    print("Sleep for {} seconds until {}".format(duration, deadline))
    return duration, preset_name


async def set_colors(connection, preset_name):
    print("Change to preset {}".format(preset_name))
    preset = await iterm2.ColorPreset.async_get(connection, preset_name)
    for partial in (await iterm2.PartialProfile.async_query(connection)):
        if partial.name in PROFILES:
            await partial.async_set_color_preset(preset)


async def main(connection):
    now = datetime.datetime.now()
    begin = get_datetime(now, LIGHT_TIME)
    end = get_datetime(now, DARK_TIME)
    if (now > begin and now < end):
        await set_colors(connection, LIGHT_PRESET_NAME)
    else:
        await set_colors(connection, DARK_PRESET_NAME)
    while True:
        duration, preset_name = get_duration()
        await asyncio.sleep(duration)
        await set_colors(connection, preset_name)
        await asyncio.sleep(1)


iterm2.run_forever(main)