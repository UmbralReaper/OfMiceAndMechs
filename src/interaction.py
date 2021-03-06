"""
 ode for interacation with the user belongs here
bad pattern: logic should be moved somewhere else
"""

# load libraries
import time
import uuid

# load internal libraries
import src.rooms
import src.items
import src.quests
import src.canvas
import src.saveing
import src.chats
import src.terrains
import config.commandChars as commandChars
import src.cinematics as cinematics
import src.gamestate

################################################################################
#
#        setting up the basic user interaction library
#         bad code: urwid specific code should be somewhere else
#
################################################################################

continousOperation = 0
main = None
footer = None
header = None
frame = None
urwid = None
fixedTicks = False
speed = None

# the game loop
# bad code: either unused or should be contained in terrain
"""
advance the game
"""


def advanceGame():
    for row in src.gamestate.gamestate.terrainMap:
        for specificTerrain in row:
            for character in specificTerrain.characters:
                character.advance()

            for room in specificTerrain.rooms:
                room.advance()

            while (
                specificTerrain.events
                and specificTerrain.events[0].tick <= src.gamestate.gamestate.tick
            ):
                event = specificTerrain.events[0]
                if event.tick < src.gamestate.gamestate.tick:
                    continue
                event.handleEvent()
                specificTerrain.events.remove(event)

    src.gamestate.gamestate.tick += 1


class abstractedDisplay(object):
    def __init__(self, urwidInstance):
        self.urwidInstance = urwidInstance

    def set_text(self, text):
        if self.urwidInstance:
            self.urwidInstance.set_text(text)
        self.text = text

    def get_text(self):
        return self.text

    def renderSDL2(self):
        pass


def setUpUrwid():
    import urwid

    # the containers for the shown text
    urwidHeader = urwid.Text(u"")
    urwidMain = urwid.Text(u"")
    urwidFooter = urwid.Text(u"", align="right")

    global main
    global footer
    global header
    global frame
    global loop

    main = abstractedDisplay(urwidMain)
    footer = abstractedDisplay(urwidFooter)
    header = abstractedDisplay(urwidHeader)

    urwidMain.set_layout("left", "clip")
    frame = urwid.Frame(
        urwid.Filler(urwidMain, "top"), header=urwidHeader, footer=urwidFooter
    )

    # get the interaction loop from the library
    loop = urwid.MainLoop(frame, unhandled_input=keyboardListener)

    def tmp(loop, user_data):
        gameLoop(loop, user_data)

    loop.set_alarm_in(0.1, tmp)

    loop.set_alarm_in(0.1, tmp2)


def setUpNoUrwid():
    global main
    global footer
    global header

    main = abstractedDisplay(None)
    footer = abstractedDisplay(None)
    header = abstractedDisplay(None)


################################################################################
#
#        the main interaction loop
#
################################################################################

# timestamps for detecting periods in inactivity etc
lastLagDetection = time.time()
lastRedraw = time.time()

# states for stateful interaction
fullAutoMode = False
idleCounter = 0
submenue = None
ticksSinceDeath = None
levelAutomated = 0

# the state for the footer
# bad code: this should be contained in an object
footerInfo = []
footerText = ""
doubleFooterText = footerText + footerText
footerPosition = 0
footerLength = len(footerText)
footerSkipCounter = 20

macros = {}

"""
calculate footer text
"""


def setFooter():
    # bad code: global variables
    global footerInfo
    global footerText
    global doubleFooterText
    global footerPosition
    global footerLength
    global footerSkipCounter

    # calculate the text
    # bad pattern: footer should be dynamically generated
    footerInfo = [
        "@  = you",
        "XX = Wall",
        ":: = floor",
        "[] = door",
        "** = pipe",
        "is = scrap",
        "is = scrap",
        "oo / öö = furnce",
        "OO / 00 = growth tank",
        "|| / // = lever",
        "@a / @b ... @z = npcs",
        "xX = quest marker (your current target)",
        "press " + commandChars.show_help + " for help",
        "press " + commandChars.move_north + " to move north",
        "press " + commandChars.move_south + " to move south",
        "press " + commandChars.show_quests + " for quests",
        "press " + commandChars.show_quests_detailed + " for advanced quests",
        "press " + commandChars.show_inventory + " for inventory",
        "press " + commandChars.move_west + " to move west",
        "press " + commandChars.move_east + " to move east",
        "press " + commandChars.activate + " to activate",
        "press " + commandChars.pickUp + " to pick up",
        "press " + commandChars.hail + " to talk",
        "press " + commandChars.drop + " to drop",
    ]
    footerText = ", ".join(footerInfo) + ", "

    # calculate meta information for footer
    doubleFooterText = footerText + footerText
    doubleFooterText = "- press " + commandChars.show_help + " for an help text -"
    doubleFooterText = doubleFooterText * 20
    footerPosition = 0
    footerLength = len(footerText)
    footerSkipCounter = 20


"""
calls show_or_exit with on param less
bad code: keystrokes should not be injected in the first place
"""


def callShow_or_exit(loop, key):
    show_or_exit(key)


"""
the callback for urwid keystrokes
bad code: this is abused as the main loop for this game
"""


def show_or_exit(key, charState=None):
    if charState is None:
        charState = src.gamestate.gamestate.mainChar.macroState

    # store the commands for later processing
    charState["commandKeyQueue"].append((key, []))


"""
the abstracted processing for keystrokes.
Takes a list of keystrokes, that have been converted to a common format
"""


def processAllInput(commandKeyQueue):
    for key in commandKeyQueue:
        processInput(key)


shownStarvationWarning = False

"""
handle a keystroke
bad code: there are way too much lines of code in this function
"""


