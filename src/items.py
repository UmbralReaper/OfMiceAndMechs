messages = None
characters = None
displayChars = None
stealKey = None
commandChars = None
terrain = None

class Item(object):
	def __init__(self,display=None,xPosition=0,yPosition=0):
		if not display:
			self.display = displayChars.notImplentedYet
		else:
			self.display = display
		self.xPosition = xPosition
		self.yPosition = yPosition
		self.listeners = []
		self.walkable = False
		self.room = None
		self.name = "item"
		self.lastMovementToken = None
		self.chainedTo = []

	def apply(self,character):
		messages.append("i can't do anything useful with this")

	def changed(self):
		messages.append(self.name+": Object changed")
		for listener in self.listeners:
			listener()

	def addListener(self,listenFunction):
		if not listenFunction in self.listeners:
			self.listeners.append(listenFunction)

	def delListener(self,listenFunction):
		if listenFunction in self.listeners:
			self.listeners.remove(listenFunction)

	def getAffectedByMovementNorth(self,force=1,movementBlock=set()):
		movementBlock.add(self)
		
		for thing in self.chainedTo:
			if thing not in movementBlock and not thing == self:
				movementBlock.add(thing)
				thing.getAffectedByMovementNorth(force=force,movementBlock=movementBlock)

		return movementBlock

	def moveNorth(self,movementToken=None):
		if not movementToken:
			import random
			movementToken = random.randint(0, 1000000)
	
		self.lastMovementToken = movementToken

		try:
			del self.terrain.itemByCoordinates[(self.xPosition,self.yPosition)]
		except:
			pass
		self.yPosition -= 1
		self.terrain.itemByCoordinates[(self.xPosition,self.yPosition)] = self

		for thing in self.chainedTo:
			if thing.lastMovementToken == movementToken:
				continue
			thing.moveNorth(movementToken=movementToken)

	def getAffectedByMovementSouth(self,force=1,movementBlock=set()):
		movementBlock.add(self)
		
		for thing in self.chainedTo:
			if thing not in movementBlock and not thing == self:
				movementBlock.add(thing)
				thing.getAffectedByMovementSouth(force=force,movementBlock=movementBlock)

		return movementBlock

	def moveSouth(self,force=1,initialMovement=True):
		try:
			del self.terrain.itemByCoordinates[(self.xPosition,self.yPosition)]
		except:
			pass
		self.yPosition += 1
		self.terrain.itemByCoordinates[(self.xPosition,self.yPosition)] = self

	def getAffectedByMovementWest(self,force=1,movementBlock=set()):
		movementBlock.add(self)
		
		for thing in self.chainedTo:
			if thing not in movementBlock and not thing == self:
				movementBlock.add(thing)
				thing.getAffectedByMovementWest(force=force,movementBlock=movementBlock)

		return movementBlock

	def moveWest(self,movementToken=None):
		if not movementToken:
			import random
			movementToken = random.randint(0, 1000000)
	
		self.lastMovementToken = movementToken
		try:
			del self.terrain.itemByCoordinates[(self.xPosition,self.yPosition)]
		except:
			pass
		self.xPosition -= 1
		self.terrain.itemByCoordinates[(self.xPosition,self.yPosition)] = self

		for thing in self.chainedTo:
			if thing.lastMovementToken == movementToken:
				continue
			thing.moveWest(movementToken=movementToken)

	def getAffectedByMovementEast(self,force=1,movementBlock=set()):
		movementBlock.add(self)
		
		for thing in self.chainedTo:
			if thing not in movementBlock and not thing == self:
				movementBlock.add(thing)
				thing.getAffectedByMovementEast(force=force,movementBlock=movementBlock)

		return movementBlock

	def moveEast(self,movementToken=None):
		if not movementToken:
			import random
			movementToken = random.randint(0, 1000000)
	
		self.lastMovementToken = movementToken
		try:
			del self.terrain.itemByCoordinates[(self.xPosition,self.yPosition)]
		except:
			pass
		self.xPosition += 1
		self.terrain.itemByCoordinates[(self.xPosition,self.yPosition)] = self

		for thing in self.chainedTo:
			if thing.lastMovementToken == movementToken:
				continue
			thing.moveEast(movementToken=movementToken)

	def getResistance(self):
		return 1

