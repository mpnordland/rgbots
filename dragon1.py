import rg
import random
import os
from collections import defaultdict

def intCmp(int1, int2):
    if int1 == int2:
        return 0
    elif int1 < int2:
        return -1
    else:
        return 1

def sortY(loc1, loc2):
    return intCmp(loc1[1], loc2[1])

def sortX(loc1, loc2):
    return intCmp(loc1[0], loc2[0])

def attack(loc):
    return ['attack', loc]

def guard():
    return ['guard']

def move(loc):
    return ['move', loc]

def moveToward(start, goal):
    return move(rg.toward(start, goal))

def findCenter(locs):
    locsY = sorted(locs, sortY)
    locsX = sorted(locs, sortX)
    x = locsX[0][0]+((locsX[-1][0]-locsX[0][0])/2)
    y = locsY[0][0]+((locsY[-1][0]-locsY[0][0])/2)
    return x, y

class StateTracker:
    def __init__(self):
        self.states = defaultdict(dict)
        self.groups = {}
        self.gameState = None
        self.groupInc = 0
        self.playerId = None

    def setPlayerId(self, playerId):
        if self.playerId == None:
            self.playerId = playerId

    def setBotProps(self, botId, propDict):
        print 'setting props for', botId, propDict
        self.states[botId] = propDict
        self.updateGroupState()
        
    def getBotProps(self, botId):
        return self.states[botId]
    
    def getGroupId(self):
        ret = self.groupInc
        self.groupInc += 1
        return ret

    def updateGameState(self, newState):
        self.gameState = newState
        self.updateGroupState()

    #group bot1 with bot2 if bot2 has no group
    #a new group is created. otherwise
    #bot1 is added to bot2's group
    def groupWith(self, bot1, bot2):
        group = self.states[bot2].get('group', None)
        if group is None:
            group_id = self.getGroupId()
            self.groups[group_id] = [bot1, bot2]
            self.states[bot2]['group'] = group_id
            self.states[bot1]['group'] = group_id
        else:
            self.states[bot1]['group'] = group
            self.groups[group].append(bot1)
        self.updateGroupState()

    def updateGroupState(self):
        for _, group in self.groups.items():
            gCenter = findCenter([self.states[bot]['loc'] for bot in group])
            for loc, bot in self.gameState['robots'].items():
                if bot['player_id'] != self.playerId:
                    eDist = rg.dist(loc, gCenter)
                    if 2 < eDist <= 8:
                        self.setGroupOrder(group, lambda rbot, loc=loc: moveToward(rbot['loc'], loc))
                    elif eDist <= 1:
                        self.setGroupOrder(group, lambda bot, loc=loc: attack(loc))
                    else:
                        self.setGroupOrder(group, lambda bot: guard())
                else:
                    self.setGroupOrder(group, lambda bot: guard())

    def setGroupOrder(self, group, order):
        for bot in group:
            self.states[bot]['order'] = order(self.getBotProps(bot))
                
    
state = StateTracker()

class Robot:
    def setup(self, game):
        global state
        props = state.getBotProps(self.robot_id)
        if not props.get("setup", False):
            props['setup'] = True
            props['rallyPoint'] = self.makeRallyPoint(game['robots'])
            state.setPlayerId(self.player_id)
            self.updateState(props, game)
        return props
    
    def updateState(self, props, game=None):
        global state
        props['loc'] = self.location
        props['hp'] = self.hp
        state.setBotProps(self.robot_id, props)
        if game is not None:
            state.updateGameState(game)

    def isValidLoc(self, loc):
        validLocs = rg.locs_around(self.location, filter_out=("invalid", "obstacle", "spawn"))
        return loc in validLocs

    def getNearFriends(self, bots):
        nearFriends = []
        for loc, bot in bots.items():
            if self.isFriend(bot) and loc != self.location:
                if rg.dist(self.location, loc) <=1:
                    nearFriends.append((loc, bot))
        return nearFriends

    def isFriend(self, bot):
        return bot['player_id'] == self.player_id

    def getFirstEnemyLoc(self, bots):
        enemies = []
        for loc, bot in bots.items():
            if bot['player_id'] != self.player_id:
                enemies.append(loc)
        enemies = sorted(enemies, sortX)
        return enemies[0]

    def getFirstFriendLoc(self, bots):
        for loc, bot in bots.items():
            if bot['player_id'] == self.player_id and bot['robot_id'] != self.robot_id:
                return loc
        
    def makeRallyPoint(self, bots):
        #avgX,avgY,botCount = 0, 0, 0
        #for loc, bot in bots.items():
        #    if self.isFriend(bot):
        #        avgX += loc[0]
        #        avgY += loc[1]
        #        botCount += 1
        #return (avgX/botCount, avgY/botCount)
        botList = []
        for loc, bot in bots.items():
            if self.isFriend(bot):
                botList.append(loc) 
        botList = sorted(botList, sortY)
        y = botList[0][1] + (botList[-1][1] - botList[0][1])/2
        botList = sorted(botList, sortX)
        x = botList[0][0] + (botList[-1][0] - botList[0][0])/2
        return x, y

    def act(self, game):
        global state
        self.props = self.setup(game)
        if self.props.get('group', None) is not None:
            return self.props['order']
        for loc, bot in game['robots'].items():
            if not self.isFriend(bot):
                if rg.dist(self.location, loc) <= 1:
                    return attack(loc)
            else:
                if rg.wdist(self.location, loc) <=1 and bot['robot_id'] != self.robot_id:
                    state.groupWith(self.robot_id, bot['robot_id'])

        self.updateState(self.props, game)
        try:
            return move(rg.toward(self.location, self.props['rallyPoint'])) 
        except KeyError:
            return guard()