def processInput(key, charState=None, noAdvanceGame=False, char=None):
    if char.dead:
        return

    char.timeTaken += 1

    if charState is None:
        charState = src.gamestate.gamestate.mainChar.macroState

    if char is None:
        char = src.gamestate.gamestate.mainChar

    if char.room:
        terrain = char.room.terrain
    else:
        terrain = char.terrain

    if terrain is None:
        if char.lastRoom:
            terrain = char.lastRoom.terrain
        else:
            terrain = char.lastTerrain

    flags = key[1]
    key = key[0]

    # ignore mouse interaction
    # bad pattern: mouse input should be used
    if type(key) == tuple:
        return

    char.specialRender = False

    if char.staggered:
        char.staggered -= 1
        char.addMessage("you are still staggered")
        return

    if charState["recording"]:
        if (
            key not in ("lagdetection", "lagdetection_", "-")
            or char.interactionState["varActions"]
        ):
            if (
                charState["recordingTo"] is None
                or charState["recordingTo"][-1].isupper()
                or charState["recordingTo"][-1] == " "
            ):
                if charState["recordingTo"] is None:
                    charState["recordingTo"] = key
                else:
                    charState["recordingTo"] += key

                if not (key.isupper() or key == " "):
                    charState["macros"][charState["recordingTo"]] = []
                    char.addMessage(
                        "start recording to: %s" % (charState["recordingTo"])
                    )
                else:
                    if (
                        src.gamestate.gamestate.mainChar == char
                        and "norecord" not in flags
                    ):
                        text = """

type the macro name you want to record to

%s

""" % (
                            charState["recordingTo"]
                        )

                        for key, value in charState["macros"].items():

                            if not key.startswith(charState["recordingTo"]):
                                continue

                            compressedMacro = ""
                            for keystroke in value:
                                if len(keystroke) == 1:
                                    compressedMacro += keystroke
                                else:
                                    compressedMacro += "/" + keystroke + "/"

                            text += """
%s - %s""" % (
                                key,
                                compressedMacro,
                            )

                        header.set_text(
                            (urwid.AttrSpec("default", "default"), "record macro")
                        )
                        main.set_text((urwid.AttrSpec("default", "default"), text))
                        footer.set_text((urwid.AttrSpec("default", "default"), ""))
                        char.specialRender = True

                return
            else:
                if "norecord" not in flags:
                    charState["macros"][charState["recordingTo"]].append(key)

    if (
        charState["submenue"]
        and charState["submenue"].type == "InputMenu"
        and (key not in ("|", ">", "<") and not charState["submenue"].escape)
    ):

        # let the submenu handle the keystroke
        lastSubmenu = charState["submenue"]
        noRender = True
        if src.gamestate.gamestate.mainChar == char and "norecord" not in flags:
            noRender = False
        done = charState["submenue"].handleKey(key, noRender=noRender)

        if not lastSubmenu == charState["submenue"]:
            charState["submenue"].handleKey("~", noRender=noRender)
            done = False

        # reset rendering flags
        if done:
            charState["submenue"] = None
            char.specialRender = False
            doAdvanceGame = False
        key = commandChars.ignore

    if key in ("|",):
        char.interactionState["stateChange"] = True
        return

    if "stateChange" in char.interactionState and char.interactionState["stateChange"]:
        if key in (">",):
            # do stateSave
            char.interactionState["replay"] = charState["replay"]
            char.interactionState["submenue"] = charState["submenue"]
            char.interactionState["number"] = charState["number"]
            char.interactionState["itemMarkedLast"] = charState["itemMarkedLast"]
            char.interactionState["macrostate"] = charState
            char.interactionStateBackup.append(char.interactionState)
            char.interactionState = {}
            charState["replay"] = []
            charState["submenue"] = None
            charState["number"] = None
            charState["itemMarkedLast"] = None
        elif key in ("<",):
            if len(char.interactionStateBackup):
                char.interactionState = char.interactionStateBackup.pop()
                charState["replay"] = char.interactionState["replay"]
                charState["submenue"] = char.interactionState["submenue"]
                charState["number"] = char.interactionState["number"]
                charState["itemMarkedLast"] = char.interactionState["itemMarkedLast"]
            else:
                char.addMessage("nothing to restore")
            del char.interactionState["stateChange"]
        return

    if char.doStackPop:
        if key in char.registers:
            char.registers[key].pop()
            if not len(char.registers[key]):
                del char.registers[key]
        char.doStackPop = False
        return
    if char.doStackPush:
        if key not in char.registers:
            char.registers[key] = []
        char.registers[key].append(0)
        char.doStackPush = False
        return

    if "advancedInteraction" in char.interactionState:
        if not char.container:
            del char.interactionState["advancedInteraction"]
            return
        if key == "w":
            items = char.container.getItemByPosition(
                (char.xPosition, char.yPosition - 1, char.zPosition)
            )
            if items:
                items[0].apply(char)
        elif key == "s":
            items = char.container.getItemByPosition(
                (char.xPosition, char.yPosition + 1, char.zPosition)
            )
            if items:
                items[0].apply(char)
        elif key == "d":
            items = char.container.getItemByPosition(
                (char.xPosition + 1, char.yPosition, char.zPosition)
            )
            if items:
                items[0].apply(char)
        elif key == "a":
            items = char.container.getItemByPosition(
                (char.xPosition - 1, char.yPosition, char.zPosition)
            )
            if items:
                items[0].apply(char)
        elif key == ".":
            items = char.container.getItemByPosition(
                (char.xPosition, char.yPosition, char.zPosition)
            )
            if items:
                items[0].apply(char)
        elif key == "j":
            character = char
            while character.jobOrders and not character.jobOrders[-1].getTask():
                character.jobOrders.pop()

            if character.jobOrders:
                character.jobOrders[-1].apply(character)
            else:
                for item in reversed(character.inventory):
                    if isinstance(item, src.items.itemMap["JobOrder"]):
                        item.apply(char)
                        char.addMessage("ran job Order")
                        break
        elif key == "f":
            character = char
            for item in character.inventory:
                if isinstance(item, src.items.GooFlask):
                    if item.uses > 0:
                        item.apply(character)
                        break
                if (
                    isinstance(item, src.items.Bloom)
                    or isinstance(item, src.items.BioMass)
                    or isinstance(item, src.items.PressCake)
                    or isinstance(item, src.items.SickBloom)
                ):
                    item.apply(character)
                    character.inventory.remove(item)
                    break
                if isinstance(item, src.items.Corpse):
                    item.apply(character)
                    break
        del char.interactionState["advancedInteraction"]
        return

    if "advancedPickup" in char.interactionState:
        if len(char.inventory) >= 10:
            char.addMessage("you cannot carry more items")
        elif not char.container:
            pass
        else:
            if key == "w":
                items = char.container.getItemByPosition(
                    (char.xPosition, char.yPosition - 1, char.zPosition)
                )
                if items:
                    item = items[0]
                    item.pickUp(char)
            elif key == "s":
                items = char.container.getItemByPosition(
                    (char.xPosition, char.yPosition + 1, char.zPosition)
                )
                if items:
                    item = items[0]
                    item.pickUp(char)
            elif key == "d":
                items = char.container.getItemByPosition(
                    (char.xPosition + 1, char.yPosition, char.zPosition)
                )
                if items:
                    item = items[0]
                    item.pickUp(char)
            elif key == "a":
                items = char.container.getItemByPosition(
                    (char.xPosition - 1, char.yPosition, char.zPosition)
                )
                if items:
                    item = items[0]
                    item.pickUp(char)
            elif key == ".":
                items = char.container.getItemByPosition(
                    (char.xPosition, char.yPosition, char.zPosition)
                )
                if items:
                    item = items[0]
                    item.pickUp(char)
        del char.interactionState["advancedPickup"]
        return

    if "functionCall" in char.interactionState:
        if key not in (" ", "backspace", "enter"):
            char.interactionState["functionCall"] += key

            if src.gamestate.gamestate.mainChar == char and "norecord" not in flags:
                header.set_text((urwid.AttrSpec("default", "default"), "call function"))
                main.set_text(
                    (
                        urwid.AttrSpec("default", "default"),
                        """

call function %s
"""
                        % (char.interactionState["functionCall"]),
                    )
                )
                footer.set_text((urwid.AttrSpec("default", "default"), ""))
                char.specialRender = True
        else:
            char.addMessage(char.interactionState["functionCall"])
            if char.interactionState["functionCall"] == "clear":
                char.registers = {}
            if char.interactionState["functionCall"] == "clear registers":
                char.registers = {}
            if char.interactionState["functionCall"] == "clearJobOrders":
                char.jobOrders = []
            del char.interactionState["functionCall"]
        char.timeTaken -= 0.99
        return

    if "advancedDrop" in char.interactionState:
        if key == "w":
            if char.inventory:
                char.drop(
                    char.inventory[-1],
                    (char.xPosition, char.yPosition - 1, char.zPosition),
                )
        elif key == "s":
            if char.inventory:
                char.drop(
                    char.inventory[-1],
                    (char.xPosition, char.yPosition + 1, char.zPosition),
                )
        elif key == "d":
            if char.inventory:
                char.drop(
                    char.inventory[-1],
                    (char.xPosition + 1, char.yPosition, char.zPosition),
                )
        elif key == "a":
            if char.inventory:
                char.drop(
                    char.inventory[-1],
                    (char.xPosition - 1, char.yPosition, char.zPosition),
                )
        elif key == ".":
            if char.inventory:
                char.drop(
                    char.inventory[-1], (char.xPosition, char.yPosition, char.zPosition)
                )
        del char.interactionState["advancedDrop"]
        return

    if "enumerateState" not in char.interactionState:
        char.interactionState["enumerateState"] = []

    if char.interactionState["enumerateState"]:

        if char.interactionState["enumerateState"][-1]["type"] is None:
            char.interactionState["enumerateState"][-1]["type"] = key
            if src.gamestate.gamestate.mainChar == char and "norecord" not in flags:
                header.set_text((urwid.AttrSpec("default", "default"), "observe"))
                main.set_text(
                    (
                        urwid.AttrSpec("default", "default"),
                        """

get position for what thing

* d - drill
* s - scrap
* f - food
* c - character
* m - marker bean
* C - coal
* M - corpse
* e - enemy
* x - tilecenter
* k - command
* n - machinery
* j - jobOrder
* J - jobBoard
* t - transport in
* T - transport out
* R - room tile

""",
                    )
                )
                footer.set_text((urwid.AttrSpec("default", "default"), ""))
                char.specialRender = True
            char.timeTaken -= 0.99
            return

        if char.interactionState["enumerateState"][-1]["type"] == "p":
            char.addMessage("type:" + key)

            if key == "d":
                char.interactionState["enumerateState"][-1]["target"] = ["Drill"]
            elif key == "s":
                char.interactionState["enumerateState"][-1]["target"] = ["Scrap"]
            elif key == "f":
                char.interactionState["enumerateState"][-1]["target"] = [
                    "Corpse",
                    "GooFlask",
                    "Bloom",
                    "SickBloom",
                    "BioMass",
                    "PressCake",
                ]
            elif key == "c":
                char.interactionState["enumerateState"][-1]["target"] = ["character"]
            elif key == "m":
                char.interactionState["enumerateState"][-1]["target"] = ["MarkerBean"]
            elif key == "C":
                char.interactionState["enumerateState"][-1]["target"] = ["Coal"]
            elif key == "k":
                char.interactionState["enumerateState"][-1]["target"] = ["Command"]
            elif key == "M":
                char.interactionState["enumerateState"][-1]["target"] = ["Corpse"]
            elif key == "n":
                char.interactionState["enumerateState"][-1]["target"] = [
                    "Machine",
                    "ScrapCompactor",
                ]
            elif key == "e":
                char.interactionState["enumerateState"][-1]["target"] = ["enemy"]
            elif key == "r":
                char.interactionState["enumerateState"][-1]["target"] = ["roomEntry"]
            elif key == "R":
                char.interactionState["enumerateState"][-1]["target"] = ["roomTile"]
            elif key == "x":
                if "d" not in char.registers:
                    char.registers["d"] = [0]
                if "s" not in char.registers:
                    char.registers["s"] = [0]
                if "a" not in char.registers:
                    char.registers["a"] = [0]
                if "w" not in char.registers:
                    char.registers["w"] = [0]
                if char.xPosition:
                    char.registers["d"][-1] = 7 - char.xPosition % 15
                    char.registers["s"][-1] = 7 - char.yPosition % 15
                char.registers["a"][-1] = -char.registers["d"][-1]
                char.registers["w"][-1] = -char.registers["s"][-1]
                char.addMessage(
                    "found in direction %sa %ss %sd %sw"
                    % (
                        char.registers["a"][-1],
                        char.registers["s"][-1],
                        char.registers["d"][-1],
                        char.registers["w"][-1],
                    )
                )
                char.interactionState["enumerateState"].pop()
                char.timeTaken -= 0.99
                return
            elif key == "j":
                char.interactionState["enumerateState"][-1]["target"] = ["JobOrder"]
            elif key == "s":
                char.interactionState["enumerateState"][-1]["target"] = ["JobBoard"]
            elif key == "t":
                char.interactionState["enumerateState"][-1]["target"] = [
                    "TransportInNode"
                ]
            elif key == "T":
                char.interactionState["enumerateState"][-1]["target"] = [
                    "TransportOutNode"
                ]
            else:
                char.addMessage("not a valid target")
                char.interactionState["enumerateState"].pop()
                char.timeTaken -= 0.99
                return

            if "a" not in char.registers:
                char.registers["a"] = [0]
            char.registers["a"][-1] = 0
            if "w" not in char.registers:
                char.registers["w"] = [0]
            char.registers["w"][-1] = 0
            if "s" not in char.registers:
                char.registers["s"] = [0]
            char.registers["s"][-1] = 0
            if "d" not in char.registers:
                char.registers["d"] = [0]
            char.registers["d"][-1] = 0

            if not char.container:
                char.addMessage("character is nowhere")
                char.interactionState["enumerateState"].pop()
                char.timeTaken -= 0.99
                return

            foundItems = []
            foundItemQuery = False
            for query in char.interactionState["enumerateState"][-1]["target"]:
                if query not in ("character", "enemy", "roomEntry", "roomTile"):
                    foundItemQuery = True
                    break
            if foundItemQuery:
                listFound = []
                if char.room:
                    itemDict = char.container.itemByCoordinates
                else:
                    itemDict = char.container.itemsByCoordinate
                for (pos, value) in itemDict.items():  # <= horrible slow
                    if (
                        pos[0] - (char.xPosition - char.xPosition % 15) > 13
                        or pos[0] - (char.xPosition - char.xPosition % 15) < 1
                    ):
                        continue
                    if (
                        pos[1] - (char.yPosition - char.yPosition % 15) > 13
                        or pos[1] - (char.yPosition - char.yPosition % 15) < 1
                    ):
                        continue
                    if value:
                        listFound.append(value[-1])

                for item in listFound:
                    if (
                        item.type not in char.interactionState["enumerateState"][-1]["target"]
                    ):
                        continue
                    foundItems.append(item)

            if "roomTile" in char.interactionState["enumerateState"][-1]["target"]:
                if char.terrain:
                    for room in char.terrain.rooms:
                        foundItems.append(room)

            if "character" in char.interactionState["enumerateState"][-1]["target"]:
                for otherChar in char.container.characters:
                    if otherChar == char:
                        continue
                    if not (
                        otherChar.xPosition
                        and otherChar.yPosition
                        and char.xPosition
                        and char.yPosition
                    ):
                        continue
                    if (
                        otherChar.xPosition - (char.xPosition - char.xPosition % 15)
                        > 13
                        or otherChar.xPosition - (char.xPosition - char.xPosition % 15)
                        < 1
                    ):
                        continue
                    if (
                        otherChar.yPosition - (char.yPosition - char.yPosition % 15)
                        > 13
                        or otherChar.yPosition - (char.yPosition - char.yPosition % 15)
                        < 1
                    ):
                        continue
                    foundItems.append(otherChar)

            if "enemy" in char.interactionState["enumerateState"][-1]["target"]:
                for otherChar in char.container.characters:
                    if otherChar == char:
                        continue
                    if not (
                        otherChar.xPosition
                        and otherChar.yPosition
                        and char.xPosition
                        and char.yPosition
                    ):
                        continue
                    if otherChar.faction == char.faction:
                        continue
                    if (
                        otherChar.xPosition - (char.xPosition - char.xPosition % 15)
                        > 13
                        or otherChar.xPosition - (char.xPosition - char.xPosition % 15)
                        < 1
                    ):
                        continue
                    if (
                        otherChar.yPosition - (char.yPosition - char.yPosition % 15)
                        > 13
                        or otherChar.yPosition - (char.yPosition - char.yPosition % 15)
                        < 1
                    ):
                        continue
                    foundItems.append(otherChar)

            found = None
            if len(foundItems):
                found = foundItems[src.gamestate.gamestate.tick % len(foundItems)]

            if not found:
                char.addMessage(
                    "no "
                    + ",".join(char.interactionState["enumerateState"][-1]["target"])
                    + " found"
                )
                char.interactionState["enumerateState"].pop()
                char.timeTaken -= 0.99
                return

            if isinstance(found, src.rooms.Room):
                char.registers["d"][-1] = found.xPosition - char.xPosition // 15
                char.registers["s"][-1] = found.yPosition - char.yPosition // 15
                char.registers["a"][-1] = -char.registers["d"][-1]
                char.registers["w"][-1] = -char.registers["s"][-1]
            else:
                char.registers["d"][-1] = found.xPosition - char.xPosition
                char.registers["s"][-1] = found.yPosition - char.yPosition
                char.registers["a"][-1] = -char.registers["d"][-1]
                char.registers["w"][-1] = -char.registers["s"][-1]

            char.addMessage(
                ",".join(char.interactionState["enumerateState"][-1]["target"])
                + " found in direction %sa %ss %sd %sw"
                % (
                    char.registers["a"][-1],
                    char.registers["s"][-1],
                    char.registers["d"][-1],
                    char.registers["w"][-1],
                )
            )
            char.interactionState["enumerateState"].pop()
            return

        char.interactionState["enumerateState"].pop()
        char.timeTaken -= 0.99
        return

    if key == "esc":
        charState["replay"] = []

    if "varActions" not in char.interactionState:
        char.interactionState["varActions"] = []

    if key == "$":
        if src.gamestate.gamestate.mainChar == char and "norecord" not in flags:
            text = """

press key for register to modify or press = to load value from a register

current registers:

"""
            for itemKey, value in char.registers.items():
                convertedValues = []
                for item in reversed(value):
                    convertedValues.append(str(item))
                text += """
%s - %s""" % (
                    itemKey,
                    ",".join(convertedValues),
                )

            header.set_text((urwid.AttrSpec("default", "default"), "registers"))
            main.set_text((urwid.AttrSpec("default", "default"), text))
            footer.set_text((urwid.AttrSpec("default", "default"), ""))
            char.specialRender = True

        char.interactionState["varActions"].append({"outOperator": None})
        char.timeTaken -= 0.99
        return

    if char.interactionState["varActions"]:

        lastVarAction = char.interactionState["varActions"][-1]
        if lastVarAction["outOperator"] is None:
            if key in ("esc", "enter"):
                char.interactionState["varActions"].pop()
                return
            elif key == "=":
                lastVarAction["outOperator"] = True
                lastVarAction["register"] = None
            else:
                lastVarAction["outOperator"] = False
                lastVarAction["register"] = ""
                lastVarAction["action"] = None
                lastVarAction["number"] = ""

        register = lastVarAction["register"]

        if lastVarAction["outOperator"] == True:
            if register is None or (
                (register == "" or register[-1].isupper() or register.endswith(" "))
                and (key.isupper() or key == " ")
            ):
                if register is None:
                    lastVarAction["register"] = ""
                else:
                    lastVarAction["register"] += key
                register = lastVarAction["register"]

                if src.gamestate.gamestate.mainChar == char and "norecord" not in flags:
                    text = """

press key for register to load value from

current registers (%s):

""" % (
                        register
                    )
                    for key, value in char.registers.items():
                        if not key.startswith(register):
                            continue
                        convertedValues = []
                        for item in reversed(value):
                            convertedValues.append(str(item))
                        text += """
%s - %s""" % (
                            key,
                            ",".join(convertedValues),
                        )

                    header.set_text(
                        (urwid.AttrSpec("default", "default"), "reading registers")
                    )
                    main.set_text((urwid.AttrSpec("default", "default"), text))
                    footer.set_text((urwid.AttrSpec("default", "default"), ""))
                    char.specialRender = True
                char.timeTaken -= 0.99
                return

            else:
                if register:
                    key = register + key

                def getValue():
                    if key not in char.registers:
                        char.addMessage("no value in register using %s" % (key,))
                        return 0

                    if isinstance(char.registers[key][-1], str):
                        return char.registers[key][-1]

                    if char.registers[key][-1] < 0:
                        # char.addMessage("negative value in register using %s"%(key,))
                        return 0

                    # char.addMessage("found value %s for register using %s"%(char.registers[key][-1],key,))
                    return char.registers[key][-1]

                value = getValue()

                valueCommand = []
                for numChar in str(value):
                    valueCommand.append((numChar, ["norecord"]))

                char.interactionState["varActions"].pop()
                charState["commandKeyQueue"] = (
                    valueCommand + charState["commandKeyQueue"]
                )
                char.timeTaken -= 0.99
                return
        else:
            if register == "" or register[-1].isupper() or register[-1] == " ":
                if key.isupper() or key == " ":
                    lastVarAction["register"] += key
                    register = lastVarAction["register"]

                    if (
                        src.gamestate.gamestate.mainChar == char
                        and "norecord" not in flags
                    ):
                        text = """

press key for register manipulate

current registers (%s):

""" % (
                            register
                        )
                        for key, value in char.registers.items():
                            if not key.startswith(register):
                                continue
                            convertedValues = []
                            for item in reversed(value):
                                convertedValues.append(str(item))
                            text += """
%s - %s""" % (
                                key,
                                ",".join(convertedValues),
                            )

                        header.set_text(
                            (urwid.AttrSpec("default", "default"), "registers")
                        )
                        main.set_text((urwid.AttrSpec("default", "default"), text))
                        footer.set_text((urwid.AttrSpec("default", "default"), ""))
                        char.specialRender = True
                    char.timeTaken -= 0.99
                    return

                else:
                    lastVarAction["register"] += key

                    if (
                        src.gamestate.gamestate.mainChar == char
                        and "norecord" not in flags
                    ):
                        text = """

press key for the action you want to do on the register

* = - assign value to register
* + - add to register
* - - subtract from register
* / - divide register
* * - mulitply register
* % - apply modulo to register

"""
                        header.set_text(
                            (urwid.AttrSpec("default", "default"), "reading registers")
                        )
                        main.set_text((urwid.AttrSpec("default", "default"), text))
                        footer.set_text((urwid.AttrSpec("default", "default"), ""))
                        char.specialRender = True
                    char.timeTaken -= 0.99
                    return
            action = lastVarAction["action"]
            if action is None:
                lastVarAction["action"] = key

                if src.gamestate.gamestate.mainChar == char and "norecord" not in flags:
                    text = """

input value for this operation ($%s%s)

type number or load value from register

""" % (
                        register,
                        action,
                    )
                    header.set_text(
                        (urwid.AttrSpec("default", "default"), "reading registers")
                    )
                    main.set_text((urwid.AttrSpec("default", "default"), text))
                    footer.set_text((urwid.AttrSpec("default", "default"), ""))
                    char.specialRender = True
                char.timeTaken -= 0.99
                return
            if key in "0123456789":
                lastVarAction["number"] += key

                if src.gamestate.gamestate.mainChar == char and "norecord" not in flags:
                    text = """

input value for this operation ($%s%s%s)

type number

press any other key to finish

""" % (
                        register,
                        action,
                        lastVarAction["number"],
                    )
                    header.set_text(
                        (urwid.AttrSpec("default", "default"), "reading registers")
                    )
                    main.set_text((urwid.AttrSpec("default", "default"), text))
                    footer.set_text((urwid.AttrSpec("default", "default"), ""))
                    char.specialRender = True
                char.timeTaken -= 0.99
                return

            if action == "=":
                if register not in char.registers:
                    char.registers[register] = [0]
                char.registers[register][-1] = int(lastVarAction["number"])
            if action == "+":
                char.registers[register][-1] += int(lastVarAction["number"])
            if action == "-":
                char.registers[register][-1] -= int(lastVarAction["number"])
            if action == "/":
                char.registers[register][-1] //= int(lastVarAction["number"])
            if action == "%":
                char.registers[register][-1] %= int(lastVarAction["number"])
            if action == "*":
                char.registers[register][-1] *= int(lastVarAction["number"])

            charState["commandKeyQueue"] = [(key, flags + ["norecord"])] + charState[
                "commandKeyQueue"
            ]
            char.interactionState["varActions"].pop()
            char.timeTaken -= 0.99
            return

    if "ifCondition" not in char.interactionState:
        char.interactionState["ifCondition"] = []
    if "ifParam1" not in char.interactionState:
        char.interactionState["ifParam1"] = []
    if "ifParam2" not in char.interactionState:
        char.interactionState["ifParam2"] = []
    if key in ("%",):
        char.interactionState["ifCondition"].append(None)
        char.interactionState["ifParam1"].append([])
        char.interactionState["ifParam2"].append([])

        if src.gamestate.gamestate.mainChar == char and "norecord" not in flags:
            text = """

press key for the condition you want to check against.

* i = inventory empty
* b = latest move was blocked by item
* I = inventory full
* > = register c is bigger than 0
* < = register c is lower than 0
* = = register c is exactly 0
* f = floor empty
* t = satiation below 300
* e = food source in inventory
* E = enemy nearby
* c = corpse nearby
* F = food nearby

"""

            header.set_text(
                (urwid.AttrSpec("default", "default"), "conditional action")
            )
            main.set_text((urwid.AttrSpec("default", "default"), text))
            footer.set_text((urwid.AttrSpec("default", "default"), ""))
            char.specialRender = True

        return

    if len(char.interactionState["ifCondition"]) and key not in (
        "%",
        "lagdetection",
        "lagdetection_",
    ):
        if char.interactionState["ifCondition"][-1] is None:
            char.interactionState["ifCondition"][-1] = key

            if src.gamestate.gamestate.mainChar == char and "norecord" not in flags:
                text = """

press key for the action to run in case the condition is true or
press _ to run a macro in case the condition is true

"""

                header.set_text(
                    (urwid.AttrSpec("default", "default"), "conditional action")
                )
                main.set_text((urwid.AttrSpec("default", "default"), text))
                footer.set_text((urwid.AttrSpec("default", "default"), ""))
                char.specialRender = True

        elif char.interactionState["ifParam1"][-1] in ([], [("_", ["norecord"])]) or (
            (
                char.interactionState["ifParam1"][-1][-1][0].isupper()
                or char.interactionState["ifParam1"][-1][-1][0] == " "
            )
            and char.interactionState["ifParam1"][-1][0][0] == "_"
        ):
            char.interactionState["ifParam1"][-1].append((key, ["norecord"]))

            if src.gamestate.gamestate.mainChar == char and "norecord" not in flags:
                if (
                    (
                        char.interactionState["ifParam1"][-1][-1][0].isupper()
                        or char.interactionState["ifParam1"][-1][-1][0] == " "
                    )
                    and char.interactionState["ifParam1"][-1][0][0] == "_"
                ) or char.interactionState["ifParam1"][-1][-1][0] == "_":
                    inputString = ""
                    for item in char.interactionState["ifParam1"][-1]:
                        inputString += item[0]
                    inputString = inputString[1:]

                    text = """

type the macro that should be run in case the condition is true

%s

""" % (
                        inputString
                    )

                    for key, value in charState["macros"].items():

                        if not key.startswith(inputString):
                            continue
                        compressedMacro = ""
                        for keystroke in value:
                            if len(keystroke) == 1:
                                compressedMacro += keystroke
                            else:
                                compressedMacro += "/" + keystroke + "/"

                            text += """
%s - %s""" % (
                                key,
                                compressedMacro,
                            )

                else:
                    text = """

press key for the action to run in case the condition is false
press _ to run a macro in case the condition is false

"""

                header.set_text(
                    (urwid.AttrSpec("default", "default"), "conditional action")
                )
                main.set_text((urwid.AttrSpec("default", "default"), text))
                footer.set_text((urwid.AttrSpec("default", "default"), ""))
                char.specialRender = True

        elif char.interactionState["ifParam2"][-1] in ([], [("_", ["norecord"])]) or (
            (
                char.interactionState["ifParam2"][-1][-1][0].isupper()
                or char.interactionState["ifParam2"][-1][-1][0] == " "
            )
            and char.interactionState["ifParam2"][-1][0][0] == "_"
        ):
            char.interactionState["ifParam2"][-1].append((key, ["norecord"]))

            if src.gamestate.gamestate.mainChar == char and "norecord" not in flags:
                inputString = ""
                for item in char.interactionState["ifParam2"][-1]:
                    inputString += item[0]
                inputString = inputString[1:]

                text = """

type the macro that should be run in case the condition is false

%s

""" % (
                    inputString
                )

                for key, value in charState["macros"].items():

                    if not key.startswith(inputString):
                        continue
                    compressedMacro = ""
                    for keystroke in value:
                        if len(keystroke) == 1:
                            compressedMacro += keystroke
                        else:
                            compressedMacro += "/" + keystroke + "/"

                        text += """
%s - %s""" % (
                            key,
                            compressedMacro,
                        )

                header.set_text(
                    (urwid.AttrSpec("default", "default"), "conditional action")
                )
                main.set_text((urwid.AttrSpec("default", "default"), text))
                footer.set_text((urwid.AttrSpec("default", "default"), ""))
                char.specialRender = True

            if not (
                char.interactionState["ifParam2"][-1] in ([], [("_", ["norecord"])])
                or char.interactionState["ifParam2"][-1][-1][0].isupper()
                or char.interactionState["ifParam2"][-1][-1][0] == " "
            ):
                conditionTrue = True

                if char.interactionState["ifCondition"][-1] == "i":
                    if len(char.inventory) == 0:
                        conditionTrue = True
                    else:
                        conditionTrue = False
                if char.interactionState["ifCondition"][-1] == "b":
                    if charState["itemMarkedLast"]:
                        conditionTrue = True
                    else:
                        conditionTrue = False
                if char.interactionState["ifCondition"][-1] == "I":
                    if len(char.inventory) >= 10:
                        conditionTrue = True
                    else:
                        conditionTrue = False
                if char.interactionState["ifCondition"][-1] == ">":
                    if "c" in char.registers and char.registers["c"][-1] > 0:
                        conditionTrue = True
                    else:
                        conditionTrue = False
                if char.interactionState["ifCondition"][-1] == "<":
                    if "c" in char.registers and char.registers["c"][-1] < 0:
                        conditionTrue = True
                    else:
                        conditionTrue = False
                if char.interactionState["ifCondition"][-1] == "=":
                    if (
                        "c" in char.registers
                        and "v" in char.registers
                        and char.registers["c"][-1] == char.registers["v"][-1]
                    ):
                        conditionTrue = True
                    else:
                        conditionTrue = False
                if char.interactionState["ifCondition"][-1] == "f":
                    pos = (char.xPosition, char.yPosition)
                    if (
                        char.container
                        and pos in char.container.itemByCoordinates
                        and len(char.container.itemByCoordinates[pos]) > 0
                    ):
                        conditionTrue = True
                    else:
                        conditionTrue = False
                if char.interactionState["ifCondition"][-1] == "t":
                    if char.satiation < 300:
                        conditionTrue = True
                    else:
                        conditionTrue = False
                if char.interactionState["ifCondition"][-1] == "e":
                    conditionTrue = False
                    for item in char.inventory:
                        if isinstance(item, src.items.GooFlask) and item.uses > 1:
                            conditionTrue = True
                            break
                if char.interactionState["ifCondition"][-1] == "E":
                    conditionTrue = False
                    if char.container:
                        for character in char.container.characters:
                            if (
                                (
                                    not (
                                        character.xPosition // 15
                                        == char.xPosition // 15
                                        and character.yPosition // 15
                                        == char.yPosition // 15
                                    )
                                )
                                or character.xPosition % 15 in [0, 14]
                                or character.yPosition % 15 in [0, 14]
                            ):
                                continue
                            if (
                                abs(character.xPosition - char.xPosition) < 20
                                and abs(character.yPosition - char.yPosition) < 20
                                and not character.faction == char.faction
                            ):
                                conditionTrue = True
                                break
                if char.interactionState["ifCondition"][-1] == "c":
                    conditionTrue = False
                    if char.container:
                        for (item, value) in char.container.itemByCoordinates.items():
                            if (
                                (
                                    not (
                                        item[0] // 15 == char.xPosition // 15
                                        and item[1] // 15 == char.yPosition // 15
                                    )
                                )
                                or item[0] % 15 in [0, 14]
                                or item[1] % 15 in [0, 14]
                            ):
                                continue
                            if not value:
                                continue

                            if value[-1].type == "Corpse":
                                conditionTrue = True
                                break
                if char.interactionState["ifCondition"][-1] == "F":
                    conditionTrue = False
                    if char.container:
                        for (item, value) in char.container.itemByCoordinates.items():
                            if not (
                                item[0] // 15 == char.xPosition // 15
                                and item[1] // 15 == char.yPosition // 15
                            ):
                                continue
                            if not value:
                                continue

                            if value[-1].type in [
                                "Corpse",
                                "GooFlask",
                                "Bloom",
                                "SickBloom",
                                "BioMass",
                                "PressCake",
                            ]:
                                conditionTrue = True
                                break
                if conditionTrue:
                    charState["commandKeyQueue"] = (
                        char.interactionState["ifParam1"][-1]
                        + charState["commandKeyQueue"]
                    )
                else:
                    charState["commandKeyQueue"] = (
                        char.interactionState["ifParam2"][-1]
                        + charState["commandKeyQueue"]
                    )

                char.interactionState["ifCondition"].pop()
                char.interactionState["ifParam1"].pop()
                char.interactionState["ifParam2"].pop()
        return

    if key in "0123456789":
        if charState["number"] is None:
            charState["number"] = ""
        charState["number"] += key
        key = commandChars.ignore
        char.timeTaken -= 0.99
        return

    if key in ("%",):
        charState["loop"].append(2)
        return

    if charState["loop"] and key not in (
        "lagdetection",
        "lagdetection_",
        commandChars.ignore,
        "_",
        "~",
    ):
        if not charState["replay"]:
            commands = [("§", ["norecord"]), (key, ["norecord"])]
            charState["commandKeyQueue"] = commands + charState["commandKeyQueue"]
            charState["loop"].pop()
        else:
            commands = [("§", ["norecord"]), ("_", ["norecord"]), (key, ["norecord"])]
            charState["commandKeyQueue"] = commands + charState["commandKeyQueue"]
            charState["loop"].pop()

    if key in ("-",) and not char.interactionState["varActions"]:
        if not charState["recording"]:
            char.addMessage("press key to record to")
            if src.gamestate.gamestate.mainChar == char and "norecord" not in flags:
                header.set_text((urwid.AttrSpec("default", "default"), "observe"))
                text = """

press key to record to.

current macros:

"""
                for key, value in charState["macros"].items():
                    compressedMacro = ""
                    for keystroke in value:
                        if len(keystroke) == 1:
                            compressedMacro += keystroke
                        else:
                            compressedMacro += "/" + keystroke + "/"

                    text += """
%s - %s""" % (
                        key,
                        compressedMacro,
                    )

                header.set_text((urwid.AttrSpec("default", "default"), "record macro"))
                main.set_text((urwid.AttrSpec("default", "default"), text))
                footer.set_text((urwid.AttrSpec("default", "default"), ""))
                char.specialRender = True

            charState["recording"] = True
            return
        else:
            charState["recording"] = False
            if charState["recordingTo"]:
                if charState["recordingTo"] in charState["macros"]:
                    if charState["macros"][charState["recordingTo"]]:
                        char.addMessage(
                            "recorded: %s to %s"
                            % (
                                "".join(charState["macros"][charState["recordingTo"]]),
                                charState["recordingTo"],
                            )
                        )
                    else:
                        del charState["macros"][charState["recordingTo"]]
                        char.addMessage(
                            "deleted: %s because of empty recording"
                            % (charState["recordingTo"])
                        )
            charState["recordingTo"] = None

    if charState["replay"] and key not in (
        "lagdetection",
        "lagdetection_",
        "~",
    ):
        if charState["replay"] and (
            charState["replay"][-1] == ""
            or charState["replay"][-1][-1].isupper()
            or charState["replay"][-1][-1] == " "
        ):
            if not charState["number"]:

                charState["replay"][-1] += key

                if (
                    charState["replay"][-1][-1].isupper()
                    or charState["replay"][-1][-1] == " "
                ):

                    if "norecord" in flags:
                        return

                    text = """

press key for macro to replay

%s

current macros:

""" % (
                        charState["replay"][-1]
                    )

                    for macroName, value in charState["macros"].items():
                        if not macroName.startswith(charState["replay"][-1]):
                            continue

                        compressedMacro = ""
                        for keystroke in value:
                            if len(keystroke) == 1:
                                compressedMacro += keystroke
                            else:
                                compressedMacro += "/" + keystroke + "/"

                        text += """
%s - %s""" % (
                            macroName,
                            compressedMacro,
                        )

                    header.set_text(
                        (urwid.AttrSpec("default", "default"), "record macro")
                    )
                    main.set_text((urwid.AttrSpec("default", "default"), text))
                    footer.set_text((urwid.AttrSpec("default", "default"), ""))
                    char.specialRender = True
                    return

                if charState["replay"][-1] in charState["macros"]:
                    char.addMessage(
                        "replaying %s: %s"
                        % (
                            charState["replay"][-1],
                            "".join(charState["macros"][charState["replay"][-1]]),
                        )
                    )
                    commands = []
                    for keyPress in charState["macros"][charState["replay"][-1]]:
                        commands.append((keyPress, ["norecord"]))
                    charState["commandKeyQueue"] = (
                        commands + charState["commandKeyQueue"]
                    )
                else:
                    char.addMessage(
                        "no macro recorded to %s" % (charState["replay"][-1])
                    )

                charState["replay"].pop()
            else:
                num = int(charState["number"])
                charState["number"] = None

                charState["doNumber"] = True

                commands = []
                counter = 0
                while counter < num:
                    commands.append(("_", ["norecord"]))
                    commands.append((key, ["norecord"]))
                    counter += 1
                charState["replay"].pop()
                charState["commandKeyQueue"] = commands + charState["commandKeyQueue"]

                charState["doNumber"] = False
                char.timeTaken -= 0.99

        return

    if key in ("_",):

        if src.gamestate.gamestate.mainChar == char and "norecord" not in flags:
            text = """

press key for macro to replay

current macros:

"""
            for key, value in charState["macros"].items():
                compressedMacro = ""
                for keystroke in value:
                    if len(keystroke) == 1:
                        compressedMacro += keystroke
                    else:
                        compressedMacro += "/" + keystroke + "/"

                text += """
%s - %s""" % (
                    key,
                    compressedMacro,
                )

            header.set_text((urwid.AttrSpec("default", "default"), "record macro"))
            main.set_text((urwid.AttrSpec("default", "default"), text))
            footer.set_text((urwid.AttrSpec("default", "default"), ""))
            char.specialRender = True

        charState["replay"].append("")
        return

    if charState["number"] and key not in (
        commandChars.ignore,
        "lagdetection",
        "lagdetection_",
    ):
        num = int(charState["number"])
        charState["number"] = None

        charState["doNumber"] = True

        commands = []
        counter = 0
        while counter < num:
            commands.append((key, ["norecord"]))
            counter += 1
        # processAllInput(commands)
        charState["commandKeyQueue"] = commands + charState["commandKeyQueue"]

        charState["doNumber"] = False
        char.timeTaken -= 0.99
        return

    # save and quit
    if key in (commandChars.quit_normal, commandChars.quit_instant):
        src.gamestate.gamestate.save()
        raise urwid.ExitMainLoop()

    """
    if key in ('S',):
        src.gamestate.gamestate.save()
        return
    """

    if key in ("<",):
        if src.gamestate.gamestate.mainChar == char and "norecord" not in flags:
            text = """

type key for the register to pop.

current registers

"""
            for key, value in char.registers.items():
                convertedValues = []
                for item in reversed(value):
                    convertedValues.append(str(item))
                text += """
%s - %s""" % (
                    key,
                    ",".join(convertedValues),
                )

            header.set_text((urwid.AttrSpec("default", "default"), "popping registers"))
            main.set_text((urwid.AttrSpec("default", "default"), text))
            footer.set_text((urwid.AttrSpec("default", "default"), ""))
            char.specialRender = True

        char.doStackPop = True
        return
    if key in (">",):
        if src.gamestate.gamestate.mainChar == char and "norecord" in flags:
            text = """

type key for the register to push.

current registers

"""
            for key, value in char.registers.items():
                convertedValues = []
                for item in reversed(value):
                    convertedValues.append(str(item))
                text += """
%s - %s""" % (
                    key,
                    ",".join(convertedValues),
                )

            header.set_text((urwid.AttrSpec("default", "default"), "pushing registers"))
            main.set_text((urwid.AttrSpec("default", "default"), text))
            footer.set_text((urwid.AttrSpec("default", "default"), ""))
            char.specialRender = True

        char.doStackPush = True
        return

    # bad code: global variables
    global lastLagDetection
    global idleCounter
    global ticksSinceDeath

    # show the scrolling footer
    # bad code: this should be contained in an object
    if key in ("lagdetection", "lagdetection_"):
        # show the scrolling footer
        if (not charState["submenue"]) and (
            not len(cinematics.cinematicQueue)
            or not cinematics.cinematicQueue[0].overwriteFooter
        ):
            # bad code: global variables
            global footerPosition
            global footerLength
            global footerSkipCounter

            # scroll footer every 20 lagdetection events (about 2 seconds)
            # bad code: using the lagdetection as timer is abuse
            if footerSkipCounter == 20:
                footerSkipCounter = 0
                if not (charState["replay"] or charState["doNumber"]):
                    screensize = loop.screen.get_cols_rows()
                    footer.set_text(
                        doubleFooterText[
                        footerPosition: screensize[0] - 1 + footerPosition
                        ]
                    )
                    if footerPosition == footerLength:
                        footerPosition = 0
                    else:
                        footerPosition += 1
                footerSkipCounter += 1

        # set the cinematic specific footer
        else:
            footerSkipCounter = 20
            if not charState["submenue"]:
                footer.set_text(" " + cinematics.cinematicQueue[0].footerText)
                if (
                    isinstance(
                        cinematics.cinematicQueue[0], src.cinematics.TextCinematic
                    )
                    and cinematics.cinematicQueue[0].firstRun
                ):
                    cinematics.cinematicQueue[0].advance()
            else:
                footer.set_text(" " + charState["submenue"].footerText)

    # discard key strokes, if they were not processed for too long
    ignoreList = (
        commandChars.autoAdvance,
        commandChars.quit_instant,
        commandChars.ignore,
        commandChars.quit_delete,
        commandChars.pause,
        commandChars.show_quests,
        commandChars.show_quests_detailed,
        commandChars.show_inventory,
        commandChars.show_inventory_detailed,
        commandChars.show_characterInfo,
    )
    if key not in ignoreList:
        if lastLagDetection < time.time() - 0.4:
            pass
            # return

    # repeat autoadvance keystrokes
    # bad code: keystrokes are abused here, a timer would be more appropriate
    if key in (commandChars.autoAdvance,):
        if not charState["ignoreNextAutomated"]:
            loop.set_alarm_in(0.2, callShow_or_exit, commandChars.autoAdvance)
        else:
            charState["ignoreNextAutomated"] = False

    # handle a keystroke while on map or in cinematic
    if not charState["submenue"]:
        if key in ("u",):
            char.setInterrupt = True
            return

        if key in ("esc",):
            options = [("save", "save"), ("quit", "save and quit"), ("actions", "actions"),
                       ("macros", "macros"), ("help", "help"), ("keybinding", "keybinding"),
                       ("changeFaction", "changeFaction"),
                       ("change personality settings", "change personality settings")]
            submenu = SelectionMenu("What do you want to do?", options)
            char.macroState["submenue"] = submenu

            def trigger():
                selection = submenu.getSelection()
                if selection == "change personality settings":

                    def getValue():
                        settingName = char.macroState["submenue"].selection

                        def setValue():
                            value = char.macroState["submenue"].text
                            if settingName in (
                                "autoCounterAttack",
                                "autoFlee",
                                "abortMacrosOnAttack",
                                "attacksEnemiesOnContact",
                            ):
                                if value == "True":
                                    value = True
                                else:
                                    value = False
                            else:
                                value = int(value)
                            char.personality[settingName] = value

                        if settingName is None:
                            return
                        submenu3 = InputMenu("input value")
                        char.macroState["submenue"] = submenu3
                        char.macroState["submenue"].followUp = setValue
                        return

                    options = []
                    for (key, value) in char.personality.items():
                        options.append((key, "%s: %s" % (key, value)))
                    submenu2 = SelectionMenu("select personality setting", options)
                    char.macroState["submenue"] = submenu2
                    char.macroState["submenue"].followUp = getValue
                    return
                if selection == "save":
                    tmp = char.macroState["submenue"]
                    char.macroState["submenue"] = None
                    src.gamestate.gamestate.save()
                    char.macroState["submenue"] = tmp
                elif selection == "quit":
                    char.macroState["submenue"] = None
                    src.gamestate.gamestate.save()
                    raise urwid.ExitMainLoop()
                elif selection == "actions":
                    pass
                elif selection == "macros":
                    pass
                elif selection == "changeFaction":
                    if char.faction == "player":
                        char.faction = "monster"
                    else:
                        char.faction = "player"
                    pass
                elif selection == "help":
                    charState["submenue"] = HelpMenu()
                elif selection == "keybinding":
                    pass

            char.macroState["submenue"].followUp = trigger
            key = "."

        if key in ("z",):
            if src.gamestate.gamestate.mainChar == char and "norecord" not in flags:
                header.set_text((urwid.AttrSpec("default", "default"), "observe"))
                main.set_text(
                    (
                        urwid.AttrSpec("default", "default"),
                        """

    select what you want to do

    * c - clear macros

    """,
                    )
                )
                footer.set_text((urwid.AttrSpec("default", "default"), ""))
                char.specialRender = True
            char.interactionState["functionCall"] = ""
            char.timeTaken -= 0.99
            return
        if key in ("o",):
            if src.gamestate.gamestate.mainChar == char and "norecord" not in flags:
                header.set_text((urwid.AttrSpec("default", "default"), "observe"))
                main.set_text(
                    (
                        urwid.AttrSpec("default", "default"),
                        """

    select what you want to observe

    * p - get position of something

    """,
                    )
                )
                footer.set_text((urwid.AttrSpec("default", "default"), ""))
                char.specialRender = True
            char.interactionState["enumerateState"].append({"type": None})
            char.timeTaken -= 0.99
            return

        # handle cinematics
        if len(cinematics.cinematicQueue):
            if src.gamestate.gamestate.mainChar == char and "norecord" not in flags:
                char.specialRender = True

            # get current cinematic
            cinematic = cinematics.cinematicQueue[0]

            # allow to quit even within a cutscene
            if key in (commandChars.quit_normal, commandChars.quit_instant):
                src.gamestate.gamestate.save()
                # bad code: directly calls urwid
                raise urwid.ExitMainLoop()

            # skip the cinematic if requested
            elif (
                key
                in (
                    commandChars.pause,
                    commandChars.advance,
                    commandChars.autoAdvance,
                    commandChars.redraw,
                    "enter",
                )
                and cinematic.skipable
            ):
                cinematic.abort()
                cinematics.cinematicQueue = cinematics.cinematicQueue[1:]
                if loop:
                    loop.set_alarm_in(0.0, callShow_or_exit, commandChars.ignore)
                else:
                    callShow_or_exit(None, commandChars.ignore)
                return

            # advance the cutscene
            else:
                if not cinematic.advance():
                    return
                if not cinematic.background:
                    # bad code: changing the key mid function
                    key = commandChars.ignore

        # set the flag to advance the game
        doAdvanceGame = True
        if key in (commandChars.ignore,):
            doAdvanceGame = False

        # invalidate input for unconscious char
        if char.unconcious:
            key = commandChars.wait

        # show a few rounds after death and exit
        if char.dead:
            if not ticksSinceDeath:
                ticksSinceDeath = src.gamestate.gamestate.tick
            key = commandChars.wait
            if src.gamestate.gamestate.tick == ticksSinceDeath + 5:
                char.macroState["commandKeyQueue"] = []
                char.macroState["submenue"] = TextMenu(
                    "You died. press ctrl-c and reload to start from last save"
                )
                # destroy the gamestate
                # bad pattern: should not always destroy gamestate
                # saveFile = open("gamestate/gamestate.json","w")
                # saveFile.write("you lost")
                # saveFile.close()
                # raise urwid.ExitMainLoop()
                pass

        # call callback if key was overwritten
        if "stealKey" in charState and key in charState["stealKey"]:
            charState["stealKey"][key]()

        # handle the keystroke for a char on the map
        else:
            # open the debug menue
            if key in ("´",):
                if debug:
                    charState["submenue"] = DebugMenu()
                else:
                    char.addMessage("debug not enabled")

            # destroy save and quit
            if key in (commandChars.quit_delete,):
                saveFile = open("gamestate/gamestate.json", "w")
                saveFile.write("reset")
                saveFile.close()
                raise urwid.ExitMainLoop()

            # kill one of the autoadvance keystrokes
            # bad pattern: doesn't actually pause
            if key in (commandChars.pause,):
                charState["ignoreNextAutomated"] = True
                doAdvanceGame = False

            """
            move the player into a direction
            bad code: huge inline function + player vs. npc movement should use same code
            """

            def moveCharacter(direction):

                # do inner room movement
                if char.room:
                    item = char.room.moveCharacterDirection(char, direction)

                    # remember items bumped into for possible interaction
                    if item:
                        char.addMessage("You cannot walk there " + str(direction))
                        char.addMessage("press " + commandChars.activate + " to apply")
                        if not noAdvanceGame:
                            header.set_text(
                                (
                                    urwid.AttrSpec("default", "default"),
                                    renderHeader(char),
                                )
                            )
                        return item
                    else:
                        char.changed("moved", direction)

                # do movement on terrain
                # bad code: these calculation should be done elsewhere
                else:
                    if not char.terrain:
                        return

                    return char.terrain.moveCharacterDirection(char, direction)

            # move the player
            if key in (commandChars.move_north, "up"):
                charState["itemMarkedLast"] = moveCharacter("north")
                if charState["itemMarkedLast"]:
                    return
            if key in (commandChars.move_south, "down"):
                charState["itemMarkedLast"] = moveCharacter("south")
                if charState["itemMarkedLast"]:
                    return
            if key in (commandChars.move_east, "right"):
                charState["itemMarkedLast"] = moveCharacter("east")
                if charState["itemMarkedLast"]:
                    return
            if key in (commandChars.move_west, "left"):
                charState["itemMarkedLast"] = moveCharacter("west")
                if charState["itemMarkedLast"]:
                    return

            # move the player
            if key in (
                "W",
                "S",
                "D",
                "A",
            ):

                lastXposition = char.xPosition
                lastYposition = char.yPosition
                if key in ("W",):
                    charState["itemMarkedLast"] = moveCharacter("north")
                if key in ("S",):
                    charState["itemMarkedLast"] = moveCharacter("south")
                if key in ("D",):
                    charState["itemMarkedLast"] = moveCharacter("east")
                if key in ("A",):
                    charState["itemMarkedLast"] = moveCharacter("west")

                if (
                    not lastXposition == char.xPosition
                    or not lastYposition == char.yPosition
                ):
                    charState["commandKeyQueue"].insert(0, (key, ("norecord",)))

                if charState["itemMarkedLast"]:
                    return

            # murder the next available character
            # bad pattern: player should be able to select whom to kill if there are multiple targets
            if key in ("M",):
                if char.combatMode is None:
                    char.combatMode = "agressive"
                elif char.combatMode == "agressive":
                    char.combatMode = "defensive"
                else:
                    char.combatMode = None
                char.addMessage("switched combatMode to: %s" % (char.combatMode,))
            if key in (commandChars.attack,):
                if (
                    "NaiveMurderQuest" not in char.solvers and not char.godMode
                ):  # disabled
                    char.addMessage("you do not have the nessecary solver yet (murder)")
                else:
                    # bad code: should be part of a position object
                    adjascentFields = [
                        (char.xPosition, char.yPosition),
                        (char.xPosition - 1, char.yPosition),
                        (char.xPosition + 1, char.yPosition),
                        (char.xPosition, char.yPosition - 1),
                        (char.xPosition, char.yPosition + 1),
                    ]
                    for enemy in char.container.characters:
                        if enemy == char:
                            continue
                        if (
                            not char.combatMode == "agressive"
                            and enemy.faction == char.faction
                        ):
                            continue
                        if (enemy.xPosition, enemy.yPosition) not in adjascentFields:
                            continue
                        if isinstance(char, src.characters.Monster) and char.phase == 4:
                            char.addMessage("entered stage 5")
                            char.enterPhase5()
                        char.attack(enemy)
                        break

            # activate an item
            if key in ("c",):
                if "NaiveActivateQuest" not in char.solvers and not char.godMode:
                    char.addMessage(
                        "you do not have the nessecary solver yet (activate)"
                    )
                else:
                    # activate the marked item
                    if charState["itemMarkedLast"]:
                        if not charState["itemMarkedLast"].container:
                            if charState["itemMarkedLast"].room:
                                charState["itemMarkedLast"].container = charState[
                                    "itemMarkedLast"
                                ].room
                            elif charState["itemMarkedLast"].terrain:
                                charState["itemMarkedLast"].container = charState[
                                    "itemMarkedLast"
                                ].terrain

                        charState["itemMarkedLast"].configure(char)

                    # activate an item on floor
                    else:
                        # for item in char.container.itemsOnFloor:
                        #    if item.xPosition == char.xPosition and item.yPosition == char.yPosition:
                        #        item.apply(char)
                        #        break
                        entry = char.container.getItemByPosition(
                            (char.xPosition, char.yPosition, char.zPosition)
                        )
                        if len(entry):
                            entry[0].configure(char)

            # activate an item
            if key in (commandChars.activate,):
                if "NaiveActivateQuest" not in char.solvers and not char.godMode:
                    char.addMessage(
                        "you do not have the nessecary solver yet (activate)"
                    )
                else:
                    # activate the marked item
                    if charState["itemMarkedLast"]:
                        if not charState["itemMarkedLast"].container:
                            if charState["itemMarkedLast"].room:
                                charState["itemMarkedLast"].container = charState[
                                    "itemMarkedLast"
                                ].room
                            elif charState["itemMarkedLast"].terrain:
                                charState["itemMarkedLast"].container = charState[
                                    "itemMarkedLast"
                                ].terrain

                        charState["itemMarkedLast"].apply(char)

                    # activate an item on floor
                    else:
                        # for item in char.container.itemsOnFloor:
                        #    if item.xPosition == char.xPosition and item.yPosition == char.yPosition:
                        #        item.apply(char)
                        #        break
                        if not (
                            char.xPosition is None
                            or char.yPosition is None
                            or char.zPosition is None
                        ):
                            entry = char.container.getItemByPosition(
                                (char.xPosition, char.yPosition, char.zPosition)
                            )

                            if entry:
                                entry[0].apply(char)

            # examine an item
            if key in (commandChars.examine,):
                if "ExamineQuest" not in char.solvers and not char.godMode:
                    char.addMessage(
                        "you do not have the nessecary solver yet (examine)"
                    )
                else:
                    # examine the marked item
                    if charState["itemMarkedLast"]:
                        char.examine(charState["itemMarkedLast"])

                    # examine an item on floor
                    else:
                        itemList = char.container.getItemByPosition(
                            (char.xPosition, char.yPosition, char.zPosition)
                        )
                        for item in itemList:
                            char.examine(item)
                            break

            # drop first item from inventory
            # bad pattern: the user has to have the choice for what item to drop
            if key in (commandChars.drop,):
                if "NaiveDropQuest" not in char.solvers and not char.godMode:
                    char.addMessage("you do not have the nessecary solver yet (drop)")
                else:
                    if len(char.inventory):
                        char.drop(char.inventory[-1])

            # drink from the first available item in inventory
            # bad pattern: the user has to have the choice from what item to drink from
            # bad code: drinking should happen in character
            if key in ("J",):
                if src.gamestate.gamestate.mainChar == char and "norecord" not in flags:
                    text = """

press key for the advanced interaction

* w = activate north
* a = activate west
* s = activate east
* d = activate south
* . = activate item on floor
* f = eat food
* j = activate job order

"""

                    header.set_text(
                        (urwid.AttrSpec("default", "default"), "advanced activate")
                    )
                    main.set_text((urwid.AttrSpec("default", "default"), text))
                    footer.set_text((urwid.AttrSpec("default", "default"), ""))
                    char.specialRender = True

                char.interactionState["advancedInteraction"] = {}
                return

            if key in ("K",):
                if src.gamestate.gamestate.mainChar == char and "norecord" not in flags:
                    text = """

press key for advanced pickup

* w = pick up north
* a = pick up west
* s = pick up east
* d = pick up south
* . = pick item on floor

"""

                    header.set_text(
                        (urwid.AttrSpec("default", "default"), "advanced pick up")
                    )
                    main.set_text((urwid.AttrSpec("default", "default"), text))
                    footer.set_text((urwid.AttrSpec("default", "default"), ""))
                    char.specialRender = True

                char.interactionState["advancedPickup"] = {}
                return

            if key in ("L",):
                if src.gamestate.gamestate.mainChar == char and "norecord" not in flags:
                    text = """

press key for advanced drop

* w = drop north
* a = drop west
* s = drop east
* d = drop south
* . = drop on floor

"""

                    header.set_text(
                        (urwid.AttrSpec("default", "default"), "advanced drop")
                    )
                    main.set_text((urwid.AttrSpec("default", "default"), text))
                    footer.set_text((urwid.AttrSpec("default", "default"), ""))
                    char.specialRender = True

                char.interactionState["advancedDrop"] = {}
                return

            # pick up items
            # bad code: picking up should happen in character
            if key in (commandChars.pickUp,):
                if "NaivePickupQuest" not in char.solvers and not char.godMode:
                    char.addMessage("you do not have the nessecary solver yet (pickup)")
                else:
                    if len(char.inventory) >= 10:
                        char.addMessage("you cannot carry more items")
                    else:
                        item = charState["itemMarkedLast"]

                        if not item:
                            itemList = char.container.getItemByPosition(
                                (char.xPosition, char.yPosition, char.zPosition)
                            )

                            if len(itemList):
                                item = itemList[0]

                        if not item:
                            char.addMessage("no item to pick up found")
                            return

                        item.pickUp(char)
                        if not item.walkable:
                            char.container.calculatePathMap()

            # open chat partner selection
            if key in (commandChars.hail,):
                charState["submenue"] = ChatPartnerselection()

            char.automated = False
            # do automated movement for the main character
            if key in (commandChars.advance, commandChars.autoAdvance):
                if len(char.quests):
                    charState["lastMoveAutomated"] = True
                    char.automated = True
                else:
                    pass

            # recalculate the questmarker since it could be tainted
            elif key not in (commandChars.pause,):
                charState["lastMoveAutomated"] = False
                if char.quests:
                    char.setPathToQuest(char.quests[0])

        # drop the marker for interacting with an item after bumping into it
        # bad code: ignore autoadvance opens up an unintended exploit
        if key not in (
            "lagdetection",
            "lagdetection_",
            commandChars.wait,
            commandChars.autoAdvance,
        ):
            charState["itemMarkedLast"] = None

        char.specialRender = False

        # doesn't open the dev menu and toggles rendering mode instead
        # bad code: code should act as advertised
        if key in (commandChars.devMenu,):
            if src.canvas.displayChars.mode == "unicode":
                src.canvas.displayChars.setRenderingMode("pureASCII")
            else:
                src.canvas.displayChars.setRenderingMode("unicode")

        # open quest menu
        if key in (commandChars.show_quests,):
            charState["submenue"] = QuestMenu()

        # open help menu
        if key in (commandChars.show_help,):
            charState["submenue"] = HelpMenu()

        # open inventory
        if key in (commandChars.show_inventory,):
            charState["submenue"] = InventoryMenu(char)

        # open the menu for giving quests
        if key in (commandChars.show_quests_detailed,):
            charState["submenue"] = AdvancedQuestMenu()

        # open the character information
        if key in (commandChars.show_characterInfo,):
            charState["submenue"] = CharacterInfoMenu(char=char)

        # open the help screen
        if key in (commandChars.show_help,):
            char.specialRender = True

    # render submenus
    if charState["submenue"]:

        # set flag to not render the game
        if src.gamestate.gamestate.mainChar == char and "norecord" not in flags:
            char.specialRender = True

        noRender = True
        if src.gamestate.gamestate.mainChar == char and "norecord" not in flags:
            noRender = False

        # let the submenu handle the keystroke
        lastSubmenu = charState["submenue"]
        done = charState["submenue"].handleKey(key, noRender=noRender)

        if not lastSubmenu == charState["submenue"]:
            charState["submenue"].handleKey("~", noRender=noRender)
            done = False

        # reset rendering flags
        if done:
            charState["submenue"] = None
            char.specialRender = False
            doAdvanceGame = False

    if charState["replay"] or charState["doNumber"]:
        text = ""
        for cmd in reversed(charState["commandKeyQueue"]):
            item = cmd[0]
            if (
                isinstance(item, list)
                or isinstance(item, tuple)
                or item in ("lagdetection", "lagdetection_")
            ):
                continue
            text += str(cmd[0])
        footer.set_text((urwid.AttrSpec("default", "default"), text))


