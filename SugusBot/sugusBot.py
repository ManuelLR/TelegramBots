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
conn = sqlite3.connect('sugusBotDB.db')


with open('token', 'rb') as token_file:
    TOKEN = str(token_file.readline()).replace('\n', '')

# Create bot object
bot = telegram.Bot(TOKEN)


def secInit():
    c = conn.cursor()
    c.execute('create table if not exists eventTable(date text, event text, name text, UNIQUE(event, name) ON CONFLICT REPLACE)')
    conn.commit()
    c.close()

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
                    send_text = show(u"Miembros en SUGUS:", who)

            if checkTypeAndTextStart(aText= actText, cText='/como', aType=actType, cType='private'):
                send_text = addTo(u'comida', actUser)

            if checkTypeAndTextStart(aText= actText, cText='/nocomo', aType=actType, cType='private'):
                send_text = removeFromEvent(u'comida', actUser)

            if checkTypeAndTextStart(aText= actText, cText='/quiencome', aType=actType, cType='private'):
                if len(findByEvent('comida')) != 0:
                    send_text = show(u"Hoy come en Sugus:", findByEvent('comida'), [2, 0])
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
                    send_text = show(u"Elige una de las listas:", listEvents(), [0])
                else:
                    if len(findByEvent(rtext)) == 0:
                        send_text = u"No hay nadie en {}".format(rtext)
                    else:
                        send_text = show(u"Participantes en {}:".format(rtext), findByEvent(rtext), [2, 0])

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
                print(u"Mensaje enviado y no publicado por:{}".format(actUser))

            LAST_UPDATE_ID = update_id + 1


def checkTypeAndTextStart(aText = None, aUName = None, cText = None, aType = None, cType = None, cUName = None):

    result = True

    if cType != None:
        result = result and aType == cType
    if cUName != None:
        if aUName in cUName:
            result = result and False
    if cText != None:
        result = result and aText.startswith(cText)

    return result

def show(header, contains , positions = None):
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
    header = u"Elige una de las opciones: "
    contain = [['/help', 'Ayuda'], ['/who',u'¿Quien hay en Sugus?'], ['/como',u'Yo como aquí']]
    contain = contain + [['/nocomo',u'Yo no como aquí'], ['/quiencome', u'¿Quien come aquí?']]
    contain = contain +[['/testinghelp', 'Ayuda testing']]
    return show(header, contain, [0,1])

def helpTesting():
    header = u"Elige una de las opciones: "
    contain = [['/testinghelp', 'Ayuda testing'], ['/testingjoin',u'Apuntarse a un evento']]
    contain = contain + [['/testingdisjoin',u'Desapuntarse de un evento'], ['/testingparticipants', u'Listar una lista']]
    contain = contain + [['/testingempty', u'Vaciar una lista']]
    return show(header, contain, [0,1])

def getUpdates(LAST_UPDATE_ID, timeout = 30):
    while True:
        try:
            updates = bot.getUpdates(LAST_UPDATE_ID, timeout=timeout, network_delay=2.0)
        except telegram.TelegramError as error:
            if error.message == "Timed out":
                print(u"Timed out! Retrying...")
            else:
                raise
        except urllib2.URLError as error:
            print(u"URLError! Retrying...")
            time.sleep(1)
        except:
            print(u'Ignore errors')
            pass
        else:
            break
    return updates

def sendMessages(send_text, chat_id):
    while True:
        try:
            bot.sendMessage(chat_id=chat_id, text=send_text)
            print(u"Mensaje enviado a id: {}".format(chat_id))
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

def getWho():
    while True:
        try:
            url = 'http://sugus.eii.us.es/en_sugus.html'
            html = urllib.urlopen(url).read()
            pq = PyQuery(html)
            break
        except:
            raise

    ul = pq('ul.usuarios > li')

    who = []
    ul.each(lambda w : who.append(ul.eq(w).text()))

    who_filtered = [w for w in who if w != "Parece que no hay nadie."]

    return who_filtered

def addTo(event, name):
    c = conn.cursor()

    date = datetime.now().strftime("%d-%m-%y")
    c.execute('insert into eventTable values(?, ?, ?)', (date, event.replace(" ",""), u'@'+name.replace(" ", "")))
    conn.commit()
    c.close()
    return name + u' añadido a ' + event

def findByEvent(event):
    c = conn.cursor()

    result = c.execute('select * from eventTable where event=?', (event.replace(" ",""),)).fetchall()

    c.close()

    return result

def removeFromEvent(event, name):
    c = conn.cursor()

    c.execute('delete from eventTable where event=? and name=?', (event, u'@' + name))

    conn.commit()

    c.close()

    return str(u'Has sido eliminado del evento '+ event)

def emptyEvent(event, name):
    # Debe de estar en el evento ! !
    c = conn.cursor()

    if u'@' + name in findByEvent(event):
        c.execute('delete from eventTable where event=?', (event))
        text = u'El evento {} ha sido eliminado'.join(event)
        conn.commit()
    else:
        text = u'El evento ' + event + ' NO ha sido eliminado'

    c.close()

    return text

def listEvents():
    c = conn.cursor()

    h = c.execute('select distinct event from eventTable')

    return h

if __name__ == '__main__':
    main()