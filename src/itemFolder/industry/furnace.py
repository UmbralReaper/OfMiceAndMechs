import src

"""
heat source for generating steam and similar
"""


class Furnace(src.items.Item):
    type = "Furnace"

    """
    straightforward state initialization
    """

    def __init__(self):
        self.activated = False
        self.boilers = []
        super().__init__(display=src.canvas.displayChars.furnace_inactive)
        self.name = "Furnace"

        # set metadata for saving
        self.attributesToStore.extend(["activated"])

    """
    fire the furnace
    """

    def apply(self, character):
        super().apply(character, silent=True)

        # select fuel
        # bad pattern: the player should be able to select fuel
        # bad pattern: coal should be preferred
        foundItem = None
        for item in character.inventory:
            canBurn = False
            if hasattr(item, "canBurn"):
                canBurn = item.canBurn

            if not canBurn:
                continue
            foundItem = item

        # refuse to fire the furnace without fuel
        if not foundItem:
            # bad code: return would be preferable to if/else
            if character.watched:
                character.addMessage(
                    "you need coal to fire the furnace and you have no coal in your inventory"
                )
        else:
            # refuse to fire burning furnace
            if self.activated:
                # bad code: return would be preferable to if/else
                if character.watched:
                    character.addMessage("already burning")
            # fire the furnace
            else:
                self.activated = True

                # destroy fuel
                character.inventory.remove(foundItem)
                character.changed()

                # add fluff
                if character.watched:
                    character.addMessage("you fire the furnace")

                # get the boilers affected
                self.boilers = []
                for boiler in self.container.itemsOnFloor:
                    if isinstance(boiler, src.items.Boiler):
                        if (
                            (
                                boiler.xPosition
                                in [
                                    self.xPosition,
                                    self.xPosition - 1,
                                    self.xPosition + 1,
                                ]
                                and boiler.yPosition == self.yPosition
                            )
                            or boiler.yPosition
                            in [self.yPosition - 1, self.yPosition + 1]
                            and boiler.xPosition == self.xPosition
                        ):
                            self.boilers.append(boiler)

                # heat up boilers
                for boiler in self.boilers:
                    boiler.startHeatingUp()

                # make the furnace stop burning after some time
                event = src.events.FurnaceBurnoutEvent(
                    self.container.timeIndex + 30
                )
                event.furnace = self
                self.container.addEvent(event)

                # notify listeners
                self.changed()

    def render(self):
        """
        render the furnace
        """
        if self.activated:
            return src.canvas.displayChars.furnace_active
        else:
            return src.canvas.displayChars.furnace_inactive

    def getLongInfo(self):
        text = """
item: Furnace

description:
A furnace is used to generate heat. Heat is used to produce steam in boilers.

You can fire the furnace by activating it with coal in your inventory.

Place the furnace next to a boiler to be able to heat up the boiler with this furnace.

"""
        return text

    def getLongInfo(self):
        return str(self.id)


src.items.addType(Furnace)