"""
The base class for submenues offering selections
bad code: there is redundant code from the specific submenus that should be put here
"""


class SubMenu(src.saveing.Saveable):
    """
    straightforward state initialization
    """

    def __init__(self, default=None):
        self.state = None
        self.options = {}
        self.selection = None
        self.selectionIndex = 1
        self.persistentText = ""
        self.footerText = "press w / s to move selection up / down, press enter / j / k to select, press esc to exit"
        self.followUp = None
        import collections

        self.options = collections.OrderedDict()
        self.niceOptions = collections.OrderedDict()
        self.default = default
        super().__init__()
        self.attributesToStore.extend(
            [
                "state",
                "selectionIndex",
                "persistentText",
                "footerText",
                "type",
                "query",
                "lockOptions",
            ]
        )
        self.callbacksToStore.extend(["followUp"])
        self.initialState = self.getState()
        self.id = uuid.uuid4().hex

    """
    set internal state from state dictionary
    """

    def setState(self, state):
        super().setState(state)

        # load options
        if "options" in state:
            if state["options"] is None:
                self.options = None
            else:
                import collections

                newOptions = collections.OrderedDict()
                for option in state["options"]:
                    newOptions[option[0]] = option[1]
                self.options = newOptions
        if "niceOptions" in state:
            if state["niceOptions"] is None:
                self.niceOptions = None
            else:
                import collections

                newNiceOptions = collections.OrderedDict()
                for option in state["niceOptions"]:
                    newNiceOptions[option[0]] = option[1]
                self.niceOptions = newNiceOptions

    """
    get state as dictionary
    """

    def getState(self):
        state = super().getState()

        # store options
        if self.options is None:
            serialisedOptions = None
        else:
            serialisedOptions = []
            for k, v in self.options.items():
                serialisedOptions.append((k, str(v)))
        state["options"] = serialisedOptions
        if self.niceOptions is None:
            serialisedOptions = None
        else:
            serialisedOptions = []
            for k, v in self.niceOptions.items():
                serialisedOptions.append((k, str(v)))
        state["niceOptions"] = serialisedOptions

        return state

    """
    sets the options to select from
    """

    def setOptions(self, query, options):
        # convert options to ordered dict
        import collections

        self.options = collections.OrderedDict()
        self.niceOptions = collections.OrderedDict()
        counter = 1
        for option in options:
            self.options[str(counter)] = option[0]
            self.niceOptions[str(counter)] = option[1]
            counter += 1

        # set related state
        self.query = query
        self.selectionIndex = 1
        self.lockOptions = True
        self.selection = None

    """
    straightforward getter for the selected item
    """

    def getSelection(self):
        return self.selection

    """
    show the options and allow the user to select one
    """

    def handleKey(self, key, noRender=False):
        # exit submenu
        if key == "esc":
            return True

        if key == "a":
            # convert options to ordered dict
            oldOptions = self.options
            oldNiceOptions = self.niceOptions

            import collections

            self.options = collections.OrderedDict()
            self.niceOptions = collections.OrderedDict()
            counter = 1
            while counter < len(oldOptions):
                self.options[str(counter)] = oldOptions[str(counter + 1)]
                self.niceOptions[str(counter)] = oldNiceOptions[str(counter + 1)]
                counter += 1
            self.options[str(counter)] = oldOptions[str(1)]
            self.niceOptions[str(counter)] = oldNiceOptions[str(1)]

        if key == "d":
            # convert options to ordered dict
            oldOptions = self.options
            oldNiceOptions = self.niceOptions

            import collections

            self.options = collections.OrderedDict()
            self.niceOptions = collections.OrderedDict()
            counter = 1
            self.options[str(counter)] = oldOptions[str(len(oldOptions))]
            self.niceOptions[str(counter)] = oldNiceOptions[str(len(oldOptions))]
            counter = 2
            while counter < len(oldOptions) + 1:
                self.options[str(counter)] = oldOptions[str(counter - 1)]
                self.niceOptions[str(counter)] = oldNiceOptions[str(counter - 1)]
                counter += 1

        if key in (commandChars.autoAdvance, commandChars.advance):
            if self.default is not None:
                self.selection = self.default
            else:
                self.selection = list(self.options.values())[0]
            self.options = None
            if self.followUp:
                self.followUp()
            return True

        # show question
        out = "\n"
        out += self.query + "\n"

        # handle the selection of options
        if not self.lockOptions:
            # change the marked option
            if key in (
                "w",
                "up",
            ):
                self.selectionIndex -= 1
                if self.selectionIndex == 0:
                    self.selectionIndex = len(self.options)
            if key in (
                "s",
                "down",
            ):
                self.selectionIndex += 1
                if self.selectionIndex > len(self.options):
                    self.selectionIndex = 1
            # select the marked option
            if key in ["enter", "j", "k", "right"]:
                # bad code: transforming the key to the shortcut is needlessly complicated
                if len(self.options.items()):
                    key = list(self.options.items())[self.selectionIndex - 1][0]
                else:
                    self.selection = None
                    self.done = True
                    return True

            # select option by shortcut
            if key in self.options:
                self.selection = self.options[key]
                self.options = None
                if self.followUp:
                    self.callIndirect(self.followUp)
                return True
        else:
            self.lockOptions = False

        if not noRender:
            # render the options
            counter = 0
            for k, v in self.niceOptions.items():
                counter += 1
                if counter == self.selectionIndex:
                    out += str(k) + " ->" + str(v) + "\n"
                else:
                    out += str(k) + " - " + str(v) + "\n"

            # show the rendered options
            # bad code: urwid specific code
            main.set_text(
                (
                    urwid.AttrSpec("default", "default"),
                    self.persistentText + "\n\n" + out,
                )
            )

        return False

    """
    set text in urwid
    bad code: should either be used everywhere or be removed
    bad code: urwid specific code
    """

    def set_text(self, text):
        main.set_text((urwid.AttrSpec("default", "default"), text))


