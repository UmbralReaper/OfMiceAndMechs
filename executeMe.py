#!/usr/bin/env python3

#####################################################################################################################
###
##      load environment and start the games main loop
#       basically nothing to see here
#       if you are a first time visitor, interaction.py, story.py and gamestate.py are probably better files to start with
#
#####################################################################################################################

# import basic libs
import sys
import json
import time

# import basic internal libs
import src.items as items
items.setup()
import src.quests as quests
import src.rooms as rooms
import src.characters as characters
import src.terrains as terrains
import src.cinematics as cinematics
import src.story as story
import src.gameMath as gameMath
import src.interaction as interaction
import src.gamestate as gamestate
import src.events as events
import src.chats as chats
import src.saveing as saveing
import src.canvas as canvas
import src.logger as logger


# import configs
import config.commandChars as commandChars
import config.names as names

# parse arguments
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("-p", "--phase", type=str, help="the phase to start in")
parser.add_argument("--unicode", action="store_true", help="force fallback encoding")
parser.add_argument("-d", "--debug", action="store_true", help="enable debug mode")
parser.add_argument("-t", "--tiles", action="store_true", help="spawn a tile based view of the map (requires pygame)")
parser.add_argument("--nourwid", action="store_true", help="do not show shell based")
parser.add_argument("-ts", "--tileSize", type=int, help="the base size of tiles")
parser.add_argument("-T", "--terrain", type=str, help="select the terrain")
parser.add_argument("-s", "--seed", type=str, help="select the seed of a new game")
parser.add_argument("--multiplayer", action="store_true", help="activate multiplayer")
parser.add_argument("--load", action="store_true", help="load")
parser.add_argument("-S", "--speed", type=int, help="set the speed of the game to a fixed speed")
parser.add_argument("-sc", "--scenario", type=str, help="set the scenario to run")
args = parser.parse_args()

##################################################################################################################################
###
##        switch scenarios
#
##################################################################################################################################

# load the gamestate
loaded = False
if not args.nourwid:
    if args.load:
        shouldLoad = True
    else:
        load = input("load saved game? (Y/n)")
        if load.lower() == "n":
            shouldLoad = False
        else:
            shouldLoad = True
else:
    shouldLoad = True

if not shouldLoad:
    if not args.scenario:
        scenarios = [
                        ("story1","story mode (old+broken)",),
                        ("story2","story mode (new)",),
                        ("siege","siege",),
                        ("survival","survival",),
                        ("creative","creative mode",),
                        ("dungeon","dungeon",),
                    ]

        text = "\n"
        counter = 0
        for scenario in scenarios:
            text += "%s: %s\n"%(counter,scenario[1],)
            counter += 1

        scenarioNum = input("select scenario (type number)\n\n%s\n\n"%(text,))
        scenario = scenarios[int(scenarioNum)][0]
    else:
        scenario = args.scenario

    if scenario == "siege":
        args.terrain = "test"
        args.phase = "BuildBase"
    elif scenario == "survival":
        args.terrain = "desert"
        args.phase = "DesertSurvival"
    elif scenario == "creative":
        args.terrain = "nothingness"
        args.phase = "CreativeMode"
    elif scenario == "dungeon":
        args.terrain = "nothingness"
        args.phase = "Dungeon"

# set rendering mode
if not args.nourwid:
    if args.unicode:
        displayChars = canvas.DisplayMapping("unicode")
    else:
        displayChars = canvas.DisplayMapping("pureASCII")
else:
    displayChars = canvas.TileMapping("testTiles")

# bad code: common variables with modules
canvas.displayChars = displayChars

if args.speed:
    interaction.speed = args.speed

if args.seed:
    seed = int(args.seed)
else:
    import random
    seed = random.randint(1,100000)

# bad code: common variables with modules
if args.nourwid:
    interaction.nourwid = True

    import src.pseudoUrwid
    interaction.urwid = src.pseudoUrwid
    items.urwid = src.pseudoUrwid
    chats.urwid = src.pseudoUrwid
    canvas.urwid = src.pseudoUrwid
    cinematics.urwid = src.pseudoUrwid

    interaction.setUpNoUrwid()

else:
    interaction.nourwid = False

    import urwid
    interaction.urwid = urwid
    items.urwid = urwid
    chats.urwid = urwid
    canvas.urwid = urwid
    cinematics.urwid = urwid

    interaction.setUpUrwid()

# bad code: common variables with modules
phasesByName = {}
gamestate.phasesByName = phasesByName
story.phasesByName = phasesByName
story.registerPhases()

# create and load the gamestate
gamestate.setup()

terrain = None
gamestate.terrain = terrain

# set up debugging
if args.debug:
    '''
    logger object for logging to file
    '''
    class debugToFile(object):
        '''
        clear file
        '''
        def __init__(self):
            logfile = open("debug.log","w")
            logfile.close()
        '''
        add log message to file
        '''
        def append(self,message):
            logfile = open("debug.log","a")
            logfile.write(str(message)+"\n")
            logfile.close()
    
    # set debug mode
    debugMessages = debugToFile()
    interaction.debug = True
    characters.debug = True
    quests.debug = True
    canvas.debug = True
    gameMath.debug = True

# set dummies to replace dummy objects
else:
    '''
    dummy logger
    '''
    class FakeLogger(object):
        '''
        discard input
        '''
        def append(self,message):
            pass

    # set debug mode
    debugMessages = FakeLogger()
    interaction.debug = False
    characters.debug = False
    quests.debug = False
    canvas.debug = False
    gameMath.debug = False

# bad code: common variables with modules
logger.debugMessages = debugMessages