class Corpse(Item):
	def __init__(self,xPosition=0,yPosition=0,name="corpse"):
		super().__init__(displayChars.corpse,xPosition,yPosition)
		self.walkable = True

class Hutch(Item):
	def __init__(self,xPosition=0,yPosition=0,name="Hutch",activated=False):
		self.activated = activated
		if self.activated:
			super().__init__(displayChars.hutch_free,xPosition,yPosition)
		else:
			super().__init__(displayChars.hutch_occupied,xPosition,yPosition)

	def apply(self,character):
		if not self.activated:
			self.activated = True
			self.display = displayChars.hutch_occupied
		else:
			self.activated = False
			self.display = displayChars.hutch_free

class Lever(Item):
	def __init__(self,xPosition=0,yPosition=0,name="lever",activated=False):
		self.activated = activated
		self.display = {True:displayChars.lever_pulled,False:displayChars.lever_notPulled}
		self.name = name
		super().__init__(displayChars.lever_notPulled,xPosition,yPosition)
		self.activateAction = None
		self.deactivateAction = None
		self.walkable = True

	def apply(self,character):
		if not self.activated:
			self.activated = True
			self.display = displayChars.lever_pulled
			messages.append(self.name+": activated!")

			if self.activateAction:
				self.activateAction(self)
		else:
			self.activated = False
			self.display = displayChars.lever_notPulled
			messages.append(self.name+": deactivated!")

			if self.deactivateAction:
				self.activateAction(self)
		self.changed()

class Furnace(Item):
	def __init__(self,xPosition=0,yPosition=0,name="Furnace"):
		self.name = name
		self.activated = False
		super().__init__(displayChars.furnace_inactive,xPosition,yPosition)

	def apply(self,character):
		messages.append("Furnace used")
		foundItem = None
		for item in character.inventory:
			try:
				canBurn = item.canBurn
			except:
				continue
			if not canBurn:
				continue

			foundItem = item

		if not foundItem:
			messages.append("keine KOHLE zum anfeuern")
		else:
			self.activated = True
			self.display = displayChars.furnace_active
			character.inventory.remove(foundItem)
			messages.append("burn it ALL")
		self.changed()

class Display(Item):
	def __init__(self,xPosition=0,yPosition=0,name="Display"):
		self.name = name
		super().__init__(displayChars.display,xPosition,yPosition)

	def apply(self,character):
		def moveNorth():
			self.room.moveNorth(force=self.room.engineStrength)
		def moveSouth():
			self.room.moveSouth(force=self.room.engineStrength)
		def moveWest():
			self.room.moveWest(force=self.room.engineStrength)
		def moveEast():
			self.room.moveEast(force=self.room.engineStrength)
		def disapply():
			del stealKey[commandChars.move_north]
			del stealKey[commandChars.move_south]
			del stealKey[commandChars.move_west]
			del stealKey[commandChars.move_east]
			del stealKey[commandChars.activate]
		stealKey[commandChars.move_north] = moveNorth
		stealKey[commandChars.move_south] = moveSouth
		stealKey[commandChars.move_west] = moveWest
		stealKey[commandChars.move_east] = moveEast
		stealKey[commandChars.activate] = disapply

class Wall(Item):
	def __init__(self,xPosition=0,yPosition=0,name="Wall"):
		self.name = name
		super().__init__(displayChars.wall,xPosition,yPosition)

class Pipe(Item):
	def __init__(self,xPosition=0,yPosition=0,name="Wall"):
		self.name = name
		super().__init__(displayChars.pipe,xPosition,yPosition)

class Coal(Item):
	def __init__(self,xPosition=0,yPosition=0,name="Coal"):
		self.name = name
		self.canBurn = True
		super().__init__(displayChars.coal,xPosition,yPosition)
		self.walkable = True