"""
does a simple selection and terminates
bad code: this does nothing the Submenu doesn't do
"""


class SelectionMenu(SubMenu):
    """
    set up the selection
    """

    def __init__(self, text="", options=[], default=None):
        self.type = "SelectionMenu"
        super().__init__(default=default)
        self.setOptions(text, options)

    """
    handles the key
    """

    def handleKey(self, key, noRender=False):
        # exit submenu
        if key == "esc":
            self.selection = None
            if self.followUp:
                self.callIndirect(self.followUp)
            return True
        if not noRender:
            header.set_text("")

        # let superclass handle the actual selection
        if not self.getSelection():
            super().handleKey(key, noRender=noRender)

        # stop when done
        if self.getSelection():
            return True
        else:
            return False


"""
Spawns a Chat submenu with a player selected character
bad code: since there is no need to wait for some return this submenue should not wrap around the Chat menu
bad code: sub menues should be implemented in the base class
"""


class ChatPartnerselection(SubMenu):
    """
    straightforward state initialization
    """

    def __init__(self):
        self.type = "ChatPartnerselection"
        self.subMenu = None
        super().__init__()

    """
    get state as dictionary
    """

    def getState(self):
        state = super().getState()
        if self.subMenu:
            state["subMenu"] = self.subMenu.getState()
        else:
            state["subMenu"] = None

        return state

    """
    set internal state from state as dictionary
    """

    def setState(self, state):
        super().setState(state)

        if "subMenu" in state:
            if state["subMenu"]:
                self.subMenu = getSubmenuFromState(state["subMenu"])
            else:
                self.subMenu = None

    """
    set up the selection and spawn the chat 
    """

    def handleKey(self, key, noRender=False):
        # wrap around the chat menu
        if self.subMenu:
            return self.subMenu.handleKey(key, noRender=noRender)

        # exit the submenu
        if key == "esc":
            return True

        # set title
        header.set_text((urwid.AttrSpec("default", "default"), "\nConversation menu\n"))
        out = "\n"

        # offer the player the option to select from characters to talk to
        # bad code: should be done in __init__
        if not self.options and not self.getSelection():
            options = []
            # get characters in room
            if src.gamestate.gamestate.mainChar.room:
                for char in src.gamestate.gamestate.mainChar.room.characters:
                    if char == src.gamestate.gamestate.mainChar:
                        continue
                    options.append((char, char.name))
            # get character on terrain
            else:
                for char in src.gamestate.gamestate.mainChar.terrain.characters:
                    # bad pattern: should only list nearby characters
                    if char == src.gamestate.gamestate.mainChar:
                        continue
                    options.append((char, char.name))

                # get nearby rooms
                bigX = src.gamestate.gamestate.mainChar.xPosition // 15
                bigY = src.gamestate.gamestate.mainChar.yPosition // 15
                rooms = []
                coordinates = [
                    (bigX, bigY),
                    (bigX - 1, bigY),
                    (bigX + 1, bigY),
                    (bigX, bigY - 1),
                    (bigX, bigY + 1),
                ]
                for coordinate in coordinates:
                    if coordinate not in char.terrain.roomByCoordinates:
                        continue
                    rooms.extend(char.terrain.roomByCoordinates[coordinate])

                # add character from nearby open rooms
                for room in rooms:
                    if not room.open:
                        continue

                    for char in room.characters:
                        options.append((char, char.name))

            self.setOptions("talk with whom?", options)

        # delegate the actual selection to the super class
        if not self.getSelection():
            super().handleKey(key, noRender=noRender)

        # spawn the chat submenu
        if self.getSelection():
            self.subMenu = src.chats.ChatMenu(self.selection)
            self.subMenu.handleKey(key, noRender=noRender)

        # wait for input
        else:
            return False


