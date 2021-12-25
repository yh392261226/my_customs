#!/usr/bin/env python3
import asyncio
import iterm2
import random
import sys

favocolormap =  [
            "Abernathy",
            "Adventure",
            "AdventureTime",
            "Afterglow",
            "Alabaster",
            "AlienBlood",
            "Andromeda",
            "Argonaut",
            "Arthur",
            "AtelierSulphurpool",
            "AtomOneLight",
            "Aurora",
            "Ayu Mirage",
            "Banana Blueberry",
            "Batman",
            "Belafonte Day",
            "Belafonte Night",
            "BirdsOfParadise",
            "Blazer",
            "Blue Matrix",
            "BlueBerryPie",
            "BlueDolphin",
            "BlulocoDark",
            "BlulocoLight",
            "Borland",
            "Breeze",
            "Bright Lights",
            "Broadcast",
            "Brogrammer",
            "Builtin Dark",
            "Builtin Light",
            "Builtin Pastel Dark",
            "Builtin Solarized Dark",
            "Builtin Solarized Light",
            "Builtin Tango Dark",
            "Builtin Tango Light",
            "CLRS",
            "Calamity",
            "Chalk",
            "Chalkboard",
            "ChallengerDeep",
            "Chester",
            "Ciapre",
            "Cobalt Neon",
            "Cobalt2",
            "CrayonPonyFish",
            "Cyberdyne",
            "Dark Pastel",
            "Dark+",
            "Darkside",
            "Desert",
            "DimmedMonokai",
            "Django",
            "DjangoRebornAgain",
            "DjangoSmooth",
            "Doom Peacock",
            "DoomOne",
            "DotGov",
            "Dracula+",
            "Dracula",
            "Duotone Dark",
            "ENCOM",
            "Earthsong",
            "Elemental",
            "Elementary",
            "Espresso Libre",
            "Espresso",
            "Fahrenheit",
            "Fairyfloss",
            "Fideloper",
            "FirefoxDev",
            "Firewatch",
            "FishTank",
            "Flat",
            "Flatland",
            "Floraverse",
            "ForestBlue",
            "Framer",
            "FrontEndDelight",
            "FunForrest",
            "Galaxy",
            "Galizur",
            "GitHub Dark",
            "Github",
            "Glacier",
            "Grape",
            "Grass",
            "Gruvbox Dark",
            "Gruvbox Light",
            "Guezwhoz",
            "HaX0R_BLUE",
            "HaX0R_GR33N",
            "HaX0R_R3D",
            "Hacktober",
            "Hardcore",
            "Harper",
            "Highway",
            "Hipster Green",
            "Hivacruz",
            "Homebrew",
            "Hopscotch.256",
            "Hopscotch",
            "Hurtado",
            "Hybrid",
            "IC_Green_PPL",
            "IC_Orange_PPL",
            "IR_Black",
            "Jackie Brown",
            "Japanesque",
            "Jellybeans",
            "JetBrains Darcula",
            "Kibble",
            "Kolorit",
            "Konsolas",
            "Lab Fox",
            "Laser",
            "Later This Evening",
            "Lavandula",
            "LiquidCarbon",
            "LiquidCarbonTransparent",
            "LiquidCarbonTransparentInverse",
            "Man Page",
            "Mariana",
            "Material",
            "MaterialDark",
            "MaterialDarker",
            "MaterialOcean",
            "Mathias",
            "Medallion",
            "Mirage",
            "Misterioso",
            "Molokai",
            "MonaLisa",
            "Monokai Remastered",
            "Monokai Soda",
            "Monokai Vivid",
            "N0tch2k",
            "Neopolitan",
            "Neutron",
            "Night Owlish Light",
            "NightLion v1",
            "NightLion v2",
            "Nocturnal Winter",
            "Novel",
            "Obsidian",
            "Ocean",
            "OceanicMaterial",
            "Ollie",
            "OneHalfDark",
            "OneHalfLight",
            "Operator Mono Dark",
            "Overnight Slumber",
            "PaleNightHC",
            "Pandora",
            "Paraiso Dark",
            "PaulMillr",
            "PencilDark",
            "PencilLight",
            "Peppermint",
            "Piatto Light",
            "Pnevma",
            "Popping and Locking",
            "Pro Light",
            "Pro",
            "Purple Rain",
            "Rapture",
            "Raycast_Dark",
            "Raycast_Light",
            "Red Alert",
            "Red Planet",
            "Red Sands",
            "Relaxed",
            "Rippedcasts",
            "Rouge 2",
            "Royal",
            "Ryuuko",
            "Sakura",
            "Scarlet Protocol",
            "SeaShells",
            "Seafoam Pastel",
            "Seti",
            "Shaman",
            "Slate",
            "SleepyHollow",
            "Smyck",
            "Snazzy",
            "SoftServer",
            "Solarized Darcula",
            "Solarized Dark - Patched",
            "Solarized Dark Higher Contrast",
            "Solarized Dark",
            "Solarized Light",
            "SpaceGray Eighties Dull",
            "SpaceGray Eighties",
            "SpaceGray",
            "Spacedust",
            "Spiderman",
            "Spring",
            "Square",
            "Sublette",
            "Subliminal",
            "Sundried",
            "Symfonic",
            "Tango Adapted",
            "Tango Half Adapted",
            "Teerb",
            "Terminal Basic",
            "Thayer Bright",
            "The Hulk",
            "Tinacious Design (Dark)",
            "Tinacious Design (Light)",
            "Tomorrow Night Blue",
            "Tomorrow Night Bright",
            "Tomorrow Night Burns",
            "Tomorrow Night Eighties",
            "Tomorrow Night",
            "Tomorrow",
            "ToyChest",
            "Treehouse",
            "Twilight",
            "Ubuntu",
            "UltraDark",
            "UltraViolent",
            "UnderTheSea",
            "Unikitty",
            "Urple",
            "Vaughn",
            "VibrantInk",
            "Violet Dark",
            "Violet Light",
            "WarmNeon",
            "Wez",
            "Whimsy",
            "WildCherry",
            "Wombat",
            "Wryan",
            "Zenburn",
            "ayu",
            "ayu_light",
            "coffee_theme",
            "cyberpunk",
            "darkermatrix",
            "darkmatrix",
            "deep",
            "iceberg-dark",
            "iceberg-light",
            "idea",
            "idleToes",
            "jubi",
            "lovelace",
            "matrix",
            "midnight-in-mojave",
            "nord",
            "primary",
            "purplepeter",
            "rebecca",
            "shades-of-purple",
            "synthwave-everything",
            "synthwave",
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