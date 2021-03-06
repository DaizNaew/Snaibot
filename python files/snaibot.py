#!python3

#    snaibot, Python 3-based IRC utility bot
#    Copyright (C) 2013  C.S.Putnam
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.


__author__ = 'C.S.Putnam'
__version__ = '3.7.0'

import pythonircbot
import configparser
import os
import time
import random
import sqlite3
import json
from datetime import timedelta
from urllib.request import urlopen
from xml.dom.minidom import parseString



class snaibot():
    def __init__(self, configfile):
        '''Initializes snaibot object. Requires only the filename for a settings.ini file in the same folder, which it will either read from (if found) or build (if not found). Default settings.ini file will not be sufficient to run bot program and will require configuration.'''
        
        self.config = configparser.ConfigParser()
        self.configfile = configfile
        self.tryBuildConfig(True)
        self.db = self.config['SERVER']['botName']+ '-' + self.config['SERVER']['server'] + '.snaidb'
        
        self.microLog = {}
        self.msgmodulestate = {}
        
        self.msgmoduleref = {'normal links':self.showNormalLinks,
                            'secret links':self.showSecretLinks,
                            'language filter':self.languageKicker,
                            'spam filter':self.spamFilter,
                            'news':self.news,
                            'choose':self.choose,
                            'admin':self.remoteAdmin,
                            'wiki':self.searchWiki,
                            'youtube':self.ytInfo,
                            'calculator':self.calculator,
                            'dice':self.diceRoll}
                            
        self.joinmodulestate = {}
        
        self.joinmoduleref = {'auto mode':self.autoModeSet}
        
        self.partmodulestate = {}
        
        self.partmoduleref = {}
        
        self.bot = pythonircbot.Bot(self.config['SERVER']['botName'], self.config['SERVER']['password'])
        self.bot.connect(self.config['SERVER']['server'], verbose = True)
        
        os.system("title {} on {} in channels: {}".format(self.config['SERVER']['botName'], self.config['SERVER']['server'], self.config['SERVER']['channels'].replace(',', ', ')))
        
        time.sleep(int(self.config['SERVER']['timeout']))
        
        for channel in self.confListParser(self.config['SERVER']['channels']):
            self.bot.joinChannel(channel)
            print(self.bot._channels)
        
        self.microLog = {}
        self.microSwearLog = {}
        
        self.updateModules()
        
        self.bot.addMsgHandler(self.help)
        
        self.bot.waitForDisconnect()

    def checkSQLDatabase(self):
        '''Verifies SQL database exists. If not, creates db and basic table'''
        if not os.path.exists(self.db):
            conn = sqlite3.connect(self.db)
            conn.isolation_level = None
            done = False
            while done != True:
                c = conn.cursor()
                c.execute('''CREATE TABLE chanmode
                (channel text, nick text, mode text)''')
                done = True
            conn.close()
    
    def updateSQLTableCM(self, channel, nick, mode):
        '''Updates SQL table for auto-mode set on join.'''
        self.checkSQLDatabase()
        conn = sqlite3.connect(self.db)
        conn.isolation_level = None
        done = False
        hier = {'v':1, 'h':2, 'o':3}
        while done != True:
            try:
                c = conn.cursor()
                c.execute("SELECT mode FROM chanmode WHERE channel=? AND nick=?",(channel, nick))
                try:
                    test = str(c.fetchall()[0][0])
                    if mode[0] == '-':
                        if mode[1] == test:
                            c.execute("""DELETE FROM chanmode WHERE channel=? AND nick=?""", (channel, nick))
                    elif hier[test] < hier[mode]:
                        c.execute("""UPDATE chanmode 
                        SET mode = ?
                        WHERE channel=? AND nick=?;""",(mode, channel, nick))
                except:
                    if mode[0] in ['v', 'h', 'o']:
                        c.execute("""INSERT INTO chanmode VALUES (?,?,?)""", (channel, nick, mode))
                done = True
            except:
                continue
        conn.close()
    
    def modeSQLCheck(self, channel, nick):
        self.checkSQLDatabase()
        conn = sqlite3.connect(self.db)
        try:
            c = conn.cursor()
            c.execute("SELECT mode FROM chanmode WHERE channel=? AND nick=?",(channel, nick))
            mode = str(c.fetchall()[0][0])
            conn.close()
            return mode
        except:
            conn.close()
            return ''

    def getTestMsg(self, nick, msg):
        '''New function to allow parsing of msg from IRC bot for gameserver. Takes a msg and original sending nick and attempts to parse out a message and nick from a CraftIRC bot. Returns a tuple of (nick, lowermsg, origmsg)'''
        
        try:
            splitnick = msg.split('> ')
            newnick = splitnick[0][1:]
            newmsg = splitnick[1]
        except:
            newnick = nick
            newmsg = msg
        return (newnick, newmsg.lower(), newmsg)
        
        
    def tryBuildConfig(self, firstRun = False):
        '''Attempts to find the config file. Will load if found or build a default if not found.'''
        
        if firstRun == True:
            self.config['SERVER'] = {'botName': 'snaibot',
                                    'server': '',
                                    'channels': '',
                                    'password':'',
                                    'timeout':'10'}
                
            self.config['Modules'] = {'Normal Links':'False',
                                    'Secret Links':'False',
                                    'Language Filter':'False',
                                    'Spam Filter':'False',
                                    'News':'False',
                                    'Choose':'False',
                                    'Admin':'False',
                                    'Wiki':'False',
                                    'Youtube':'False',
                                    'Calculator':'False',
                                    'Auto Mode':'False',
                                    'Dice':'False'}
            
            self.config['KICK/BAN Settings'] = {'Number of repeat messages before kick': '5',
                                           'Number of kicks before channel ban': '5',
                                           'Naughty words':'fuck,cunt,shit,faggot, f4gg0t,f4ggot,f4g,dick,d1ck,d1ckhead,dickhead,cocksucker,pussy,motherfucker,muthafucker,muthafucka,fucker,fucking,fuckin,fuckhead,fuckface'}
            
            self.config['Keyword Links'] = {'source':'https://github.com/snaiperskaya/Snaibot/',
                                       'snaibot':'I was built by snaiperskaya for the good of all mankind...'}
            
            self.config['Secret Links'] = {'secret':'These links will not show up in *commands and will only send via query.'}
            
            self.config['NEWS'] = {'News Item':'*Insert Useful News Here*'}
            
            self.config['Admin'] = {'Admin Nicks':'snaiperskaya'}
        
        if not os.path.exists(self.configfile):
            print('Building Default settings.ini file...')
                      
            with open(self.configfile, 'w') as confile:
                self.config.write(confile)
                confile.close()
            print('Basic settings.ini file built. Please configure and restart bot...')
            
        else:
            self.config.remove_section('Mod Links')
            self.config.remove_section('Keyword Links')
            self.config.remove_section('Secret Links')
            self.config.read(self.configfile)
            if firstRun == True:
                with open(self.configfile, 'w') as confile:
                    self.config.write(confile)
                    confile.close()
            
            
    def confListParser(self, configList):
        '''Micro function to convert a comma-separated String into a usable list. Used for parsing lists entered into settings file.'''
        
        l = configList.replace(' ','').split(',')
        return l
    
    def opsListBuilder(self, channel, level = 'o'):
        '''Scans the channel and returns a set containing all people with elevated privledges in the channel specified. Level allows specification of minimum priledge level to include. Default will be "o" (OPS+), but other options will be "v" (Voice+), "h" (HOPS+), "a" (AOPS+), and "own" (Owner only). Note that some servers only consider some of these (some only use OP and Voice, in which case use of "h" would still only include Voice).'''
        lev = level.lower()
        namelist = set()
        if lev not in ['own','a','o','h','v']:
            lev = 'o' #conditional to force OP+ if level unrecognized
        
        if lev == 'v':
            namelist.update(self.bot.getVoices(channel))
            namelist.update(self.bot.getHops(channel))
            namelist.update(self.bot.getOps(channel))
            namelist.update(self.bot.getAops(channel))
            namelist.update(self.bot.getOwner(channel))
        elif lev == 'h':
            namelist.update(self.bot.getHops(channel))
            namelist.update(self.bot.getOps(channel))
            namelist.update(self.bot.getAops(channel))
            namelist.update(self.bot.getOwner(channel))
        elif lev == 'o':
            namelist.update(self.bot.getOps(channel))
            namelist.update(self.bot.getAops(channel))
            namelist.update(self.bot.getOwner(channel))
        elif lev == 'a':
            namelist.update(self.bot.getAops(channel))
            namelist.update(self.bot.getOwner(channel))
        elif lev == 'own':
            namelist.update(self.bot.getOwner(channel))
        return namelist    
    
    
    def updateModules(self):
        '''NEW TO SNAIBOT 3.0: This will form the backbone of the new modular design. This will update the settings from the config and attempt to turn on or off modules based on those settings. If a module is not properly marked as true or false in the config, it will set it to false automatically.'''
        
        self.tryBuildConfig()
        
        modules = self.config['Modules']
        
        for module in self.msgmoduleref.keys():
            if modules[module].lower() == 'true' or modules[module].lower() == 'false':
                if modules[module].lower() == 'true':
                    try:
                        test = self.msgmodulestate[module]
                    except:
                        self.msgmodulestate[module] = self.bot.addMsgHandler(self.msgmoduleref[module])
                elif modules[module].lower() == 'false':
                    try:
                        self.bot.removeMsgHandler(self.msgmodulestate.pop(module))
                    except:
                        pass
            else:
                self.config['Modules'][module] = 'False'
                with open(self.configfile, 'w') as configfile:
                    self.config.write(configfile)
                    configfile.close()
                    
        for module in self.joinmoduleref.keys():
            if modules[module].lower() == 'true' or modules[module].lower() == 'false':
                if modules[module].lower() == 'true':
                    try:
                        test = self.joinmodulestate[module]
                    except:
                        self.joinmodulestate[module] = self.bot.addJoinHandler(self.joinmoduleref[module])
                elif modules[module].lower() == 'false':
                    try:
                        self.bot.removeJoinHandler(self.joinmodulestate.pop(module))
                    except:
                        pass
            else:
                self.config['Modules'][module] = 'False'
                with open(self.configfile, 'w') as configfile:
                    self.config.write(configfile)
                    configfile.close()
                    
        for module in self.partmoduleref.keys():
            if modules[module].lower() == 'true' or modules[module].lower() == 'false':
                if modules[module].lower() == 'true':
                    try:
                        test = self.partmodulestate[module]
                    except:
                        self.partmodulestate[module] = self.bot.addPartHandler(self.partmoduleref[module])
                elif modules[module].lower() == 'false':
                    try:
                        self.bot.removePartHandler(self.partmodulestate.pop(module))
                    except:
                        pass
            else:
                self.config['Modules'][module] = 'False'
                with open(self.configfile, 'w') as configfile:
                    self.config.write(configfile)
                    configfile.close()

    def stripped(self, x):
        '''Helper function for the language filter. Strips extra-extraneous characters from string x and returns it.'''
        return "".join([i for i in x if ord(i) in range(32, 127)])



    """
    FUNCTIONS FOR MSG HANDLERS. (All must contain arguements for self, msg, channel, nick, client, msgMatch)
    """
    
    
    def echo(self, msg, channel, nick, client, msgMatch):
        '''Simple parser for testing purposes. Will repeat msg with nick and client into chat.'''
        
        msg = msg + " was said by: " + nick + " on " + client
        self.bot.sendMsg(channel, msg)
        
        
    def help(self, msg, channel, nick, client, msgMatch):
        '''Builds help command based on loaded modules. This will always run regardless of other modules loaded.'''
        
        self.updateModules()
        parsemsg = self.getTestMsg(nick, msg)
        nick = parsemsg[0]
        testmsg = parsemsg[1]
        msg = parsemsg[2]
        modules = self.config['Modules']
        if testmsg == '.help' or testmsg == '.commands' or testmsg == '.options' or testmsg == '*commands'or testmsg == '*options' or testmsg == '*help':
            toSend = '*commands, *help'
            
            if modules['News'].lower() == 'true':
                toSend = toSend + ', *news'
                
            if modules['Normal Links'].lower() == 'true':
                for i in self.config.options('Keyword Links'):
                    toSend = toSend + ', *' + i
                    
            if modules['Choose'].lower() == 'true':
                toSend = toSend + ', *choose <opt1;opt2;etc>'
                
            if modules['Wiki'].lower() == 'true':
                toSend = toSend + ', *atlwiki <searchterm>, *fullatlwiki <searchterm>'            
                
            if modules['Calculator'].lower() == 'true':
                toSend = toSend + ', *calc <expression>'
            
            if modules['Dice'].lower() == 'true':
                toSend = toSend + ', *dice <#d#>'
            
            self.bot.sendMsg(channel, nick + ": " + toSend)            
    

    def news(self, msg, channel, nick, client, msgMatch):
        '''Module and reading and editing latest news story. Edit only available to OP+.'''
        
        parsemsg = self.getTestMsg(nick, msg)
        nick = parsemsg[0]
        testmsg = parsemsg[1]
        msg = parsemsg[2]
        if testmsg.split(' ')[0] == '*news':
            try:
                if testmsg.split(' ')[1] == 'edit':
                    tryOPVoice = self.opsListBuilder(channel)
                    if nick in tryOPVoice:
                        news = ''
                        for i in msg.split(' ')[2:]:
                            news = news + ' ' + i
                        self.config['NEWS']['News Item'] = news[1:]
                        with open(self.configfile, 'w') as configfile:
                            self.config.write(configfile)
                            configfile.close()
                        self.bot.sendMsg(channel, 'News Updated in Config!')
                            
                    else:
                        self.bot.sendMsg(channel, self.config['NEWS']['News Item'])
            except:
                self.bot.sendMsg(channel, self.config.get('NEWS','News Item'))        
        

    def showNormalLinks(self, msg, channel, nick, client, msgMatch):
        '''Parses list for links from Keyword Links and returns them to chat if found.'''
        
        parsemsg = self.getTestMsg(nick, msg)
        nick = parsemsg[0]
        testmsg = parsemsg[1]
        msg = parsemsg[2]
        try:
            if testmsg[0] == '*':
                    toSend = self.config['Keyword Links'][testmsg[1:]]
                    self.bot.sendMsg(channel, nick + ": " + toSend)
        except:
            return


    def showSecretLinks(self, msg, channel, nick, client, msgMatch):
        '''Parses list for links from Secret Links and sends them directly to nick in query if found.'''
        
        parsemsg = self.getTestMsg(nick, msg)
        nick = parsemsg[0]
        testmsg = parsemsg[1]
        msg = parsemsg[2]
        try:
            toSend = self.config['Secret Links'][testmsg[1:]]
            self.bot.sendMsg(nick, nick + ": " + toSend)
            self.bot.sendMsg(nick, "Shhh... It's a seekrit!")
        except:
            return        


    def choose(self, msg, channel, nick, client, msgMatch):
        '''Takes a string of arguments from chat that are ;-separated and picks one at random.'''
        
        parsemsg = self.getTestMsg(nick, msg)
        nick = parsemsg[0]
        testmsg = parsemsg[1]
        msg = parsemsg[2]
        if testmsg[:7] == '*choose':
            try:
                toParse = msg[7:].rstrip().lstrip()
                parList = toParse.split(';')
                final = []
                for item in parList:
                    final.append(item.rstrip().lstrip())
                toSend = random.choice(final)
                self.bot.sendMsg(channel, nick + ": I think you should pick...    " + toSend)
            except:
                pass


    def spamFilter(self, msg, channel, nick, client, msgMatch):
        '''Parses chat and weeds out repeat lines from a nick as *spam*. Kicks and bans can be issued by an OP'd bot at intervals specified in config. Will ignore OP or Voiced nicks.'''
        
        if channel.upper() in self.bot._channels:
            
            tryOPVoice = self.opsListBuilder(channel,'v')
            tryOP = self.opsListBuilder(channel, 'h')
            
            if self.bot._nick in tryOP:
            
                if nick not in tryOPVoice:
                    
                    msg = msg.lower()
                
                    numTilKick = int(self.config['KICK/BAN Settings']['number of repeat messages before kick']) - 1
                    numTilBan = int(self.config['KICK/BAN Settings']['number of kicks before channel ban'])
                    
                    if channel not in self.microLog:
                        self.microLog[channel] = {client:[msg, 1, 0]}
                        
                    elif client not in self.microLog[channel]:
                        self.microLog[channel][client] = [msg, 1, 0]
                        
                    elif self.microLog[channel][client][0] == msg and self.microLog[channel][client][1] >= numTilKick and self.microLog[channel][client][2] >= (numTilBan - 1):
                        self.bot.banUser(channel, client)
                        self.bot.kickUser(channel, nick, 'Spamming (bot)')
                        self.microLog[channel][client][1] = numTilKick - 1
                        self.microLog[channel][client][2] = 0
                        
                    elif self.microLog[channel][client][0] == msg and self.microLog[channel][client][1] >= numTilKick:
                        self.bot.kickUser(channel, nick, 'Spamming (bot)')
                        self.microLog[channel][client][1] = numTilKick - 1
                        self.microLog[channel][client][2] = self.microLog[channel][client][2] + 1
                        
                    elif self.microLog[channel][client][0] == msg:
                        self.microLog[channel][client][1] = self.microLog[channel][client][1] + 1
                        
                    else:
                        self.microLog[channel][client][0] = msg
                        self.microLog[channel][client][1] = 1


    def languageKicker(self, msg, channel, nick, client, msgMatch):
        '''Module to parse language in chat and log usage of "bad words" (as defined in config). Kicks and Bans based on config file.'''
        
        if channel.upper() in self.bot._channels:
            
            tryOPVoice = self.opsListBuilder(channel,'v')
            tryOP = self.opsListBuilder(channel, 'h')
            
            if self.bot._nick in tryOP:            
            
                if nick not in tryOPVoice:    
                    
                    msg = msg.lower()
                    msg = self.stripped(msg)
                    msg = msg.strip('.,!?/@#$^:;*&()\\ -_')
                    
                    words = self.confListParser(self.config['KICK/BAN Settings']['Naughty words'])
                    #msglist = msg.split()
                    
                    numTilKick = 1
                    numTilBan = int(self.config['KICK/BAN Settings']['number of kicks before channel ban'])    
                    
                    for i in words:
                        if i in msg:
                            if channel not in self.microSwearLog:
                                self.microSwearLog[channel] = {client:[1, 0]}
                                self.bot.sendMsg(channel, nick + ": Please watch your language...")
                                
                            elif client not in self.microSwearLog[channel]:
                                self.microSwearLog[channel][client] = [1, 0]
                                self.bot.sendMsg(channel, nick + ": Please watch your language...")
                                
                            elif self.microSwearLog[channel][client][0] >= numTilKick and self.microSwearLog[channel][client][1] >= numTilBan:
                                self.bot.banUser(channel, client)
                                self.bot.kickUser(channel, nick, 'Swearing (bot)')
                                self.microSwearLog[channel][client][0] = numTilKick - 1
                                self.microSwearLog[channel][client][1] = 0
                                
                            elif self.microSwearLog[channel][client][0] >= numTilKick:
                                self.bot.sendMsg(channel, nick + ": Please watch your language...")
                                self.bot.kickUser(channel, nick, 'Swearing (bot)')
                                self.microSwearLog[channel][client][0] = numTilKick - 1
                                self.microSwearLog[channel][client][1] = self.microSwearLog[channel][client][1] + 1
                                
                            else:
                                self.microSwearLog[channel][client][0] = self.microSwearLog[channel][client][0] + 1
                                self.bot.sendMsg(channel, nick + ": Please watch your language...")
                                
                            break


    def remoteAdmin(self, msg, channel, nick, client, msgMatch):
        '''Module to allow command-based administration via chat from those either registered as admins in the config or those with OP+'''
        
        parsemsg = self.getTestMsg(nick, msg)
        nick = parsemsg[0]
        testmsg = parsemsg[1]
        msg = parsemsg[2]
        configAdmin = self.confListParser(self.config['Admin']['Admin Nicks'])
        try:
            if channel.upper() in self.bot._channels:
                chanOPList = self.opsListBuilder(channel)
                if self.bot._nick in chanOPList:
                    if nick in configAdmin or nick in chanOPList:
                        if testmsg == '*admin':
                            self.bot.sendMsg(nick, 'The following administrative commands are available in {}: Set modes (*v <nick>, *h <nick>, *o <nick>), Un-set Modes (*dv <nick>, *dh <nick>, *do <nick>), *kick <nick>, *join <channel>, *leave <channel>, *identify'.format(channel))     
                        elif testmsg == '*identify':
                            self.bot.verifyNick(self.config['SERVER']['password'])
                        elif testmsg.split()[0] == '*join':
                            chan = testmsg.split()[1]
                            if chan[0] == '#':
                                self.bot.joinChannel(chan)
                            else:
                                self.bot.sendMsg(nick, 'Not a valid channel...')
                        elif testmsg.split()[0] == '*leave':
                            chan = testmsg.split()[1]
                            if chan[0] == '#':
                                self.bot.partChannel(chan)
                            else:
                                self.bot.sendMsg(nick, 'Not a valid channel...')
                        else:
                            testmessage = testmsg.split()
                            comm = testmessage.pop(0)
                            for nik in testmessage:
                                if comm == '*kick':
                                    self.bot.kickUser(channel, nik, 'Requested by {}'.format(nick))
                                elif comm == '*v':
                                    self.bot.setMode(channel, nik, 'v')
                                    self.updateSQLTableCM(channel, nik, 'v')
                                elif comm == '*h':
                                    self.bot.setMode(channel, nik, 'h')
                                    self.updateSQLTableCM(channel, nik, 'h')
                                elif comm == '*o':
                                    self.bot.setMode(channel, nik, 'o')
                                    self.updateSQLTableCM(channel, nik, 'o')
                                elif comm == '*dv':
                                    self.bot.unsetMode(channel, nik, 'v')
                                    self.updateSQLTableCM(channel, nik, '-v')
                                elif comm == '*dh':
                                    self.bot.unsetMode(channel, nik, 'h')
                                    self.updateSQLTableCM(channel, nik, '-h')
                                elif comm == '*do':
                                    self.bot.unsetMode(channel, nik, 'o')
                                    self.updateSQLTableCM(channel, nik, '-o')
                            
                else:
                    if testmsg == '*admin':
                        self.bot.sendMsg(nick, 'Bot not OPed in {}! The following administrative commands are available: *join <channel>, *leave <channel>, *identify'.format(channel))
                    elif testmsg == '*identify':
                        self.bot.verifyNick(self.config['SERVER']['password'])
                    elif testmsg.split()[0] == '*join':
                        chan = testmsg.split()[1]
                        if chan[0] == '#':
                            self.bot.joinChannel(chan)
                        else:
                            self.bot.sendMsg(nick, 'Not a valid channel...')
                    elif testmsg.split()[0] == '*leave':
                        chan = testmsg.split()[1]
                        if chan[0] == '#':
                            self.bot.partChannel(chan)
                        else:
                            self.bot.sendMsg(nick, 'Not a valid channel...')                 
            
            else:
                if nick in configAdmin:
                    if testmsg == '*admin':
                        self.bot.sendMsg(nick, 'The following administrative commands are available: *join <channel>, *leave <channel>, *identify')
                    elif testmsg == '*identify':
                        self.bot.verifyNick(self.config['SERVER']['password'])
                    elif testmsg.split()[0] == '*join':
                        chan = testmsg.split()[1]
                        if chan[0] == '#':
                            self.bot.joinChannel(chan)
                        else:
                            self.bot.sendMsg(nick, 'Not a valid channel...')
                    elif testmsg.split()[0] == '*leave':
                        chan = testmsg.split()[1]
                        if chan[0] == '#':
                            self.bot.partChannel(chan)
                        else:
                            self.bot.sendMsg(nick, 'Not a valid channel...')
                            
        except:
            pass

    
    def searchWiki(self, msg, channel, nick, client, msgMatch):
        '''Module allows for searching ATLWiki.net for articles. Bot is largely used for a Minecraft Community, so this was extremely helpful as a resource.'''
        try:
            parsemsg = self.getTestMsg(nick, msg)
            nick = parsemsg[0]
            testmsg = parsemsg[1]
            msg = parsemsg[2]
            if testmsg[:12] == '*fullatlwiki':
                toParse = msg[12:].rstrip().lstrip()
                toParse = toParse.replace('\'', '%27')
                parList = toParse.split(' ')
                if parList[0] != '':
                    term1 = parList.pop(0)
                    term1 = term1[:1].upper() + term1[1:]
                    searchTerm = term1
                    instantURL = term1
                    for i in parList:
                        term = i
                        term = term[:1].upper() + term[1:]
                        searchTerm = searchTerm + '%20' + term
                    baseurl = "http://atlwiki.net/api.php?format=json&action=query&list=search&srsearch={}&srwhat=title"
                    qurl = baseurl.format(searchTerm)
                    openurl = urlopen(qurl).read()
                    jsread = json.loads(openurl.decode('utf-8'))
                    numTitles = len(jsread['query']['search'])
                    if numTitles > 0:
                        self.bot.sendMsg(nick, "Full search results for " + searchTerm.replace('%20',' '))
                        for i in jsread['query']['search']:
                            self.bot.sendMsg(nick, i['title'] + '  -  http://atlwiki.net/{}'.format(i['title'].replace(' ', '_')))
                    else:
                        self.bot.sendMsg(channel, nick + ': No results found. If this page should exist, please consider contributing to the wiki! http://atlwiki.net')                    
                else:
                    self.bot.sendMsg(channel, nick + ": http://atlwiki.net")                    
    
            elif testmsg[:8] == '*atlwiki':
                toParse = msg[8:].rstrip().lstrip()
                toParse = toParse.replace('\'', '%27')
                parList = toParse.split(' ')
                if parList[0] != '':
                    term1 = parList.pop(0)
                    term1 = term1[:1].upper() + term1[1:]
                    searchTerm = term1
                    instantURL = term1
                    for i in parList:
                        term = i
                        term = term[:1].upper() + term[1:]
                        searchTerm = searchTerm + '%20' + term
                    baseurl = "http://atlwiki.net/api.php?format=json&action=query&list=search&srsearch={}&srwhat=title"
                    qurl = baseurl.format(searchTerm)
                    openurl = urlopen(qurl).read()
                    jsread = json.loads(openurl.decode('utf-8'))
                    numTitles = len(jsread['query']['search'])
                    if numTitles > 0:
                        eMatch = False
                        for i in jsread['query']['search']:
                            if i['title'].lower() == toParse.strip().lower():
                                self.bot.sendMsg(channel, nick + ": Exact Match Found! " + i['title'] + '  -  http://atlwiki.net/{}'.format(i['title'].replace(' ', '_')))
                                eMatch = True
                                break
                        if not eMatch:
                            topres = jsread['query']['search'][0]
                            self.bot.sendMsg(channel, nick + ": " + topres['title'] + '  -  http://atlwiki.net/{}'.format(topres['title'].replace(' ', '_')))
                    else:
                        self.bot.sendMsg(channel, nick + ': No results found. If this page should exist, please consider contributing to the wiki! http://atlwiki.net')                    
                else:
                    self.bot.sendMsg(channel, nick + ": http://atlwiki.net")
        except:
            print('Wiki Module Error')
   
    
    def ytInfo(self, msg, channel, nick, client, msgMatch):
        '''Module to parse incoming messages for YouTube links and attempt to parse video info and reply to channel.'''
        parsemsg = self.getTestMsg(nick, msg)
        nick = parsemsg[0]
        testmsg = parsemsg[1].split(' ')
        msg = parsemsg[2].split(' ')
        
        for i in range(len(msg)):
            if testmsg[i].count('youtube.com') > 0 or testmsg[i].count('youtu.be') > 0:
                vid = msg[i]
                try:
                    vidid = vid.split('.be/')[1]
                except:
                    try:
                        vidid = vid.split('v=')[1].split('&')[0]
                    except:
                        return
                
                # Try to open gdata URL
                try:
                    url = 'https://gdata.youtube.com/feeds/api/videos/{0}'.format(vidid)
                    s = urlopen(url).read()
                    d = parseString(s)
                except:
                    return
                    
                # Get video length
                try:
                    e = d.getElementsByTagName('yt:duration')[0]
                    a = e.attributes['seconds']
                    v = int(a.value)
                    time = timedelta(seconds=v)
                except:
                    time = 'N/A'
                
                # Get view count
                try:
                    e2 = d.getElementsByTagName('yt:statistics')[0]
                    views = int(e2.attributes['viewCount'].value)
                except:
                    views = 'N/A'
                    
                # Get video author
                try:
                    video_title = d.getElementsByTagName('title')[0].firstChild.nodeValue
                    video_title = self.stripped(video_title)
                except:
                    video_title = 'Error retrieving title'
                    
                # Get video author
                try:
                    author = d.getElementsByTagName('author')[0].getElementsByTagName('name')[0].firstChild.nodeValue
                    author = self.stripped(author)
                except:
                    author = 'Error retrieving author'
                    
                # Get video rating as percent
                try:
                    e3 = d.getElementsByTagName('gd:rating')[0]
                    rating = float(e3.attributes['average'].value)
                    rateperc = (rating / 5.0) * 100
                    ratestr = '{0:.2F}%'.format(rateperc)
                except:
                    ratestr = 'N/A'
                self.bot.sendMsg(channel,'"{}" by {} ( Views: {}   Rating: {}   Duration: {} )'.format(video_title, author, views, ratestr, time))


    def calculator(self, msg, channel, nick, client, msgMatch):
        '''Basic Calculator with minor safeguards in place to reduce abuse. Uses the format *calc <expression>'''
        parsemsg = self.getTestMsg(nick, msg)
        nick = parsemsg[0]
        testmsg = parsemsg[1]
        
        if testmsg[:5] == '*calc':
            try:
                toParse = testmsg[5:].strip(' ')
                expr = toParse.replace('^', '**')
                valid = True
                for i in expr:
                    if not i.isnumeric() and i not in ['+','-','(',')','*','/',' ','.']:
                        valid = False
                if expr.count('**') < 3 and valid == True:
                    num = eval(expr)
                    strnum = str(num)
                    if len(strnum) > 30:
                        strnum = strnum[:30] + '... char limit exceeded ...'
                    self.bot.sendMsg(channel, nick + ': The answer should be ' + strnum)
                else:
                    self.bot.sendMsg(channel, nick + ': ERROR - Formula too complex') 
            except:
                self.bot.sendMsg(channel, nick + ': ERROR - Please check your formula...')
    
    
    def autoModeSet(self, channel, nick, client):
        '''Module to automatically promote users joining a channel to their assigned level. This can only be done on user snaibot recognizes in its database and only levels at or below its own.'''
        mode = self.modeSQLCheck(channel, nick.lower())
        if mode in ['v', 'h', 'o']:
            self.bot.setMode(channel, nick, mode)
   
    
    def diceRoll(self, msg, channel, nick, client, msgMatch):
        '''A simple DnD-esque dice roll module using the #d# notation. The format is *dice <number of dice to roll>d<sides per die>. Output will include the total as well as a list of all dice rolled up to character limit of channel.'''
        parsemsg = self.getTestMsg(nick, msg)
        nick = parsemsg[0]
        testmsg = parsemsg[1]
        
        if testmsg[:5] == '*dice':
            test = testmsg[5:].lower().strip(' ').split('d')
            if len(test) == 2:
                if test[0].isdigit() and test[1].isdigit():
                    numDice = int(test[0])
                    numSides = int(test[1])
                    roll = 0
                    rolls = []
                    if numDice > 0 and numSides > 1:
                        for i in range(1, numDice + 1):
                            d = random.randint(1, numSides)
                            roll = roll + d
                            rolls.append(d)
                        self.bot.sendMsg(channel, nick + ': Total value rolled was {} - Dice Rolled: {}'.format(roll, rolls))
                    else:
                        self.bot.sendMsg(channel, nick + ': Error: Invalid numbers. Please try again.')                    
                else:
                    self.bot.sendMsg(channel, nick + ': Error: Non Digit Dice Values (#d# required)')
            else:
                self.bot.sendMsg(channel, nick + ': Error: Invalid Format (#d# required)')