"""
minimal debug ability
"""


class DebugMenu(SubMenu):
    """
    straightforward state initialization
    """

    def __init__(self, char=None):
        self.type = "DebugMenu"
        super().__init__()

    """
    show some debug output
    """

    def handleKey(self, key, noRender=False):
        # exit submenu
        if key == "esc":
            return True


"""
show the quests for a character and allow player interaction
"""


class QuestMenu(SubMenu):
    """
    straightforward state initialization
    """

    def __init__(self, char=None):
        self.type = "QuestMenu"
        self.lockOptions = True
        if not char:
            char = src.gamestate.gamestate.mainChar
        self.char = char
        self.offsetX = 0
        self.questIndex = 0
        super().__init__()

    """
    show a questlist and handle interactions
    overrides the superclasses method completely
    """

    def handleKey(self, key, noRender=False):
        # exit submenu
        if key == "esc":
            return True

        # scrolling
        # bad code: doesn't actually work
        if key == "W":
            self.offsetX -= 1
        if key == "S":
            self.offsetX += 1
        if self.offsetX < 0:
            self.offsetX = 0

        # move the marker that marks the selected quest
        if key == "w":
            self.questIndex -= 1
        if key == "s":
            self.questIndex += 1
        if self.questIndex < 0:
            self.questIndex = 0
        if self.questIndex > len(self.char.quests) - 1:
            self.questIndex = len(self.char.quests) - 1

        # make the selected quest active
        if key == "j":
            if self.questIndex:
                quest = self.char.quests[self.questIndex]
                self.char.quests.remove(quest)
                self.char.quests.insert(0, quest)
                self.char.setPathToQuest(quest)
                self.questIndex = 0

        # render the quests
        addition = ""
        if self.char == src.gamestate.gamestate.mainChar:
            addition = " (you)"
        header.set_text(
            (
                urwid.AttrSpec("default", "default"),
                "\nquest overview for "
                + self.char.name
                + ""
                + addition
                + "\n(press "
                + commandChars.show_quests_detailed
                + " for the extended quest menu)\n\n",
            )
        )
        self.persistentText = []
        self.persistentText.append(
            renderQuests(char=self.char, asList=True, questIndex=self.questIndex)
        )

        # spawn the quest menu for complex quest handling
        if not self.lockOptions:
            if key in ["q"]:
                global submenue
                submenue = AdvancedQuestMenu()
                submenue.handleKey(key, noRender=noRender)
                return False
        self.lockOptions = False

        # add interaction instructions
        self.persistentText.extend(
            [
                "\n",
                "* press q for advanced quests\n",
                "* press W to scroll up",
                "\n",
                "* press S to scroll down",
                "\n",
                "\n",
            ]
        )

        # flatten the mix of strings and urwid format so that it is less recursive to workaround an urwid bug
        # bad code: should be elsewhere
        def flatten(pseudotext):
            newList = []
            for item in pseudotext:
                if isinstance(item, list):
                    for subitem in flatten(item):
                        newList.append(subitem)
                elif isinstance(item, tuple):
                    newList.append((item[0], flatten(item[1])))
                else:
                    newList.append(item)
            return newList

        self.persistentText = flatten(self.persistentText)

        # show rendered quests via urwid
        main.set_text((urwid.AttrSpec("default", "default"), self.persistentText))

        return False