class Door(Item):
	def __init__(self,xPosition=0,yPosition=0,name="Door"):
		super().__init__(displayChars.door_closed,xPosition,yPosition)
		self.name = name
		self.walkable = False

	def apply(self,character):
		if self.walkable:
			self.close()
		else:
			self.open()
	
	def open(self):
		self.walkable = True
		self.display = displayChars.door_opened
		self.room.open = True

	def close(self):
		self.walkable = False
		self.display = displayChars.door_closed
		self.room.open = False

class Pile(Item):
	def __init__(self,xPosition=0,yPosition=0,name="pile",itemType=Coal):
		self.name = name
		self.canBurn = True
		self.type = itemType
		super().__init__(displayChars.pile,xPosition,yPosition)

	def apply(self,character):
		messages.append("Pile used")
		character.inventory.append(self.type())
		character.changed()

class Acid(Item):
	def __init__(self,xPosition=0,yPosition=0,name="pile",itemType=Coal):
		self.name = name
		self.canBurn = True
		self.type = itemType
		super().__init__(displayChars.acid,xPosition,yPosition)

	def apply(self,character):
		messages.append("Pile used")
		character.inventory.append(self.type())
		character.changed()

class Chain(Item):
	def __init__(self,xPosition=0,yPosition=0,name="chain"):
		self.name = name
		super().__init__(displayChars.chains,xPosition,yPosition)
		self.walkable = True

		self.chainedTo = []
		self.fixed = False

	def apply(self,character):
		if not self.fixed:
			if self.room:
				messages.append("TODO")
			else:
				self.fixed = True

				items = []
				for coordinate in [(self.xPosition-1,self.yPosition),(self.xPosition+1,self.yPosition),(self.xPosition,self.yPosition-1),(self.xPosition,self.yPosition+1)]:
					if coordinate in self.terrain.itemByCoordinates:
						items.append(self.terrain.itemByCoordinates[coordinate])

				roomCandidates = []
				bigX = self.xPosition//15
				bigY = self.yPosition//15
				for coordinate in [(bigX,bigY),(bigX-1,bigY),(bigX+1,bigY),(bigX,bigY-1),(bigX,bigY+1)]:
					if coordinate in self.terrain.roomByCoordinates:
						roomCandidates.extend(self.terrain.roomByCoordinates[coordinate])

				rooms = []
				for room in roomCandidates:
					if (room.xPosition*15+room.offsetX == self.xPosition+1) and (self.yPosition > room.yPosition*15+room.offsetY-1 and self.yPosition < room.yPosition*15+room.offsetY+room.sizeY):
						rooms.append(room)
					if (room.xPosition*15+room.offsetX+room.sizeX == self.xPosition) and (self.yPosition > room.yPosition*15+room.offsetY-1 and self.yPosition < room.yPosition*15+room.offsetY+room.sizeY):
						rooms.append(room)
					if (room.yPosition*15+room.offsetY == self.yPosition+1) and (self.xPosition > room.xPosition*15+room.offsetX-1 and self.xPosition < room.xPosition*15+room.offsetX+room.sizeX):
						rooms.append(room)
					if (room.yPosition*15+room.offsetY+room.sizeY == self.yPosition) and (self.xPosition > room.xPosition*15+room.offsetX-1 and self.xPosition < room.xPosition*15+room.offsetX+room.sizeX):
						rooms.append(room)
				messages.append(items)
				messages.append(rooms)

				self.chainedTo = []
				self.chainedTo.extend(items)
				self.chainedTo.extend(rooms)

				for thing in self.chainedTo:
					thing.chainedTo.append(self)
					messages.append(thing.chainedTo)
		else:
			self.fixed = False
			for thing in self.chainedTo:
				if self in thing.chainedTo:
					thing.chainedTo.remove(self)
			self.chainedTo = []
			
class Winch(Item):
	def __init__(self,xPosition=0,yPosition=0,name="winch"):
		self.name = name
		super().__init__(displayChars.winch_inactive,xPosition,yPosition)

	def apply(self,character):
		messages.append("TODO")

