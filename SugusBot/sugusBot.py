#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import urllib
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

    # Create bot object
    bot = telegram.Bot(TOKEN)

    # Get last update ID
    LAST_UPDATE_ID = None

    # Discard old updates, sent before the bot was started
    num_discarded = 0
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
        while True:
            try:
                updates = bot.getUpdates(LAST_UPDATE_ID, timeout=30, network_delay=2.0)
            except telegram.TelegramError as error:
                if error.message == "Timed out":
                    print("Timed out! Retrying...")
                else:
                    raise
            except:
                raise
            else:
                break

        for update in updates:
            message = update.message
            actText = message.text
            actType = message.chat.type
            chat_id = message.chat.id
            update_id = update.update_id

            send_text = None

            if checkTypeAndTextStart(aText= actText, cText='/who', aType=actType, cType='private'):
                who = getWho()

                if len(who) == 0:
                    send_text = u"Parece que no hay nadie... {}".format(telegram.Emoji.DISAPPOINTED_FACE.decode('utf-8'))
                else:
                    send_text = show(u"Miembros en SUGUS:", who, [0])
            if checkTypeAndTextStart(aText= actText, cText='/join', aType=actType, cType='private'):
                rtext = actText.replace('/join','').replace(' ','')
                if not rtext:
                    send_text = u"Dime el evento"
                else:
                    addTo(rtext, message.from_user.username)

            if checkTypeAndTextStart(aText= actText, cText='/participants', aType=actType, cType='private'):
                rtext = actText.replace('/participants','').replace(' ','')
                if not rtext:
                    events = listEvents()
                    events_bonito = [u"{}{}".format(telegram.Emoji.SMALL_BLUE_DIAMOND.decode('utf-8'), w[0]) for w in events]
                    send_text = u"Elige una de las listas: \n{}".format('\n'.join(events_bonito))
                else:
                    event = rtext
                    participants = findByEvent(event)
                    if len(participants) == 0:
                        send_text = u"No hay nadie en {}".format(event)
                    else:
                        send_text = show(u"Participantes en {}:".format(event), participants, [2, 0])

            if checkTypeAndTextStart(aText= actText, cText='/disjoin', aType=actType, cType='private'):
                rtext = actText.replace('/disjoin','').replace(' ','')
                send_text = removeFromEvent(rtext, message.from_user.username)

            if checkTypeAndTextStart(aText= actText, cText='/empty', aType=actType, cType='private'):
                rtext = actText.replace('/empty').replace(' ','')
                send_text = emptyEvent(rtext, message.from_user.username)

            if send_text != None:
                bot.sendMessage(chat_id=chat_id, text=send_text)
                print(u"Mensaje enviado a {}/{} ({})".format(message.from_user.username, message.from_user.first_name, str(message.chat.id)))

            LAST_UPDATE_ID = update_id + 1


def checkTypeAndTextStart(aText = None, aUName = None, cText = None, aType = None, cType = None, cUName = None):

    result = True

    if cType != None:
        result = result and aType == cType
    if cUName != None:
        result = result and aUName == cUName
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


def getWho():
    url = 'http://sugus.eii.us.es/en_sugus.html'
    html = urllib.urlopen(url).read()
    pq = PyQuery(html)
    ul = pq('ul.usuarios > li')

    who = []
    ul.each(lambda w : who.append(ul.eq(w).text()))

    who_filtered = [w for w in who if w != "Parece que no hay nadie."]

    return who_filtered

def addTo(event, name):
    c = conn.cursor()

    date = datetime.now().strftime("%d-%m-%y")
    c.execute('insert into eventTable values(?, ?, ?)', (date, event.replace(" ",""), name.replace(" ", "")))

    conn.commit()

    c.close()

def findByEvent(event):
    c = conn.cursor()

    result = c.execute('select * from eventTable where event=?', (event.replace(" ",""),)).fetchall()

    c.close()

    return result

def removeFromEvent(event, name):
    c = conn.cursor()

    c.execute('delete from eventTable where event=? and name=?', (event, name))

    c.close()

    return u'Has sido eliminado del evento {}'.join(event)

def emptyEvent(event, name):
    # Debe de estar en el evento ! !
    c = conn.cursor()

    if name in findByEvent(event):
        c.execute('delete from eventTable where event=?', (event, name))
        text = u'El evento {} ha sido eliminado'.join(event)
    else:
        text = u'El evento {} NO ha sido eliminado'.join(event)

    c.close()

    return text

def listEvents():
    c = conn.cursor()

    h = c.execute('select distinct event from eventTable')

    return h

if __name__ == '__main__':
    main()