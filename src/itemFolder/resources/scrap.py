import src


class Scrap(src.items.Item):
    """
    crushed something, basically raw metal
    """

    type = "Scrap"

    def __init__(self, amount=1, name="scrap", noId=False):
        """
        almost straightforward state initialization
        """

        super().__init__(display=src.canvas.displayChars.scrap_light, name=name)

        # set up metadata for saving
        self.attributesToStore.extend(["amount"])

        self.bolted = False

        # how many scraps this pile consists of
        self.amount = amount

        # reset walkable
        self.setWalkable()

    def moveDirection(self, direction, force=1, initialMovement=True):
        """
        move the item and leave residue
        """
        self.dropStuff()
        super().moveDirection(direction, force, initialMovement)

    # bad code: only works on terrain
    def dropStuff(self):
        """
        leave a trail of pieces
        """

        # only drop something if there is something left to drop
        if self.amount <= 1:
            return

        # determine how much should fall off
        fallOffAmount = 1
        if self.amount > 2:
            fallOffAmount = 2

        # remove scrap from self
        self.amount -= fallOffAmount

        # generate the fallen off scrap
        newItem = Scrap(amount=fallOffAmount)
        self.container.addItem(newItem, self.xPosition, self.yPosition)

        self.setWalkable()

    def setWalkable(self):
        """
        recalculate the walkable attribute
        """
        if self.amount < 5:
            self.walkable = True
        else:
            self.walkable = False

    def render(self):
        """
        render the scrap depending on amount
        """
        if self.amount < 5:
            return src.canvas.displayChars.scrap_light
        elif self.amount < 15:
            return src.canvas.displayChars.scrap_medium
        else:
            return src.canvas.displayChars.scrap_heavy

    def getResistance(self):
        """
        get resistance to beeing moved depending on size
        """
        return self.amount * 2

    def destroy(self, generateSrcap=True):
        """
        destroying scrap means to merge the scrap
        """

        # get list of scrap on same location
        # bad code: should be handled in the container
        foundScraps = []
        for item in self.container.getItembyPosition(
            (self.xPosition, self.yPosition, self.zPosition)
        ):
            if item.type == "Scrap":
                foundScraps.append(item)

        # merge existing and new scrap
        toRemove = []
        if len(foundScraps) > 1:
            for item in foundScraps:
                if item == self:
                    continue
                self.amount += item.amount
                toRemove.append(item)

        self.container.removeItems(toRemove)

    def getLongInfo(self):
        """
        generate simple text description
        """

        text = """
item: Scrap

description:
Scrap is a raw material. Its main use is to be converted to metal bars in a scrap compactor.

There is %s in this pile
""" % (
            self.amount,
        )

        return text

    def pickUp(self, character):
        """
        get picked up by the supplied character
        """

        # get picked up completely
        if self.amount <= 1:
            super().pickUp(character)
            return

        # prevents crashes
        if self.xPosition is None or self.yPosition is None:
            return

        # remove a singe piece of scrap
        self.amount -= 1
        character.addMessage(
            "you pick up a piece of scrap, there is %s left" % (self.amount,)
        )

        # add item to characters inventory
        character.addToInventory(Scrap(amount=1))

    def apply(self, character):
        """
        add more scrap to a scrap pile if available
        """
        scrapFound = []
        for item in character.inventory:
            if item.type == "Scrap":
                scrapFound.append(item)
                break

        for item in scrapFound:
            if self.amount < 20:
                self.amount += item.amount
                character.addMessage(
                    "you add a piece of scrap there pile contains %s scrap now."
                    % (self.amount,)
                )
                character.inventory.remove(item)

        self.setWalkable()


src.items.addType(Scrap)
