#!/usr/bin/env python3
import asyncio
import iterm2
import random
import sys

favocolormap =  [
            "AlienBlood",
            "Argonaut",
            "Arthur",
            "Aurora",
            "Batman",
            "Belafonte Night",
            "BirdsOfParadise",
            "BlulocoDark",
            "Breeze",
            "Calamity",
            "Chalk",
            "Chalkboard",
            "Ciapre",
            "CrayonPonyFish",
            "Dark+",
            "Desert",
            "DjangoRebornAgain",
            "ENCOM",
            "Earthsong",
            "Elemental",
            "Flatland",
            "ForestBlue",
            "Gruvbox Dark",
            "Guezwhoz",
            "Highway",
            "Hipster Green",
            "Hopscotch.256",
            "Hopscotch",
            "Hybrid",
            "IC_Green_PPL",
            "IC_Orange_PPL",
            "JetBrains Darcula",
            "Laser",
            "MaterialDark",
            "MaterialOcean",
            "Medallion",
            "MonaLisa",
            "Monokai Remastered",
            "Monokai Soda",
            "Monokai Vivid",
            "Neopolitan",
            "NightLion v2",
            "Obsidian",
            "OceanicMaterial",
            "Ollie",
            "OneHalfDark",
            "Operator Mono Dark",
            "Overnight Slumber",
            "PaleNightHC",
            "Raycast_Dark",
            "Rippedcasts",
            "Royal",
            "SeaShells",
            "SoftServer",
            "Solarized Darcula",
            "Solarized Dark",
            "Sundried",
            "Tomorrow Night Bright",
            "Tomorrow Night Burns",
            "Tomorrow Night Eighties",
            "Treehouse",
            "UnderTheSea",
            "idleToes",
            "midnight-in-mojave", #normal
            "AtomOneLight",     #light
            "Belafonte Day", #light
            "Gruvbox Light", #light
            "Man Page", #light
            "Novel", #light
            "OneHalfLight", #light
            "Solarized Light", #light
            "Violet Light", #light
            "coffee_theme", #light
            "iceberg-light", #light
           ]


async def changecurapp(connection):
    app = await iterm2.async_get_app(connection)
    for cur_window in app.terminal_windows:
        for cur_tab in cur_window.tabs:
            for cur_session in cur_tab.sessions:
                if theme != '':
                    randomcolor = theme
                else:
                    randomcolor = random.choice(favocolormap)
                preset = await iterm2.ColorPreset.async_get(connection, randomcolor)
                if not preset:
                    return
                profile = await cur_session.async_get_profile()
                if not profile:
                    return
                await profile.async_set_color_preset(preset)

async def changecurwindow(connection):
    app = await iterm2.async_get_app(connection)
    cur_window = app.current_terminal_window
    for cur_tab in cur_window.tabs:
        for cur_session in cur_tab.sessions:
            if theme != '':
                randomcolor = theme
            else:
                randomcolor = random.choice(favocolormap)
            preset = await iterm2.ColorPreset.async_get(connection, randomcolor)
            if not preset:
                return
            profile = await cur_session.async_get_profile()
            if not profile:
                return
            await profile.async_set_color_preset(preset)

async def changecurtab(connection):
    app = await iterm2.async_get_app(connection)
    cur_window = app.current_terminal_window
    cur_tab = cur_window.current_tab
    for cur_session in cur_tab.sessions:
        if theme != '':
            randomcolor = theme
        else:
            randomcolor = random.choice(favocolormap)
        preset = await iterm2.ColorPreset.async_get(connection, randomcolor)
        if not preset:
            return
        profile = await cur_session.async_get_profile()
        if not profile:
            return
        await profile.async_set_color_preset(preset)

async def changecursession(connection):
    app = await iterm2.async_get_app(connection)
    cur_window = app.current_terminal_window
    cur_tab = cur_window.current_tab
    cur_session = cur_tab.current_session
    if theme != '':
        randomcolor = theme
    else:
        randomcolor = random.choice(favocolormap)
    preset = await iterm2.ColorPreset.async_get(connection, randomcolor)
    if not preset:
        return
    profile = await cur_session.async_get_profile()
    if not profile:
        return
    await profile.async_set_color_preset(preset)
    print("Current color is : " + randomcolor)

async def main(connection):
    if act in ["session", "s"]:
        await changecursession(connection)
    elif act in ["tab", "t"]:
        await changecurtab(connection)
    elif act in ["window", "w"]:
        await changecurwindow(connection)
    elif act in ["all", "a"]:
        await changecurapp(connection)
    else:
        print("Wrong action ...")


# 通过传参 变更session、tab、window、all
act = sys.argv[1]
if len(sys.argv) >= 3:
    theme = sys.argv[2]
else:
    theme = ''

try:
    iterm2.run_until_complete(main)
except:
    print("Unable to connect on iTerm2 application")