"""
show the players inventory
bad code: should be abstracted
bad code: uses global functions to render
"""


class InventoryMenu(SubMenu):
    type = "InventoryMenu"

    def __init__(self, char=None):
        self.subMenu = None
        self.skipKeypress = False
        self.activate = False
        self.drop = False
        self.char = char
        super().__init__()
        self.footerText = "press j to activate, press l to drop, press esc to exit"

    """
    show the inventory
    bad pattern: no player interaction
    """

    def handleKey(self, key, noRender=False):
        if self.subMenu:
            self.subMenu.handleKey(key, noRender=noRender)
            if not self.subMenu.getSelection() is None:
                if self.activate:
                    if (
                        "NaiveActivateQuest" not in self.char.solvers
                        and not char.godMode
                    ):
                        self.persistentText = (
                            urwid.AttrSpec("default", "default"),
                            "you do not have the nessecary solver yet (activate)",
                        )
                        main.set_text(
                            (urwid.AttrSpec("default", "default"), self.persistentText)
                        )
                    else:
                        text = (
                            "you activate the "
                            + self.char.inventory[self.subMenu.getSelection()].name
                        )
                        self.persistentText = (
                            urwid.AttrSpec("default", "default"),
                            text,
                        )
                        if not noRender:
                            main.set_text(
                                (
                                    urwid.AttrSpec("default", "default"),
                                    self.persistentText,
                                )
                            )
                        self.char.addMessage(text)
                        self.char.inventory[self.subMenu.getSelection()].apply(
                            self.char
                        )
                    self.activate = False
                    self.subMenu = None
                    return True
                if self.drop:
                    if "NaiveDropQuest" not in self.char.solvers and not char.godMode:
                        self.persistentText = (
                            urwid.AttrSpec("default", "default"),
                            "you do not have the nessecary solver yet (acivate)",
                        )
                        main.set_text(
                            (urwid.AttrSpec("default", "default"), self.persistentText)
                        )
                    else:
                        text = (
                            "you drop the "
                            + self.char.inventory[self.subMenu.getSelection()].name
                        )
                        self.persistentText = (
                            urwid.AttrSpec("default", "default"),
                            text,
                        )
                        if not noRender:
                            main.set_text(
                                (
                                    urwid.AttrSpec("default", "default"),
                                    self.persistentText,
                                )
                            )
                        self.char.addMessage(text)
                        self.char.drop(self.char.inventory[self.subMenu.getSelection()])
                    self.drop = False
                    self.subMenu = None
                    return True
                self.subMenu = None
                self.skipKeypress = True
                return False
            else:
                return False

        if self.skipKeypress:
            self.skipKeypress = False
        else:
            # exit the submenu
            if key == "esc":
                return True

            if key == "j":
                if not len(self.char.inventory):
                    return True

                options = []
                counter = 0
                for item in self.char.inventory:
                    options.append([counter, item.name])
                    counter += 1
                self.subMenu = SelectionMenu("activate what?", options)
                self.subMenu.handleKey(".", noRender=noRender)
                self.activate = True
                return False

            if key == "l":
                if not len(self.char.inventory):
                    return True

                options = []
                counter = 0
                for item in self.char.inventory:
                    options.append([counter, item.name])
                    counter += 1
                self.subMenu = SelectionMenu("drop what?", options)
                self.subMenu.handleKey(".", noRender=noRender)
                self.drop = True
                return False

        if not noRender:
            header.set_text(
                (urwid.AttrSpec("default", "default"), "\ninventory overview\n\n")
            )

            # bad code: uses global function
            self.persistentText = (
                urwid.AttrSpec("default", "default"),
                renderInventory(),
            )

            # show the render
            main.set_text((urwid.AttrSpec("default", "default"), self.persistentText))

        return False


"""
show the players inventory
"""


class InputMenu(SubMenu):
    type = "InputMenu"

    def __init__(self, query="", char=None, ignoreFirst=False):
        self.query = query
        self.text = ""
        super().__init__()
        self.footerText = "enter the text press enter to confirm"
        self.firstHit = True
        self.ignoreFirst = ignoreFirst
        self.escape = False
        self.position = 0

    """
    show the inventory
    """

    def handleKey(self, key, noRender=False):

        if key == "enter" and not self.escape or len(self.text) > 15 * 15:
            if self.followUp:
                self.followUp()
            return True

        if self.ignoreFirst and self.firstHit:
            pass
        elif key == "\\" and not self.escape:
            self.escape = True
        elif key == "backspace" and not self.escape:
            if self.position:
                self.text = (
                    self.text[0: self.position - 1] + self.text[self.position:]
                )
                self.position -= 1
        elif key == "delete" and not self.escape:
            if self.position < len(self.text):
                self.text = (
                    self.text[0: self.position] + self.text[self.position + 1:]
                )
        elif key == "~":
            pass
        elif key == "left":
            self.position -= 1
        elif key == "right":
            self.position += 1
        else:
            if key == "enter":
                key = "\n"
            if len(self.text):
                self.text = (
                    self.text[0: self.position] + key + self.text[self.position:]
                )
            else:
                self.text = key
            self.position += 1
            self.escape = False

        if len(self.text):
            text = self.text[0: self.position] + "█" + self.text[self.position:]
        else:
            text = "█"

        if not noRender:
            header.set_text((urwid.AttrSpec("default", "default"), "\ntext input\n\n"))
            footer.set_text((urwid.AttrSpec("default", "default"), "\ntext input\n\n"))

            self.persistentText = (
                urwid.AttrSpec("default", "default"),
                "\n" + self.query + "\n\n" + text,
            )

            # show the render
            main.set_text((urwid.AttrSpec("default", "default"), self.persistentText))

        if self.firstHit:
            self.firstHit = False

        return False


"""
show the players attributes
bad code: should be abstracted
bad code: uses global function to render
"""


