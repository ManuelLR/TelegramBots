#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import urllib
import urllib2
import time
from pyquery import PyQuery
import telegram
import string

import codecs
import sys

import sqlite3
from datetime import datetime


TOKEN = None
conn = sqlite3.connect('payTogetherDB.db')


with open('token', 'rb') as token_file:
    TOKEN = str(token_file.readline()).replace('\n', '')

# Create bot object
bot = telegram.Bot(TOKEN)




class dataBase():
	
    def __init__(self):
        print("completar __init__ en class dataBase()")
        self.conn = sqlite3.connect('payTogetherDB.db')

    def __secInit(self):
        c = conn.cursor()

        # Toda la info para las consultas: https://sqlite.org/lang_createtable.html
        # Probar las consultas: http://stackoverflow.com/questions/8272534/testing-sqlite-code-online

        c.execute('CREATE TABLE IF NOT EXISTS userTable(userId INTEGER NOT NULL UNIQUE, userName TEXT NOT NULL, privateConversationID integer NOT NULL, owe REAL DEFAULT 0)')
        # Siempre que se inserte o modifique algo en la expensesTable o en la relationTable se debe actualizar el campo "owe"

        c.execute('CREATE TABLE IF NOT EXISTS expensesTable(id INTEGER PRIMARY KEY, paidBy INTEGER NOT NULL REFERENCES userTable(userId), insertBy integer NOT NULL REFERENCES userTable(userId), amount REAL DEFAULT 0, description TEXT, datePayment TEXT, dateInsertion TEXT NOT NULL)')


        c.execute('CREATE TABLE IF NOT EXISTS relationTable(expenseID INTEGER NOT NULL REFERENCES expensesTable(id), userId INTEGER NOT NULL REFERENCES userTable(userId), percentInfluenced REAL DEFAULT 0,  PRIMARY KEY (expenseID, userId))')

        conn.commit()
        c.close()

	
    def __createUser(self, userId, userName, privateConversationID):
        c = self.conn.cursor()
        userName = "@" + userName

        c.execute('INSERT INTO userTable (userId, userName, privateConversationID) VALUES(?, ?, ?)', (userId, userName, privateConversationID)
        self.conn.commit()
        c.close()
	
	def __createExpense(self, paidBy, insertBy, amount, description, datePayment):
        c = conn.cursor()
        dateInsertion = "Today"
		
        # Antes de insertar se debe comprobar que el paidBy y el insertBy existe en userTable

		c.execute('INSERT INTO expensesTable (paidBy, insertBy, amount, description, datePayment, dateInsertion) VALUES(?, ?, ?, ?, ?, ?)', (paidBy, insertBy, amount, description, datePayment, dateInsertion)
		
		conn.commit()
		c.close()
	
	def __createRelation(self, expenseID, userId, percentInfluenced):
        c = conn.cursor()
		
        c.execute('INSERT INTO relationTable (expenseID, userId, percentInfluenced) VALUES(?, ?, ?)', (expenseID, userId, percentInfluenced)
		
		conn.commit()
		c.close()
		
	def __getUserRow(self, userId):
        c = conn.cursor()
		
        h = c.execute('SELECT * FROM userTable WHERE userId = ?', userId).fetchall()
		
        return h
		
    def __existUser(self, userId, userName):
        user = self.__getUserRow(userId)
        if len(user) != 0:
            print("el método existUser debe comprobar si el nombre de usuario ha variado")
			return True
		else:
			return False

def main():

    secInit()

    # UTF-8 console stuff thingies
    UTF8Writer = codecs.getwriter('utf8')
    sys.stdout = UTF8Writer(sys.stdout)

    # Init logging
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Discard old updates, sent before the bot was started
    num_discarded = 0


    # Get last update ID
    LAST_UPDATE_ID = None

    while True:
        updates = bot.getUpdates(LAST_UPDATE_ID, timeout=1, network_delay=2.0)
        if updates is not None and len(updates) > 0:
            num_discarded = num_discarded + len(updates)
            LAST_UPDATE_ID = updates[-1].update_id + 1
        else:
            break

    print("Discarded {} old updates".format(num_discarded))

    # Main loop
    print('Working...')
    while True:
        updates = getUpdates(LAST_UPDATE_ID)

        for update in updates:
            message = update.message
            actText = message.text
            actType = message.chat.type
            chat_id = message.chat.id
            update_id = update.update_id
            actUser = message.from_user.username

            send_text = None

            periodicCheck()

            if checkTypeAndTextStart(aText= actText, cText='/who', aType=actType, cType='private'):
                who = getWho()

                if len(who) == 0:
                    send_text = u"Parece que no hay nadie... {}".format(telegram.Emoji.DISAPPOINTED_FACE.decode('utf-8'))
                else:
                    send_text = showList(u"Miembros en SUGUS:", who)

            if checkTypeAndTextStart(aText= actText, cText='/como', aType=actType, cType='private'):
                send_text = addTo(u'comida', actUser)

            if checkTypeAndTextStart(aText= actText, cText='/nocomo', aType=actType, cType='private'):
                send_text = removeFromEvent(u'comida', actUser)

            if checkTypeAndTextStart(aText= actText, cText='/quiencome', aType=actType, cType='private'):
                if len(findByEvent('comida')) != 0:
                    send_text = showList(u"Hoy come en Sugus:", findByEvent('comida'), [2, 0])
                else:
                    send_text = u'De momento nadie come en Sugus'

            if checkTypeAndTextStart(aText= actText, cText='/testingjoin', aType=actType, cType='private'):
                rtext = actText.replace('/testingjoin','').replace(' ','')
                if not rtext:
                    send_text = u"Elige un evento /testingparticipants"
                else:
                    addTo(rtext, actUser)

            if checkTypeAndTextStart(aText= actText, cText='/testingparticipants', aType=actType, cType='private'):
                rtext = actText.replace('/testingparticipants','').replace(' ','')
                if not rtext:
                    send_text = showList(u"Elige una de las listas:", listEvents(), [0])
                else:
                    if len(findByEvent(rtext)) == 0:
                        send_text = u"No hay nadie en {}".format(rtext)
                    else:
                        send_text = showList(u"Participantes en {}:".format(rtext), findByEvent(rtext), [2, 0])

            if checkTypeAndTextStart(aText= actText, cText='/testingdisjoin', aType=actType, cType='private'):
                rtext = actText.replace('/testingdisjoin','').replace(' ','')
                send_text = removeFromEvent(rtext, actUser)

            if checkTypeAndTextStart(aText= actText, cText='/testinghelp', aType=actType, cType='private'): #, aType=actType, cType='private'):
                send_text = helpTesting()

            if checkTypeAndTextStart(aText= actText, cText='/testingempty', aType=actType, cType='private'):
                rtext = actText.replace('/testingempty','').replace(' ','')
                if rtext != u'comida':
                    send_text = emptyEvent(rtext, actUser)
                else:
                    send_text = u'No soy tonto, no voy a dejar que borres quien come hoy'

            if send_text != None:
                sendMessages(send_text, chat_id)
            elif checkTypeAndTextStart(aType=actType, cType='private'):
                sendMessages(help(), chat_id)
            else:
                print("Mensaje enviado y no publicado por: " + actUser )

            LAST_UPDATE_ID = update_id + 1


def checkTypeAndTextStart(aText = None, cText = None, aType = None, cType = None, aUName = None, cUName = None):

    result = True

    if cType != None:
        result = result and aType == cType
    if cUName != None:
        if aUName in cUName:
            result = result and False
    if cText != None:
        result = result and aText.startswith(cText)

    return result

def showList(header, contains, positions = None):
    result = u'{}'.format(header)
    if contains != None:
        for a in contains:
            result = u'{}\n {}'.format(result, telegram.Emoji.SMALL_BLUE_DIAMOND.decode('utf-8'))
            if positions != None:
                for i in positions:
                    result = u'{} {} '.format(result, a[i])
            else:
                result = u'{} {} '.format(result, a[:])
    return result

def periodicCheck():

    ## Remove periodic comida
    actDate = datetime.now().strftime("%d-%m-%y")
    actComida = findByEvent('comida')

    for a in actComida:
        if a[0] != actDate:
            removeFromEvent('comida', a[2])

def help():
    header = "Elige una de las opciones: "
    contain = [['/help', 'Ayuda'], ['/spendAdd','Añadir un gasto'], ['/owe','¿Cuanto debo?']]
    contain = contain + [['/sendExpenses', 'Envía los gastos'], ['/quiencome', '¿Quien come aquí?']]
    contain = contain +[['/advancedhelp', 'Ayuda avanzada']]
    return showList(header, contain, [0, 1])

def helpTesting():
    header = "Elige una de las opciones: "
    contain = [['/advancedhelp', 'Ayuda avanzada'], ['/spendDel','Eliminar un gasto']]
    contain = contain + [['/oweRefresh','Recalcula lo que debo'], ['/?¿', '?¿']]
    contain = contain + [['/testingempty', 'Vaciar una lista']]
    return showList(header, contain, [0, 1])

def getUpdates(LAST_UPDATE_ID, timeout = 30):
    while True:
        try:
            updates = bot.getUpdates(LAST_UPDATE_ID, timeout=timeout, network_delay=2.0)
        except telegram.TelegramError as error:
            if error.message == "Timed out":
                print("Timed out! Retrying...")
            elif error.message == "Bad Gateway":
                    print("Bad gateway. Retrying...")
            else:
                raise
        except urllib2.URLError as error:
            print("URLError! Retrying...")
            time.sleep(1)
        except:
            print('Ignore errors')
            pass
        else:
            break
    return updates

def sendMessages(send_text, chat_id):
    while True:
        try:
            bot.sendMessage(chat_id=chat_id, text=send_text)
            print("Mensaje enviado a id: " + chat_id)
            break
        except telegram.TelegramError as error:
            if error.message == "Timed out":
                print("Timed out! Retrying...")
            else:
                print(error)
        except urllib2.URLError as error:
            print("URLError! Retrying to send message...")
            time.sleep(1)
        except:
            print('Ignore exception')
            pass

def addTo(event, name):

    if len(event) != 0 and len(event) != 0:
        c = conn.cursor()
        date = datetime.now().strftime("%d-%m-%y")

        c.execute('insert into eventTable values(?, ?, ?)', (date, event.replace(" ",""), u'@'+name.replace(" ", "")))
        conn.commit()
        c.close()
        result = name + ' añadido a ' + event

    elif len(name) != 0:
        result = "No tienes nombre de usuario o alias. \n Es necesario para poder añadirte a un evento"
    else:
        result = "No se ha podido añadir el usuario @" + name+ " a la lista " + name

    return result

def findByEvent(event):
    c = conn.cursor()

    result = c.execute('select * from eventTable where event=?', (event.replace(" ",""),)).fetchall()

    c.close()

    return result

def removeFromEvent(event, name):

    if '@' + name in findByEvent(event):
        c = conn.cursor()

        c.execute('delete from eventTable where event=? and name=?', (event, u'@' + name))
        conn.commit()

        c.close()
        result = "Has sido eliminado del evento " + event
    else:
        result = "No estás en el evento " + event

    return result

def emptyEvent(event, name):

    if u'@' + name in findByEvent(event):
        c = conn.cursor()

        c.execute('delete from eventTable where event=?', (event))

        result = "El evento " + event +" ha sido eliminado"
        conn.commit()

        c.close()
    else:
        result = 'El evento ' + event + ' NO ha sido eliminado'

    return result

def listEvents():
    c = conn.cursor()

    h = c.execute('select distinct event from eventTable')

    return h

if __name__ == '__main__':
    main()