if shouldLoad:
    try:
        # load the game
        loaded = gamestate.gamestate.load()
        seed = gamestate.gamestate.initialSeed
    except Exception as e:
        ignore = input("error in gamestate, could not load gamestate completely. Abort and show error message? (Y/n)")
        if not ignore.lower() == "n":
            raise e
mainChar = gamestate.gamestate.mainChar

##################################################################################################################################
###
##        some stuff that is somehow needed but slated for removal
#
#################################################################################################################################

interaction.setFooter()

##########################################
###
## set up the terrain
#
##########################################

if not loaded:
    # spawn selected terrain
    if args.terrain and args.terrain == "scrapField":
        gamestate.gamestate.terrainType = terrains.ScrapField
    elif args.terrain and args.terrain == "nothingness":
        gamestate.gamestate.terrainType = terrains.Nothingness
    elif args.terrain and args.terrain == "test":
        gamestate.gamestate.terrainType = terrains.GameplayTest
    elif args.terrain and args.terrain == "tutorial":
        gamestate.gamestate.terrainType = terrains.TutorialTerrain
    elif args.terrain and args.terrain == "desert":
        gamestate.gamestate.terrainType = terrains.Desert
    else:
        gamestate.gamestate.terrainType = terrains.GameplayTest
else:
    terrain = gamestate.gamestate.terrain
    interaction.lastTerrain = terrain

# state that should be contained in the gamestate
mapHidden = True
mainChar = None

if not loaded:
    gamestate.gamestate.setup(phase=args.phase, seed=seed)
    terrain = gamestate.gamestate.terrain
    interaction.lastTerrain = terrain

# bad code: common variables with modules
story.terrain = terrain

items.terrain = terrain
interaction.terrain = terrain
terrains.terrain = terrain
gamestate.terrain = terrain
quests.terrain = terrain
chats.terrain = terrain
characters.terrain = terrain

##################################################################################################################################
###
##        the main loop
#
#################################################################################################################################

# the game loop
# bad code: either unused or should be contained in terrain
'''
advance the game
'''
def advanceGame():
    for row in gamestate.gamestate.terrainMap:
        for specificTerrain in row:
            for character in specificTerrain.characters:
                character.advance()

            for room in specificTerrain.rooms:
                room.advance()

            while specificTerrain.events and specificTerrain.events[0].tick <= gamestate.gamestate.tick:
                event = specificTerrain.events[0]
                if event.tick < gamestate.gamestate.tick:
                    continue
                event.handleEvent()
                specificTerrain.events.remove(event)

    gamestate.gamestate.tick += 1


# bad code: common variables with modules
cinematics.advanceGame = advanceGame
interaction.advanceGame = advanceGame
story.advanceGame = advanceGame

# set up the splash screen
if not args.debug and not interaction.submenue and not loaded:
    text = """

     OOO FFF          AAA N N DD
     O O FF   mice    AAA NNN D D
     OOO F            A A N N DD



     MMM   MMM  EEEEEE  CCCCCC  HH   HH  SSSSSSS
     MMMM MMMM  EE      CC      HH   HH  SS
     MM MMM MM  EEEE    CC      HHHHHHH  SSSSSSS
     MM  M  MM  EEEE    CC      HHHHHHH  SSSSSSS
     MM     MM  EE      CC      HH   HH        S
     MM     MM  EEEEEE  CCCCCC  HH   HH  SSSSSSS


        - a pipedream


    press space to continue

"""
    openingCinematic = cinematics.TextCinematic(text,rusty=True,scrolling=True)
    cinematics.cinematicQueue.insert(0,openingCinematic)
    gamestate.gamestate.openingCinematic = openingCinematic
    gamestate.gamestate.mainChar.macroState["commandKeyQueue"].insert(0,(".",["norecord"]))
    gamestate.gamestate.mainChar.macroState["commandKeyQueue"].insert(0,(".",["norecord"]))
    gamestate.gamestate.mainChar.macroState["commandKeyQueue"].insert(0,(".",["norecord"]))
    gamestate.gamestate.mainChar.macroState["commandKeyQueue"].insert(0,(".",["norecord"]))
else:
    gamestate.gamestate.openingCinematic = None

# set up the current phase
if not loaded:
    gamestate.gamestate.currentPhase.start(seed=seed)

# bad code: loading registry should be cleared

# set up tile based mode
if args.tiles:
    # spawn tile based rendered window
    import pygame
    pygame.init()
    pygame.key.set_repeat(200,20)
    if args.tileSize:
        interaction.tileSize = args.tileSize
    else:
        interaction.tileSize = 10
    pydisplay = pygame.display.set_mode((1200, 700),pygame.RESIZABLE)
    pygame.display.set_caption('Of Mice and Mechs')
    pygame.display.update()
    interaction.pygame = pygame
    interaction.pydisplay = pydisplay
    interaction.useTiles = True
    interaction.tileMapping = canvas.TileMapping("testTiles")
else:
    interaction.useTiles = False
    interaction.tileMapping = None

######################################################################################################
###
##    main loop is started here
#
######################################################################################################

if args.multiplayer:
    interaction.multiplayer = True
    interaction.fixedTicks = 0.1
else:
    interaction.multiplayer = False
    interaction.fixesTicks = False

# start the interaction loop of the underlying library
if not args.nourwid:
    input("game ready. press enter to start")
    interaction.loop.run()

if args.nourwid:
    while 1:
        interaction.gameLoop(None,None)

# print death messages
if gamestate.gamestate.mainChar.dead:
    print("you died.")
    if gamestate.gamestate.mainChar.deathReason:
        print("Cause of death:\n"+gamestate.gamestate.mainChar.deathReason)