class CharacterInfoMenu(SubMenu):
    type = "CharacterInfoMenu"

    def __init__(self, char=None):
        self.char = char

    """
    show the attributes
    """

    def handleKey(self, key, noRender=False):
        # exit the submenu
        if key == "esc":
            return True

        char = self.char

        text = char.getDetailedInfo() + "\n\n"

        for jobOrder in char.jobOrders:
            text += str(jobOrder.taskName)

        armorValue = None
        if char.armor:
            armorValue = char.armor.armorValue
        baseDamage = None
        if char.weapon:
            baseDamage = char.weapon.baseDamage

        text += "numChars: %s\n" % (len(char.container.characters))
        text += "lastJobOrder: %s\n" % char.lastJobOrder
        text += "weapon: %s\n" % baseDamage
        text += "armor: %s\n" % armorValue
        text += "numAttackedWithoutResponse: %s\n" % char.numAttackedWithoutResponse

        char.setRegisterValue("HEALTh", char.health)
        text += "HEALTh - %s" % char.health + "\n"
        char.setRegisterValue("SELFx", char.xPosition % 15)
        text += "SELFx - %s" % (char.xPosition % 15) + "\n"
        char.setRegisterValue("SELFy", char.yPosition % 15)
        text += "SELFy - %s" % (char.yPosition % 15) + "\n"
        char.setRegisterValue("SELF BIG x", char.xPosition // 15)
        text += "SELF BIG x - %s" % (char.xPosition // 15) + "\n"
        char.setRegisterValue("SELF BIG y", char.yPosition // 15)
        text += "SELF BIG y - %s" % (char.yPosition // 15) + "\n"
        char.setRegisterValue("SATIATIOn", char.satiation)
        text += "SATIATIOn - %s" % char.satiation + "\n"
        char.setRegisterValue("NUM INVENTORY ITEMs", len(char.inventory))
        text += "NUM INVENTORY ITEMs - %s" % (len(char.inventory)) + "\n"
        char.setRegisterValue("frustration", char.frustration)
        text += "frust: %s\n" % char.frustration

        # show info
        header.set_text((urwid.AttrSpec("default", "default"), "\ncharacter overview"))
        main.set_text((urwid.AttrSpec("default", "default"), [text]))
        header.set_text((urwid.AttrSpec("default", "default"), ""))


"""
player interaction for delegating a quest
"""


class AdvancedQuestMenu(SubMenu):
    type = "AdvancedQuestMenu"

    """
    straighforwad state initalisation
    """

    def __init__(self):
        self.character = None
        self.quest = None
        self.questParams = {}
        super().__init__()

    """
    gather the quests parameters and assign the quest
    """

    def handleKey(self, key, noRender=False):
        # exit submenu
        if key == "esc":
            return True

        # start rendering
        header.set_text(
            (urwid.AttrSpec("default", "default"), "\nadvanced Quest management\n")
        )
        out = "\n"
        if self.character:
            out += "character: " + str(self.character.name) + "\n"
        if self.quest:
            out += "quest: " + str(self.quest) + "\n"
        out += "\n"

        # let the player select the character to assign the quest to
        if self.state is None:
            self.state = "participantSelection"
        if self.state == "participantSelection":

            # set up the options
            if not self.options and not self.getSelection():

                # add the main player as target
                options = [(
                    src.gamestate.gamestate.mainChar,
                    src.gamestate.gamestate.mainChar.name + " (you)",
                )]

                # add the main players subordinates as target
                for char in src.gamestate.gamestate.mainChar.subordinates:
                    options.append((char, char.name))
                self.setOptions("whom to give the order to: ", options)

            # let the superclass handle the actual selection
            if not self.getSelection():
                super().handleKey(key, noRender=noRender)

            # store the character to assign the quest to
            if self.getSelection():
                self.state = "questSelection"
                self.character = self.selection
                self.selection = None
                self.lockOptions = True
            else:
                return False

        # let the player select the type of quest to create
        if self.state == "questSelection":

            # add quests to select from
            if not self.options and not self.getSelection():
                options = []
                for key, value in src.quests.questMap.items():

                    # show only quests the character has done
                    if key not in src.gamestate.gamestate.mainChar.questsDone:
                        continue

                    # do not show naive quests
                    if key.startswith("Naive"):
                        continue

                    options.append((value, key))
                options.append(("special_furnace", "vehicle fueling"))
                self.setOptions("what type of quest:", options)

            # let the superclass handle the actual selection
            if not self.getSelection():
                super().handleKey(key, noRender=noRender)

            # store the type of quest to create
            if self.getSelection():
                self.state = "parameter selection"
                self.quest = self.selection
                self.selection = None
                self.lockOptions = True
                self.questParams = {}
            else:
                return False

        # let the player select the parameters for the quest
        if self.state == "parameter selection":
            if self.quest == src.quests.EnterRoomQuestMeta:

                # set up the options
                if not self.options and not self.getSelection():

                    # add a list of of rooms
                    options = []
                    for room in src.gamestate.gamestate.terrain.rooms:
                        # do not show unimportant rooms
                        if isinstance(room, src.rooms.MechArmor) or isinstance(
                            room, src.rooms.CpuWasterRoom
                        ):
                            continue
                        options.append((room, room.name))
                    self.setOptions("select the room:", options)

                # let the superclass handle the actual selection
                if not self.getSelection():
                    super().handleKey(key, noRender=noRender)

                # store the parameter
                if self.getSelection():
                    self.questParams["room"] = self.selection
                    self.state = "confirm"
                    self.selection = None
                    self.lockOptions = True
                else:
                    return False

            elif self.quest == src.quests.StoreCargo:

                # set up the options for selecting the cargo room
                if "cargoRoom" not in self.questParams:
                    if not self.options and not self.getSelection():
                        # add a list of of rooms
                        options = []
                        for room in src.gamestate.gamestate.terrain.rooms:
                            # show only cargo rooms
                            if not isinstance(room, src.rooms.CargoRoom):
                                continue
                            options.append((room, room.name))
                        self.setOptions("select the room:", options)

                    # let the superclass handle the actual selection
                    if not self.getSelection():
                        super().handleKey(key, noRender=noRender)

                    # store the parameter
                    if self.getSelection():
                        self.questParams["cargoRoom"] = self.selection
                        self.selection = None
                        self.lockOptions = True
                    else:
                        return False
                else:
                    # set up the options for selecting the storage room
                    if not self.options and not self.getSelection():
                        # add a list of of rooms
                        options = []
                        for room in src.gamestate.gamestate.terrain.rooms:
                            # show only storage rooms
                            if not isinstance(room, src.rooms.StorageRoom):
                                continue
                            options.append((room, room.name))
                        self.setOptions("select the room:", options)

                    # let the superclass handle the actual selection
                    if not self.getSelection():
                        super().handleKey(key, noRender=noRender)

                    # store the parameter
                    if self.getSelection():
                        self.questParams["storageRoom"] = self.selection
                        self.state = "confirm"
                        self.selection = None
                        self.lockOptions = True
                    else:
                        return False
            else:
                # skip parameter selection
                self.state = "confirm"

        # get confirmation and assign quest
        if self.state == "confirm":

            # set the options for confirming the selection
            if not self.options and not self.getSelection():
                options = [("yes", "yes"), ("no", "no")]
                if self.quest == src.quests.EnterRoomQuestMeta:
                    self.setOptions(
                        "you chose the following parameters:\nroom: "
                        + str(self.questParams)
                        + "\n\nDo you confirm?",
                        options,
                    )
                else:
                    self.setOptions("Do you confirm?", options)

            # let the superclass handle the actual selection
            if not self.getSelection():
                super().handleKey(key, noRender=noRender)

            if self.getSelection():
                # instantiate quest
                # bad code: repetitive code
                if self.selection == "yes":
                    if self.quest == src.quests.MoveQuestMeta:
                        questInstance = self.quest(
                            src.gamestate.gamestate.mainChar.room, 2, 2
                        )
                    elif self.quest == src.quests.ActivateQuestMeta:
                        questInstance = self.quest(
                            src.gamestate.gamestate.terrain.tutorialMachineRoom.furnaces[
                                0
                            ]
                        )
                    elif self.quest == src.quests.EnterRoomQuestMeta:
                        questInstance = self.quest(self.questParams["room"])
                    elif self.quest == src.quests.FireFurnaceMeta:
                        questInstance = self.quest(
                            src.gamestate.gamestate.terrain.tutorialMachineRoom.furnaces[
                                0
                            ]
                        )
                    elif self.quest == src.quests.WaitQuest:
                        questInstance = self.quest()
                    elif self.quest == src.quests.LeaveRoomQuest:
                        try:
                            questInstance = self.quest(self.character.room)
                        except:
                            pass
                    elif self.quest == src.quests.ClearRubble:
                        questInstance = self.quest()
                    elif self.quest == src.quests.RoomDuty:
                        questInstance = self.quest()
                    elif self.quest == src.quests.ConstructRoom:
                        for room in src.gamestate.gamestate.terrain.rooms:
                            if isinstance(room, src.rooms.ConstructionSite):
                                constructionSite = room
                                break
                        questInstance = self.quest(
                            constructionSite,
                            src.gamestate.gamestate.terrain.tutorialStorageRooms,
                        )
                    elif self.quest == src.quests.StoreCargo:
                        for room in src.gamestate.gamestate.terrain.rooms:
                            if isinstance(room, src.rooms.StorageRoom):
                                storageRoom = room
                        questInstance = self.quest(
                            self.questParams["cargoRoom"],
                            self.questParams["storageRoom"],
                        )
                    elif self.quest == src.quests.MoveToStorage:
                        questInstance = self.quest(
                            [
                                src.gamestate.gamestate.terrain.tutorialLab.itemByCoordinates[
                                    (1, 9)
                                ][
                                    0
                                ],
                                src.gamestate.gamestate.terrain.tutorialLab.itemByCoordinates[
                                    (2, 9)
                                ][
                                    0
                                ],
                            ],
                            src.gamestate.gamestate.terrain.tutorialStorageRooms[1],
                        )
                    elif self.quest == "special_furnace":
                        questInstance = src.quests.KeepFurnaceFiredMeta(
                            self.character.room.furnaces[0]
                        )
                    else:
                        questInstance = self.quest()

                    # show some fluff
                    if not self.character == src.gamestate.gamestate.mainChar:
                        self.persistentText += self.character.name + ': "understood?"\n'
                        self.persistentText += (
                            src.gamestate.gamestate.mainChar.name
                            + ': "understood and in execution"\n'
                        )

                    # assign the quest
                    self.character.assignQuest(questInstance, active=True)

                    self.state = "done"

                # reset progress
                else:
                    self.state = "questSelection"

                self.selection = None
                self.lockOptions = False
            else:
                return False

        # close submenu
        if self.state == "done":
            if self.lockOptions:
                self.lockOptions = False
            else:
                return True

        # show rendered text via urwid
        main.set_text((urwid.AttrSpec("default", "default"), self.persistentText))

        return False


"""
render the information section on top of the screen
bad pattern: should be configurable
"""


def renderHeader(character):
    # render the sections to display
    questSection = renderQuests(maxQuests=2)
    messagesSection = renderMessages(character)

    # calculate the size of the elements
    if loop:
        screensize = loop.screen.get_cols_rows()
    else:
        screensize = (400, 400)
    questWidth = (screensize[0] // 3) - 2
    messagesWidth = screensize[0] - questWidth - 3

    # prepare for rendering the header
    txt = ""
    counter = 0
    splitedQuests = questSection.split("\n")
    splitedMessages = messagesSection.split("\n")
    rowCounter = 0

    # add lines for the header
    continueLooping = True
    questLine = ""
    messagesLine = ""
    while True:

        # get the next line for each element
        if questLine == "" and len(splitedQuests):
            questLine = splitedQuests.pop(0)
        if messagesLine == "" and len(splitedMessages):
            messagesLine = splitedMessages.pop(0)

        # stop adding lines after some rounds
        rowCounter += 1
        if rowCounter > 5:
            break

        # cut off left line
        if len(questLine) > questWidth:
            txt += questLine[:questWidth] + "┃ "
            questLine = questLine[questWidth:]

        # pad left line
        else:
            txt += questLine + " " * (questWidth - len(questLine)) + "┃ "
            # bug?: doesn't this pop twice?
            if splitedQuests:
                questLine = splitedQuests.pop(0)
            else:
                questLine = ""

        if len(messagesLine) > messagesWidth:
            # cut off right line
            txt += messagesLine[:messagesWidth]
            messagesLine = messagesLine[messagesWidth:]
        else:
            txt += messagesLine
            # bug?: doesn't this pop twice?
            if splitedMessages:
                messagesLine = splitedMessages.pop(0)
            else:
                messagesLine = ""
        txt += "\n"

    # add the lower decoration
    txt += "━" * +questWidth + "┻" + "━" * (screensize[0] - questWidth - 1) + "\n"

    return txt


"""
render the last x messages into a string
bad code: global function
"""


def renderMessages(character, maxMessages=5):
    txt = ""
    messages = character.messages
    if len(messages) > maxMessages:
        for message in messages[-maxMessages + 1:]:
            txt += str(message) + "\n"
    else:
        for message in messages:
            txt += str(message) + "\n"

    return txt


"""
render the quests into a string or list
bad code: the asList and questIndex parameters are out of place
"""


def renderQuests(maxQuests=0, char=None, asList=False, questIndex=0):
    # basic set up
    if not char:
        char = src.gamestate.gamestate.mainChar
    if asList:
        txt = []
    else:
        txt = ""

    # render the quests
    if len(char.quests):
        counter = 0
        for quest in char.quests:
            # render quest
            if asList:
                if counter == questIndex:
                    txt.extend(
                        [
                            (urwid.AttrSpec("#0f0", "default"), "QUEST: "),
                            quest.getDescription(
                                asList=asList, colored=True, active=True
                            ),
                            "\n",
                        ]
                    )
                else:
                    txt.extend(
                        [
                            (urwid.AttrSpec("#090", "default"), "QUEST: "),
                            quest.getDescription(asList=asList, colored=True),
                            "\n",
                        ]
                    )
            else:
                txt += "QUEST: " + quest.getDescription(asList=asList) + "\n"

            # break if maximum reached
            counter += 1
            if counter == maxQuests:
                break

    # return placeholder for no quests
    else:
        if asList:
            txt.append("No Quest")
        else:
            txt += "No Quest"

    return txt


"""
render the inventory of the player into a string
bad code: global function
bad code: should be abstracted
"""


def renderInventory():
    char = src.gamestate.gamestate.mainChar
    txt = []
    if len(char.inventory):
        counter = 0
        for item in char.inventory:
            counter += 1
            if isinstance(item.render(), int):
                txt.extend(
                    [
                        str(counter),
                        " - ",
                        src.canvas.displayChars.indexedMapping[item.render()],
                        " - ",
                        item.name,
                        "\n     ",
                        item.getDetailedInfo(),
                        "\n",
                    ]
                )
            else:
                txt.extend(
                    [
                        str(counter),
                        " - ",
                        item.render(),
                        " - ",
                        item.name,
                        "\n     ",
                        item.getDetailedInfo(),
                        "\n",
                    ]
                )
    else:
        txt = "empty Inventory"
    return txt


"""
the help submenue
bad code: uses global function to render
"""


class HelpMenu(SubMenu):
    type = "AdvancedQuestMenu"
    """
    show the help text
    """

    def handleKey(self, key, noRender=False):
        # exit the submenu
        if key == "esc":
            return True

        # show info
        header.set_text((urwid.AttrSpec("default", "default"), "\n\nhelp\n\n"))
        self.persistentText = ""
        self.persistentText += renderHelp()
        main.set_text((urwid.AttrSpec("default", "default"), self.persistentText))

        return False


"""
"""


class TextMenu(SubMenu):
    type = "TextMenu"

    def __init__(self, text=""):
        super().__init__()
        self.text = text

    """
    """

    def handleKey(self, key, noRender=False):
        # exit the submenu
        if key in (
            "esc",
            "enter",
            "space",
            "j",
        ):
            if self.followUp:
                self.followUp()
            return True

        if not noRender:
            # show info
            header.set_text((urwid.AttrSpec("default", "default"), ""))
            self.persistentText = ""
            self.persistentText += self.text
            main.set_text((urwid.AttrSpec("default", "default"), self.persistentText))

        return False


"""
"""


class OneKeystrokeMenu(SubMenu):
    type = "OneKeystrokeMenu"

    def __init__(self, text=""):
        super().__init__()
        self.text = text
        self.firstRun = True
        self.keyPressed = ""
        self.done = False

    """
    """

    def handleKey(self, key, noRender=False):

        # show info
        if not noRender:
            header.set_text((urwid.AttrSpec("default", "default"), ""))
            self.persistentText = ""
            self.persistentText += self.text
            main.set_text((urwid.AttrSpec("default", "default"), self.persistentText))

        # exit the submenu
        if key not in ("~",) and not self.firstRun:
            self.keyPressed = key
            if self.followUp:
                self.callIndirect(self.followUp)
            self.done = True
            return True

        self.firstRun = False

        return False


"""
return the help text
bad code: should not be a global function
"""


def renderHelp():
    char = src.gamestate.gamestate.mainChar
    txt = "the Goal of the Game is to stay alive and build a base.\nThe daily Grind can be delageted to subordinates.\n\nThe game is focused on automation so try to use Commands and NPCs to automate production.\n\nUse the Auto tutor to do challenges and to learn how to play the game.\n\n"
    txt += "your keybindings are:\n\n"
    txt += "* move_north: " + commandChars.move_north + "\n"
    txt += "* move_east: " + commandChars.move_east + "\n"
    txt += "* move_west: " + commandChars.move_west + "\n"
    txt += "* move_south: " + commandChars.move_south + "\n"
    txt += "* activate: " + commandChars.activate + "\n"
    txt += "* drink: " + commandChars.drink + "\n"
    txt += "* pickUp: " + commandChars.pickUp + "\n"
    txt += "* drop: " + commandChars.drop + "\n"
    txt += "* hail: " + commandChars.hail + "\n"
    txt += "* examine: " + commandChars.examine + "\n"
    txt += "* quit_normal: " + commandChars.quit_normal + "\n"
    txt += "* quit_instant: " + commandChars.quit_instant + "\n"
    txt += "* quit_delete: " + commandChars.quit_delete + "\n"
    txt += "* autoAdvance: " + commandChars.autoAdvance + "\n"
    txt += "* advance: " + commandChars.advance + "\n"
    txt += "* pause: " + commandChars.pause + "\n"
    txt += "* ignore: " + commandChars.ignore + "\n"
    txt += "* wait: " + commandChars.wait + "\n"
    txt += "* show_quests " + commandChars.show_quests + "\n"
    txt += "* show_quests_detailed: " + commandChars.show_quests_detailed + "\n"
    txt += "* show_inventory: " + commandChars.show_inventory + "\n"
    txt += "* show_inventory_detailed: " + commandChars.show_inventory_detailed + "\n"
    txt += "* show_characterInfo: " + commandChars.show_characterInfo + "\n"
    txt += "* redraw: " + commandChars.redraw + "\n"
    txt += "* show_help: " + commandChars.show_help + "\n"
    txt += "* attack: " + commandChars.attack + "\n"
    txt += "* devMenu: " + commandChars.devMenu + "\n"
    txt += "\n\nMove onto an item and press the key to interact with it. Move against big items and press the key to interact with it\n\n"
    return txt


lastTerrain = None

lastCenterX = None
lastCenterY = None
"""
render the map
bad code: should be contained somewhere
"""


def render(char):
    if char.room:
        thisTerrain = char.room.terrain
    else:
        thisTerrain = char.terrain

    global lastTerrain
    if thisTerrain:
        lastTerrain = thisTerrain
    else:
        thisTerrain = lastTerrain

    # render the map
    if (
        src.gamestate.gamestate.mainChar.room
        and not src.gamestate.gamestate.mainChar.room.xPosition
    ):
        chars = src.gamestate.gamestate.mainChar.room.render()
    else:
        chars = thisTerrain.render()

    # center on player
    # bad code: should focus on arbitrary positions
    if (
        src.gamestate.gamestate.mainChar.room
        and src.gamestate.gamestate.mainChar.room.xPosition
    ):
        centerX = (
            src.gamestate.gamestate.mainChar.room.xPosition * 15
            + src.gamestate.gamestate.mainChar.room.offsetX
            + src.gamestate.gamestate.mainChar.xPosition
        )
        centerY = (
            src.gamestate.gamestate.mainChar.room.yPosition * 15
            + src.gamestate.gamestate.mainChar.room.offsetY
            + src.gamestate.gamestate.mainChar.yPosition
        )
    else:
        centerX = src.gamestate.gamestate.mainChar.xPosition
        centerY = src.gamestate.gamestate.mainChar.yPosition

    global lastCenterX
    global lastCenterY
    if not centerX:
        centerX = lastCenterX
        centerY = lastCenterY
    else:
        lastCenterX = centerX
        lastCenterY = centerY

    # set size of the window into the world
    viewsize = 41
    halfviewsite = (viewsize - 1) // 2

    # calculate the windows position
    if loop:
        screensize = loop.screen.get_cols_rows()
        decorationSize = frame.frame_top_bottom(loop.screen.get_cols_rows(), True)
        screensize = (
            screensize[0] - decorationSize[0][0],
            screensize[1] - decorationSize[0][1],
        )
    else:
        screensize = (400, 400)
    shift = (
        screensize[1] // 2 - (viewsize - 1) // 2,
        screensize[0] // 4 - (viewsize - 1) // 2,
    )

    # place rendering in screen
    canvas = src.canvas.Canvas(
        size=(viewsize, viewsize),
        chars=chars,
        coordinateOffset=(centerY - halfviewsite, centerX - halfviewsite),
        shift=shift,
        displayChars=src.canvas.displayChars,
        tileMapping=tileMapping,
    )

    return canvas


multi_currentChar = None
multi_chars = None
charindex = 0


def keyboardListener(key):
    global multi_currentChar
    global multi_chars
    global charindex

    global continousOperation
    continousOperation = -1

    if not multi_currentChar:
        multi_currentChar = src.gamestate.gamestate.mainChar
    if multi_chars is None:
        multi_chars = src.gamestate.gamestate.terrain.characters[:]
        for room in src.gamestate.gamestate.terrain.rooms:
            for character in room.characters[:]:
                if character not in multi_chars:
                    multi_chars.append(character)

    state = src.gamestate.gamestate.mainChar.macroState

    if key == "ctrl d":
        state["commandKeyQueue"].clear()
        state["loop"] = []
        state["replay"].clear()
        if "ifCondition" in src.gamestate.gamestate.mainChar.interactionState:
            src.gamestate.gamestate.mainChar.interactionState["ifCondition"].clear()
            src.gamestate.gamestate.mainChar.interactionState["ifParam1"].clear()
            src.gamestate.gamestate.mainChar.interactionState["ifParam2"].clear()

    elif key == "ctrl p":
        if not src.gamestate.gamestate.mainChar.macroStateBackup:
            src.gamestate.gamestate.mainChar.macroStateBackup = (
                src.gamestate.gamestate.mainChar.macroState
            )
            src.gamestate.gamestate.mainChar.setDefaultMacroState()
            src.gamestate.gamestate.mainChar.macroState[
                "macros"
            ] = src.gamestate.gamestate.mainChar.macroStateBackup["macros"]

            state = src.gamestate.gamestate.mainChar.macroState
        else:
            src.gamestate.gamestate.mainChar.macroState = (
                src.gamestate.gamestate.mainChar.macroStateBackup
            )
            src.gamestate.gamestate.mainChar.macroState[
                "macros"
            ] = src.gamestate.gamestate.mainChar.macroStateBackup["macros"]
            src.gamestate.gamestate.mainChar.macroStateBackup = None

    elif key == "ctrl x":
        src.gamestate.gamestate.save()
        raise urwid.ExitMainLoop()

    elif key == "ctrl o":
        with open("macros.json", "r") as macroFile:
            import json

            rawMacros = json.loads(macroFile.read())
            parsedMacros = {}

            state = "normal"
            for key, value in rawMacros.items():
                parsedMacro = []
                for char in value:
                    if state == "normal":
                        if char == "/":
                            state = "multi"
                            combinedKey = ""
                            continue
                        parsedMacro.append(char)
                    if state == "multi":
                        if char == "/":
                            state = "normal"
                            parsedMacro.append(combinedKey)
                        else:
                            combinedKey += char
                parsedMacros[key] = parsedMacro

            src.gamestate.gamestate.mainChar.macroState["macros"] = parsedMacros

    elif key == "ctrl k":
        with open("macros.json", "w") as macroFile:
            import json

            compressedMacros = {}
            for key, value in src.gamestate.gamestate.mainChar.macroState[
                "macros"
            ].items():
                compressedMacro = ""
                for keystroke in value:
                    if len(keystroke) == 1:
                        compressedMacro += keystroke
                    else:
                        compressedMacro += "/" + keystroke + "/"
                compressedMacros[key] = compressedMacro
            macroFile.write(json.dumps(compressedMacros, indent=10, sort_keys=True))

    elif key == "ctrl a":
        for character in src.gamestate.gamestate.terrain.characters:
            if character not in multi_chars:
                multi_chars.append(character)
        for room in src.gamestate.gamestate.terrain.rooms:
            for character in room.characters[:]:
                if character not in multi_chars:
                    multi_chars.append(character)

        toRemove = []
        for character in multi_chars:
            if character.dead:
                toRemove.append(character)
        for character in toRemove:
            multi_chars.remove(character)

        newChar = None

        charindex += 1
        if charindex >= len(multi_chars):
            charindex = 0
        newChar = multi_chars[charindex]

        if not newChar:
            messages.append("charindex %s" % charindex)
            return

        src.gamestate.gamestate.mainChar = newChar
        state = src.gamestate.gamestate.mainChar.macroState

    elif key == "ctrl w":
        if not src.gamestate.gamestate.mainChar.room:
            return
        import json

        state = src.gamestate.gamestate.mainChar.room.getState()
        serializedState = json.dumps(state, indent=10, sort_keys=True)

        with open("roomExport.json", "w") as exportFile:
            exportFile.write(serializedState)

    else:
        show_or_exit(key, charState=state)


lastAdvance = 0
lastAutosave = 0


def gameLoop(loop, user_data=None):
    import time

    global lastAdvance
    global fixedTicks
    global lastAutosave

    runFixedTick = False
    if speed:
        fixedTicks = speed
    if fixedTicks and time.time() - lastAdvance > fixedTicks:
        runFixedTick = True

    global multi_currentChar
    global multi_chars

    firstRun = True
    while not loop or firstRun:

        if lastAutosave == 0:
            lastAutosave = src.gamestate.gamestate.tick
        if src.gamestate.gamestate.tick - lastAutosave > 1000:
            # src.gamestate.gamestate.save()
            lastAutosave = src.gamestate.gamestate.tick

        firstRun = False

        if not multi_currentChar:
            multi_currentChar = src.gamestate.gamestate.mainChar
        if multi_chars is None:
            multi_chars = []

        # transform and store the keystrokes that accumulated in pygame
        if useTiles:
            import pygame

            for item in pygame.event.get():
                if item.type == pygame.QUIT:
                    src.gamestate.gamestate.save()
                    pygame.quit()
                if not hasattr(item, "unicode"):
                    continue
                key = item.unicode
                if key == "":
                    continue
                if key == "\x10":
                    key = "ctrl p"
                if key == "\x18":
                    key = "ctrl x"
                if key == "\x0f":
                    key = "ctrl o"
                if key == "\x04":
                    key = "ctrl d"
                if key == "\x0b":
                    key = "ctrl k"
                if key == "\x01":
                    key = "ctrl a"
                if key == "\x17":
                    key = "ctrl w"
                if key == "\x1b":
                    key = "esc"
                if key == "\r":
                    key = "enter"
                keyboardListener(key)

        for char in src.gamestate.gamestate.terrain.characters[:]:
            if char not in multi_chars:
                multi_chars.append(char)

        for room in src.gamestate.gamestate.terrain.rooms:
            for character in room.characters[:]:
                if character not in multi_chars:
                    multi_chars.append(character)

        for char in multi_chars:
            if char.room:
                for other in char.room.characters:
                    if other not in multi_chars:
                        multi_chars.append(other)

        global continousOperation
        if (
            src.gamestate.gamestate.mainChar.macroState["commandKeyQueue"] and not speed
        ) or runFixedTick:
            continousOperation += 1

            if not len(cinematics.cinematicQueue):
                lastAdvance = time.time()
                advanceGame()

            removeChars = []
            for char in multi_chars:
                if char.dead and not char == src.gamestate.gamestate.mainChar:
                    removeChars.append(char)
                if char.stasis:
                    continue

                if (
                    len(cinematics.cinematicQueue)
                    and not char == src.gamestate.gamestate.mainChar
                ):
                    continue

                state = char.macroState

                # do random action
                if not len(state["commandKeyQueue"]):
                    char.startIdling()

                if len(state["commandKeyQueue"]):
                    key = state["commandKeyQueue"][0]
                    while (
                        isinstance(key[0], list)
                        or isinstance(key[0], tuple)
                        or key[0] in ("lagdetection", "lagdetection_")
                    ):
                        if len(state["commandKeyQueue"]):
                            key = state["commandKeyQueue"][0]
                            state["commandKeyQueue"].remove(key)
                        else:
                            key = ("~", [])

                    while len(state["commandKeyQueue"]) and char.timeTaken < 1:
                        key = state["commandKeyQueue"][0]
                        state["commandKeyQueue"].remove(key)
                        processInput(
                            key, charState=state, noAdvanceGame=True, char=char
                        )

                    char.timeTaken -= 1

            for char in removeChars:
                multi_chars.remove(char)

            text = ""
            for cmd in src.gamestate.gamestate.mainChar.macroState["commandKeyQueue"]:
                item = cmd[0]
                if (
                    isinstance(item, list)
                    or isinstance(item, tuple)
                    or item in ("lagdetection", "lagdetection_")
                ):
                    continue
                text += str(cmd[0])
            text += (
                " | satiation: "
                + str(src.gamestate.gamestate.mainChar.satiation)
                + " health: "
                + str(src.gamestate.gamestate.mainChar.health)
            )
            footer.set_text((urwid.AttrSpec("default", "default"), text))

            def stringifyUrwid(inData):
                outData = ""
                for item in inData:
                    if isinstance(item, tuple):
                        outData += stringifyUrwid(item[1])
                    if isinstance(item, list):
                        outData += stringifyUrwid(item)
                    if isinstance(item, str):
                        outData += item
                return outData

            # render the game
            if not src.gamestate.gamestate.mainChar.specialRender:

                skipRender = True

                thresholds = [
                    10,
                    50,
                    100,
                    500,
                    1000,
                    5000,
                    10000,
                    50000,
                    100000,
                    500000,
                    1000000,
                ]
                skipper = 0
                for threshold in thresholds:
                    if continousOperation > threshold:
                        skipper += 1
                if skipper == 0 or src.gamestate.gamestate.tick % skipper == 0:
                    skipRender = False

                if (
                    len(src.gamestate.gamestate.mainChar.macroState["commandKeyQueue"])
                    == 0
                ):
                    skipRender = False

                if (not skipRender) or fixedTicks:

                    # render map
                    # bad code: display mode specific code
                    canvas = render(src.gamestate.gamestate.mainChar)
                    if not src.gamestate.gamestate.mainChar.godMode and (
                        src.gamestate.gamestate.mainChar.satiation < 100
                        or src.gamestate.gamestate.mainChar.health < 10
                    ):
                        warning = True
                    else:
                        warning = False
                    main.set_text(
                        (
                            urwid.AttrSpec("#999", "black"),
                            canvas.getUrwirdCompatible(warning=warning),
                        )
                    )
                    if useTiles:
                        canvas.setPygameDisplay(pydisplay, pygame, tileSize)
                    header.set_text(
                        (
                            urwid.AttrSpec("default", "default"),
                            renderHeader(src.gamestate.gamestate.mainChar),
                        )
                    )
                    if useTiles:
                        w, h = pydisplay.get_size()

                        font = pygame.font.Font("config/DejaVuSansMono.ttf", 14)
                        plainText = stringifyUrwid(header.get_text())
                        counter = 0
                        for line in plainText.split("\n"):
                            text = font.render(line, True, (200, 200, 200))
                            pydisplay.blit(text, (0, 0 + 15 * counter))
                            counter += 1
                        pygame.display.update()

                        plainText = stringifyUrwid(footer.get_text())
                        text = font.render(plainText, True, (200, 200, 200))
                        tw, th = font.size(plainText)
                        pydisplay.blit(text, (w - tw - 8, h - th - 8))
                        pygame.display.update()
            else:
                if useTiles:
                    pydisplay.fill((0, 0, 0))
                    font = pygame.font.Font("config/DejaVuSansMono.ttf", 14)

                    plainText = stringifyUrwid(main.get_text())
                    counter = 0
                    for line in plainText.split("\n"):
                        text = font.render(line, True, (200, 200, 200))
                        pydisplay.blit(text, (30, 110 + 15 * counter))
                        counter += 1

                    pygame.display.update()
        else:
            continousOperation = 0

    loop.set_alarm_in(0.001, gameLoop)


loop = None

s = None


def tmp2(loop, user_data):
    if not multiplayer:
        return

    HOST = "127.0.0.1"
    PORT = 65440

    global s
    if not s:
        import socket

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((HOST, PORT))
        s.listen()

    import json
    import urwid

    conn, addr = s.accept()
    with conn:
        data = conn.recv(1024 * 1024 * 1024)

        if data == b"ignore":
            loop.set_alarm_in(0.1, tmp2)
            return

        realMainChar = src.gamestate.gamestate.mainChar

        if len(multi_chars) > 1:
            src.gamestate.gamestate.mainChar = multi_chars[1]

        if data == b"redraw":
            pass
        else:
            for key in json.loads(data.decode("utf-8")):
                keyboardListener(key)

        canvas = render(src.gamestate.gamestate.mainChar)
        info = {
            "head": ["adsada"],
            "main": [(urwid.AttrSpec("#999", "black"), canvas.getUrwirdCompatible())],
            "footer": ["asdasdasf sf"],
        }
        src.gamestate.gamestate.mainChar = realMainChar

        def serializeUrwid(inData):
            outData = []
            for item in inData:
                if isinstance(item, tuple):
                    outData.append(
                        [
                            "tuple",
                            [item[0].foreground, item[0].background],
                            serializeUrwid(item[1]),
                        ]
                    )
                if isinstance(item, list):
                    outData.append(["list", serializeUrwid(item)])
                if isinstance(item, str):
                    outData.append(["str", item])
            return outData

        info["head"] = serializeUrwid(info["head"])
        info["main"] = serializeUrwid(info["main"])
        info["footer"] = serializeUrwid(info["footer"])

        info = json.dumps(info)
        data = info.encode("utf-8")
        conn.sendall(data)

    loop.set_alarm_in(0.1, tmp2)


# the directory for the submenus
subMenuMap = {
    "SelectionMenu": SelectionMenu,
    "ChatPartnerselection": ChatPartnerselection,
    "DebugMenu": DebugMenu,
    "QuestMenu": QuestMenu,
    "InventoryMenu": InventoryMenu,
    "CharacterInfoMenu": CharacterInfoMenu,
    "AdvancedQuestMenu": AdvancedQuestMenu,
    "HelpMenu": HelpMenu,
    "TextMenu": TextMenu,
    "OneKeystrokeMenu": OneKeystrokeMenu,
}

"""
get item instances from dict state
"""


def getSubmenuFromState(state):
    print(state)
    subMenu = subMenuMap[state["type"]]()
    subMenu.setState(state)
    src.saveing.loadingRegistry.register(subMenu)
    return subMenu
