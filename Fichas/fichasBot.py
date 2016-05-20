#!/usr/bin/python
# -*- coding: utf-8 -*-

import traceback
import logging
import urllib
# import urllib2 # Doesn't work in python 3
import time
import csv
from pyquery import PyQuery
import telegram
# import string
import array
import math
import os
import logging

import codecs
import sys

import sqlite3
import configparser
from datetime import datetime

# file_name = "DefaultConfig.ini"
from telegram import forcereply

file_name = "MyConfig.ini"

config = configparser.ConfigParser()
config.read(file_name)

# Create bot object
bot = telegram.Bot(config['Bot']['TOKEN'])

# Definitions of parameters
TOKEN = config['Bot']['TOKEN']
my_id = int(config['Admin']['my_id'])
luna_id = int(config['Admin']['luna_id'])
group_id = int(config['Admin']['group_id'])
dbName = config['DataBase']['file_name']
notify_expense_added = config['Admin'].getboolean('notify_expense_added')
onlySendToMe = config['Admin'].getboolean('only_send_to_me')
verboseMode = config['Logs'].getboolean('mode_verbose')
only_luna_can_fichas = config['Admin'].getboolean('only_luna_can_fichas')
spammer = []

class data_base():
    def __init__(self):
        # self.conn = sqlite3.connect('payTogetherDBconUseMonica.db')
        self.conn = sqlite3.connect(dbName)

        c = self.conn.cursor()

        # Toda la info para las consultas: https://sqlite.org/lang_createtable.html
        # Probar las consultas: http://stackoverflow.com/questions/8272534/testing-sqlite-code-online

        c.execute('CREATE TABLE IF NOT EXISTS userTable(userId INTEGER NOT NULL UNIQUE, userName TEXT NOT NULL, '
                  'mail TEXT)')
        # Siempre que se inserte o modifique algo en la expensesTable o en la relationTable se debe actualizar el campo "owe"

        c.execute('CREATE TABLE IF NOT EXISTS fichasTable(id INTEGER PRIMARY KEY, '
                  'deId integer NOT NULL REFERENCES userTable(userId), '
                  'paraId integer NOT NULL REFERENCES userTable(userId), '
                  'total INTEGER DEFAULT 0, '
                  'UNIQUE (deId, paraId))')

        c.execute('CREATE TABLE IF NOT EXISTS ghostTable(id INTEGER PRIMARY KEY, '
                  'userId integer NOT NULL REFERENCES userTable(userId), '
                  'total INTEGER DEFAULT 0, '
                  'UNIQUE (userId))')

        self.conn.commit()
        # self.__toSend = None

        c.close()

    def check_user(self, actUser, toSend):
        # Check if the actUser is in the data_base or changed his username
        self.__toSend = toSend
        if len(actUser.username) > 3:
            userDB = self.__getUserRow(actUser.id)
            if userDB == None:
                self.__createUser(actUser.id, actUser.username)
            elif userDB[1] != u"@" + actUser.username:
                self.__createUser(actUser.id, actUser.username)
            return True
        else:
            return False

    def getUserNames(self):
        c = self.conn.cursor()

        h = c.execute('SELECT userName FROM userTable').fetchall()

        return h

    def addFicha(self, deUserName, paraUserName, puntos):
        try:
            deId = self.__getUserByUsername(deUserName)[0][0]
            paraId = self.__getUserByUsername(paraUserName)[0][0]
            expenseID = self.__addFicha(deId, paraId, puntos)

        except:
            print('Errors in addFicha: ' + str(sys.exc_info()[0]))
            return False
        else:
            return expenseID

    def __addFicha(self, deId, paraId, number):
        c = self.conn.cursor()

        if deId != paraId:
            total = c.execute('SELECT total FROM fichasTable WHERE deId = "{deId}" and paraId = "{paraId}"'.format(
                deId=deId, paraId=paraId)).fetchone()
        # print("Consulta h: " + str(h))

            if total is not None:
                number += total[0]
                print("Fichas en db: " + str(total[0]) + ";")

            print("Fichas a insertar en db: " + str(number) + " " + str(deId) + " -> " +str(paraId))
            h = c.execute('INSERT OR REPLACE INTO fichasTable (deId, paraId, total) '
                  'VALUES(?, ?, ?)', (deId, paraId, number))

            self.conn.commit()
        c.close()
        return number

    def addGhost(self, userName, puntos):
        try:
            deId = self.__getUserByUsername(userName)[0][0]
            expenseID = self.__addGhost(deId, puntos)

        except:
            print('Errors in addGhost: ' + str(sys.exc_info()[0]))
            return False
        else:
            return expenseID

    def __addGhost(self, deId, number):
        c = self.conn.cursor()

        total = c.execute('SELECT total FROM ghostTable WHERE userId = "{deId}"'.format(
            deId=deId)).fetchone()
        # print("Consulta h: " + str(h))

        if total is not None:
            number += total[0]
            print("Fantasma en db: " + str(total[0]) + ";")

        print("Fantasma a insertar en db: " + str(number) + " " + str(deId))
        h = c.execute('INSERT OR REPLACE INTO ghostTable (userId, total) '
                          'VALUES(?, ?)', (deId, number))

        self.conn.commit()
        c.close()
        return number


    def __createUser(self, userId, userName):
        c = self.conn.cursor()
        userName = "@" + str(userName)
        print("No chequea que tenga nombre de usuario ! ! !")
        c.execute('INSERT OR REPLACE INTO userTable (userId, userName) VALUES(?, ?)', (userId, userName))
        self.conn.commit()
        c.close()


    def __getUserRow(self, userId):
        c = self.conn.cursor()

        h = c.execute('SELECT * FROM userTable WHERE userId = {uid}'.format(uid=userId)).fetchone()

        return h


    def __getUserByUsername(self, username):
        c = self.conn.cursor()
        username = str(username).replace(" ", "")

        h = c.execute('SELECT * FROM userTable WHERE userName = "{uname}"'.format(uname=username)).fetchall()
        c.close()
        return h


    def getExpenseByUser(self, user, numExpenses=1):
        c = self.conn.cursor()

        print("OJO !!!!, el método getExpenseByUser no devuelve todos los expenses que estén relacionados con ese "
              "usuario, solo devuelve aquellos expenses que haya insertado ese usuario")
        print("OJO ! ! !, el método getExpenseByUser devuelve los relations de cualquier manera. Corregir!")

        h = c.execute('SELECT id FROM expensesTable WHERE insertBy = {uid} ORDER BY dateInsertion DESC Limit {nE}'
                      .format(uid=user.id, nE=numExpenses)).fetchall()

        # # Desde getOwe
        # fromUser = c.execute('SELECT userTable.userName, oweTable.owe FROM oweTable INNER JOIN userTable '
        #                      'ON userTable.userId == oweTable.toUserId '
        #                      'WHERE fromUserId = "{Uid}" and fromUserId != toUserId'.format(Uid=user.id)).fetchall()
        # toUser = c.execute('SELECT userTable.userName, oweTable.owe FROM oweTable INNER JOIN userTable '
        #                    'ON userTable.userId == oweTable.fromUserId '
        #                    'WHERE toUserId = "{Uid}" and fromUserId != toUserId'.format(Uid=user.id)).fetchall()
        # result = set(fromUser + toUser)
        c.close()
        return h


    def getStatusFantasmas(self):
        c = self.conn.cursor()
        relation = c.execute('SELECT de.userName, f.total '
                             'FROM ghostTable as f INNER JOIN userTable AS de '
                             'ON de.userId == f.userId ').fetchall()
        c.close()
        return relation

    def getStatusFichas(self):
        c = self.conn.cursor()
        relation = c.execute('SELECT de.userName, para.userName, f.total '
                             'FROM fichasTable as f INNER JOIN userTable AS de '
                             'ON de.userId == f.deId '
                             'INNER JOIN userTable AS para '
                             'ON para.userId == f.paraId').fetchall()

        c.close()
        return relation

    def getStatusFichasDeId(self, userId):
        c = self.conn.cursor()
        relation = c.execute('SELECT de.userName, f.total '
                             'FROM fichasTable as f INNER JOIN userTable AS de '
                             'ON de.userId == f.deId '
                             'INNER JOIN userTable AS para '
                             'ON para.userId == f.paraId '
                             'WHERE f.paraId = "{userId}"'.format(userId=userId)).fetchall()

        c.close()
        return relation

    def getInfoByExpenseId(self, expenseId):
        c = self.conn.cursor()
        expenseId = int(expenseId)
        print("OJO !!!!! El método getInfoByExpenseId no checkea que el usuario que lo ejecuta esté "
              "incluido en ese gasto")
        # RelationTable
        relation = c.execute('SELECT userTable.userName, relationTable.percentInfluenced '
                             'FROM relationTable INNER JOIN userTable '
                             'ON userTable.userId == relationTable.userId '
                             'WHERE expenseID = "{Eid}" and relationTable.userId != insertBy'.format(
                Eid=expenseId)).fetchall()

        expense = c.execute('SELECT expensesTable.id, expensesTable.amount, expensesTable.datePayment, '
                            'expensesTable.description '
                            'FROM expensesTable '  # INNER JOIN userTable '
                            # 'ON userTable.userId == relationTable.userId '
                            'WHERE id = "{Eid}"'.format(Eid=expenseId)).fetchone()
        c.close()
        # h = {"relation": relation, "expense": expense}
        expenseNew = []
        if expense is not None:
            expenseNew.append(["<b>Id:</b>", expense[0]])
            expenseNew.append(["<b>Importe:</b>", expense[1]])
            expenseNew.append(["<b>Fecha de pago:</b>", expense[2]])
            expenseNew.append(["<b>Descripción:</b>", expense[3]])

        relationNew = []
        for a in range(len(relation)):
            relationNew.append([relation[a][0], relation[a][1] * expense[1]])

        return {"relation": relationNew, "expense": expenseNew}

    def clean_fichas(self):
        c = self.conn.cursor()
        c.execute('DELETE FROM fichasTable')
        self.conn.commit()
        c.close()

    def query_database(self, toQuery):
        c = self.conn.cursor()
        res = c.execute(toQuery)
        self.conn.commit()
        c.close()
        return res


class inConversation():
    def __init__(self):
        self.__inConversation = {}

    def __gKey(self, actUser, conversationId=None):
        # Generate the key based on actUser and conversationId
        if conversationId is None:
            conversationId = actUser.id

        return str(actUser.id) + "-" + str(conversationId)

    def addOption(self, actUser, option, value, conversationId=None):
        key = self.__gKey(actUser, conversationId)
        if self.get(actUser) == []:
            self.__inConversation[key] = {option: value}
        else:
            self.__inConversation[key][option] = value

    def __add(self, key, options):
        self.__inConversation[key] = options

    def delOption(self, actUser, option, conversationId=None):
        key = self.__gKey(actUser, conversationId)
        del self.__inConversation[key][option]

    def empty(self, actUser, conversationId=None):
        key = self.__gKey(actUser, conversationId)
        del self.__inConversation[key]

    def get(self, actUser, conversationId=None):
        key = self.__gKey(actUser, conversationId)
        try:
            result = self.__inConversation[key]
        except KeyError as error:
            result = []
            pass
        return result

    def containOption(self, actUser, option, conversationId=None, cOptValue=None):
        options = self.get(actUser, conversationId)
        if option in options:
            if cOptValue == options[option]:
                return True
            elif cOptValue == None:
                return True
            else:
                return False
        else:
            return False

    def status(self, actUser, conversationId=None):
        key = self.__gKey(actUser, conversationId)
        if key in self.__inConversation:
            return True
        else:
            return False


class send():
    def __init__(self):
        # Create bot object
        self.__bot = telegram.Bot(TOKEN)
        self.__files = []
        self.__messages = []

    def confUser(self, message):
        self.chat_id = message.chat.id
        self.reply_id = message.message_id

    def addFile(self, path=None, URL=None, data=None, header=None, filename=None):
        if path is None and URL is None and data is None:
            print("Impossible get the file")
        else:
            if path is not None:
                self.__files.append([self.chat_id, path, filename])
            elif URL is not None:
                self.__bot.sendDocument(chat_id=self.chat_id, document=URL, filename=filename)
            else:
                print("userid: " + str(self.chat_id))
                if os.path.exists('output.csv'):
                    os.remove('output.csv')
                with open('output.csv', 'w') as f:
                    writer = csv.writer(f)
                    if header is not None:
                        writer.writerow([i[0] for i in header])
                    writer.writerows(data)
                    # writer.writerows([i for i in data])
                f.close()
                self.__files.append([self.chat_id, 'output.csv', filename])

    def addMessages(self, send_text, chat_id=None, send_markup=None, parse_mode=None, is_reply=True):
        if chat_id is None:
            chat_id = self.chat_id
        self.__messages.append([chat_id, send_text, send_markup, parse_mode, is_reply])

    def status(self):
        if len(self.__files) > 0 or len(self.__messages) > 0:
            return True
        else:
            return False

    def sendAll(self):
        for a in self.__files:
            g = open(a[1], 'rb')
            # self.__bot.sendDocument(chat_id=a[0], document=g, filename=a[2])
            if a[0] is self.chat_id or notify_expense_added:
                self.__sendDocument(chat_id=a[0], data=g, filename=a[2])
        self.__files.clear()

        for a in self.__messages:
            if a[0] is self.chat_id or notify_expense_added:
                self.__sendMessage(chat_id=a[0], send_text=a[1], send_markup=a[2], parse_mode=a[3], is_reply=a[4])
        self.__messages.clear()

    def __sendDocument(self, chat_id, data, filename):
        while True:
            try:
                self.__bot.sendDocument(chat_id=chat_id, document=data, filename=filename)

            except telegram.TelegramError as error:
                if error.message == "Timed out":
                    print("Timed out! Retrying...")
                else:
                    print(error)
                    # except urllib.URLError as error:
                    #     print("URLError! Retrying to send message...")
                    #     time.sleep(1)
            except:
                print('Ignore exception:' + str(sys.exc_info()[0]))
                pass
            else:
                print("Documento enviado a id: " + str(chat_id))
                break

    def __sendMessage(self, send_text, chat_id=None, send_markup=None, parse_mode=None, is_reply=True):
        while True:
            try:
                if is_reply:
                    self.__bot.sendMessage(chat_id=chat_id, text=send_text, reply_markup=send_markup,
                                           parse_mode=parse_mode, reply_to_message_id=self.reply_id)
                else:
                    self.__bot.sendMessage(chat_id=chat_id, text=send_text, reply_markup=send_markup,
                                           parse_mode=parse_mode)
                #  El error a veces se debe al método addRelation cuando envía al otro usuario el mensaje de confirmación
            except telegram.TelegramError as error:
                if error.message == "Timed out":
                    print("Timed out! Retrying...")
                else:
                    print(error)
                    # except urllib.URLError as error:
                    #     print("URLError! Retrying to send message...")
                    #     time.sleep(1)
            except:
                print('Ignore exception:')
                print(traceback.print_exc())
                print("chat_id='" + str(chat_id) + "', text='" + str(send_text) + "', reply_markup='" +
                      str(send_markup) + "', parse_mode='" + str(parse_mode)+"'")
                pass
                print("Este break debería eliminarse ! ! !")
                break  # No debería estar
                # raise
            else:
                print("Mensaje enviado a id: " + str(chat_id))
                break


def main():
    # UTF-8 console stuff thingies
    UTF8Writer = codecs.getwriter('utf8')
    # sys.stdout = UTF8Writer(sys.stdout)


    # Init logging
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Discard old updates, sent before the bot was started
    num_discarded = 0

    # Init Data Base
    dBase = data_base()
    inConv = inConversation()
    toSend = send()

    # Get last update ID
    LAST_UPDATE_ID = None

    while True:
        # updates = bot.getUpdates(LAST_UPDATE_ID, timeout=1, network_delay=2.0)
        updates = getUpdates(LAST_UPDATE_ID, timeout=0.5)
        if updates is not None and len(updates) > 0:
            num_discarded += len(updates)
            LAST_UPDATE_ID = updates[-1].update_id + 1
        else:
            break

    print("Discarded {} old updates".format(num_discarded))

    onlySendToMe = config['Admin'].getboolean('only_send_to_me')
    verboseMode = config['Logs'].getboolean('mode_verbose')
    only_luna_can_fichas = config['Admin'].getboolean('only_luna_can_fichas')
    group_id = int(config['Admin']['group_id'])

    # Main loop
    print('Working...')
    while True:

        updates = getUpdates(LAST_UPDATE_ID)
        # El timeout es el tiempo que tarda en ejecutar el bucle

        for update in updates:
            message = update.message
            actText = message.text
            actType = message.chat.type
            chat_id = message.chat.id
            update_id = update.update_id
            actUser = message.from_user

            send_text = None
            send_markup = None

            toSend.confUser(message=message)

            # periodicCheck()

            # print(pending_development())

            if dBase.check_user(actUser, toSend) and (actUser.id == my_id or not onlySendToMe) and \
                    ((not actUser.id in spammer) or actUser.id == my_id):

                if actUser.id != my_id and verboseMode:
                    my_text = "El usuario '" + str(actUser.id) + "' ha enviado un mensaje y tiene nombre de " \
                                                                 "usario '@" + str(actUser.username) + "'" \
                                ":\n" + actText + "\nPuedes ejecutar /stop! para volverlo privado"
                    sendMessages(my_text, my_id)

                if regularCheck(message, inConv, cText='/cancel'):
                    if inConv.status(actUser, chat_id):
                        inConv.empty(actUser, chat_id)
                    send_markup = telegram.ReplyKeyboardHide()
                    send_text = "Listo"

                elif regularCheck(message, inConv, cText='/help'):
                    send_text = help()

                # if checkTypeAndTextStart(aText= actText, cText='/me', aType=actType, cType='private'):
                elif regularCheck(message, inConv, cText='/me'):
                    send_text = "User ID: " + str(actUser.id) + "; Username: @" + str(actUser.username) + \
                                "; Conversation id: " + str(chat_id)

                    print(send_text)

                elif ((regularCheck(message, inConv, cText='/ficha') and not only_luna_can_fichas) or
                    regularCheck(message, inConv, cText='/ficha', cUid=[luna_id])):

                    if (message.chat.type == 'group'):
                        toSend.addMessages("Por privado")

                    users = dBase.getUserNames()
                    text = "¿Quien ha sido el campeón que te ha metido una ficha?"

                    toSend.addMessages(text,
                                       send_markup=telegram.ReplyKeyboardMarkup(users, selective=True,
                                                                                resize_keyboard=True),
                                       chat_id=actUser.id, is_reply=False)

                    inConv.addOption(actUser, "/ficha", "paraquien", conversationId=actUser.id)

                elif regularCheck(message, inConv, cOption='/ficha', cOptValue='paraquien', cType='private'):

                    ret = dBase.addFicha(paraUserName='@' + actUser.username, deUserName= actText, puntos=1)
                    toSend.addMessages("Recibido !", send_markup=telegram.ReplyKeyboardHide())

                    toSend.addMessages(actText + " le ha tirado una ficha a @" + actUser.username,
                                       send_markup=telegram.ReplyKeyboardHide(), chat_id=group_id, is_reply=False)
                    inConv.empty(actUser, chat_id)

                elif regularCheck(message, inConv, cText='/fantasma'):
                    if message.chat.type == 'group':
                        toSend.addMessages("Por privado")
                    toSend.addMessages("Dime quien es el fantasma",
                                       send_markup=telegram.ReplyKeyboardMarkup(dBase.getUserNames(), selective=True,
                                                                                resize_keyboard=True),
                                       chat_id=actUser.id, is_reply=False)
                    inConv.addOption(actUser, "/fantasma", "paraquien", conversationId=actUser.id)

                elif regularCheck(message, inConv, cOption='/fantasma', cOptValue='paraquien', cType='private'):

                    if actText.replace(" ", "") != "@" + actUser.username:
                        dBase.addGhost(userName=actText, puntos=1)
                        toSend.addMessages("Fantasma recibido ! ", send_markup=telegram.ReplyKeyboardHide())
                        toSend.addMessages("@" + actUser.username + " ha añadido un fantasma para " + actText ,
                                       send_markup=telegram.ReplyKeyboardHide(), chat_id=group_id, is_reply=False)
                        inConv.empty(actUser, chat_id)
                    else:
                        toSend.addMessages(" ?¿ ")

                elif regularCheck(message, inConv, cText='/rkfantasma'):
                    toSend.addMessages(
                            showList("Estado Fantasmas: ", dBase.getStatusFantasmas(),
                                     [0, 1], [" => ", "" + telegram.Emoji.GHOST]))


                elif regularCheck(message, inConv, cText='/rkfichas'):
                    if only_luna_can_fichas:
                        toSend.addMessages(
                            showList("Estado de las fichas hacia @Luna2395: ", dBase.getStatusFichasDeId(luna_id),
                                     [0, 1], [" => ", ""]))
                    else:
                        toSend.addMessages(
                            showList("Estado de las fichas: ", dBase.getStatusFichas(), [0, 1, 2],
                                     [" -> ", " => ", ""]))

                elif regularCheck(message, inConv, cText='/backupDB', cType='private', cUid=[my_id]):
                    if actUser.id == my_id:
                        toSend.addFile(path=dbName)

                elif regularCheck(message, inConv, cText='/advancedhelp', cUid=[my_id]):
                    send_text = helpTesting()

                elif regularCheck(message,inConv, cText='/cleanFichas', cUid=[my_id]):
                    dBase.clean_fichas()
                    toSend.addMessages("Limpiado")

                elif regularCheck(message,inConv, cText='/luna-id', cUid=[my_id]):
                    toSend.addMessages("Dime el id:")
                    inConv.addOption(actUser, "/luna-id", "id", chat_id)

                elif regularCheck(message, inConv, cOption='/luna-id', cOptValue='id'):
                    inConv.empty(actUser, chat_id)
                    try:
                        id_luna = int(actText.replace(' ', ''))
                        config['Admin']['luna_id'] = str(id_luna)
                        with open(file_name, 'w') as configfile:
                            config.write(configfile)
                    except:
                        toSend.addMessages("No pude cambar el ID")
                    else:
                        toSend.addMessages("Id cambiado a '" + str(id_luna) + "'")

                elif regularCheck(message, inConv, cText='/groupId', cUid=[my_id]):
#                    inConv.empty(actUser, chat_id)
                    try:
                        group_id = int(actText.replace('/groupId', '').replace(' ', ''))
                        config['Admin']['group_id'] = str(group_id)
                        with open(file_name, 'w') as configfile:
                            config.write(configfile)
                    except:
                        toSend.addMessages("No pude cambar el ID")
                    else:
                        toSend.addMessages("Id cambiado a '" + str(group_id) + "'")

                elif regularCheck(message,inConv, cText='/lunaFichas', cUid=[my_id]):
                    toSend.addMessages("Cambiando la variable 'only_luna_can_fichas'")
                    only_luna_can_fichas = not only_luna_can_fichas
                    config['Admin']['only_luna_can_fichas'] = str(only_luna_can_fichas)
                    with open(file_name, 'w') as configfile:
                        config.write(configfile)

                    toSend.addMessages("Nuevo valor: " + str(only_luna_can_fichas))

                elif regularCheck(message,inConv, cText='/addSpammer', cUid=[my_id]):
                    actText = actText.replace('/addSpammer', '').replace(' ', '')
                    spammer.append(int(actText))
                    toSend.addMessages("Añadido a spammer el id '" + str(int(actText)) + "'")

                elif regularCheck(message,inConv, cText='/delSpammer', cUid=[my_id]):
                    actText = actText.replace('/delSpammer', '').replace(' ', '')
                    spammer.remove(int(actText))
                    toSend.addMessages("Eliminado de spammer el id '" + str(int(actText)) + "'")

                elif regularCheck(message,inConv, cText='/listSpammer', cUid=[my_id]):
                    toSend.addMessages("Son los siguientes: " + str(spammer))

                elif regularCheck(message,inConv, cText='/sqlInjection', cUid=[my_id]):
                    toSend.addMessages("Dime la query:")
                    inConv.addOption(actUser, "/sqlInjection", "inject", chat_id)

                elif regularCheck(message, inConv, cOption='/sqlInjection', cOptValue='inject', cUid=[my_id]):
                    res = dBase.query_database(actText)
                    inConv.empty(actUser,chat_id)
                    toSend.addMessages("Resultado de la query: " + str(res))

                elif regularCheck(message,inConv, cText='/stop!', cUid=[my_id]):
                    toSend.addMessages("Solo te contestaré a ti hasta que uses /start!")
                    onlySendToMe = True
                    config['Admin']['only_send_to_me'] = str(onlySendToMe)
                    with open(file_name, 'w') as configfile:
                        config.write(configfile)

                elif regularCheck(message,inConv, cText='/start!', cUid=[my_id]):
                    toSend.addMessages("Contestaré a todos hasta que uses /stop!")
                    onlySendToMe = False
                    config['Admin']['only_send_to_me'] = str(onlySendToMe)
                    with open(file_name, 'w') as configfile:
                        config.write(configfile)

                elif regularCheck(message,inConv, cText='/verbosemode', cUid=[my_id]):
                    toSend.addMessages("Cambiado el modo a dime todo / no me digas nada")
                    verboseMode = not verboseMode
                    config['Logs']['mode_verbose'] = str(verboseMode)
                    with open(file_name, 'w') as configfile:
                        config.write(configfile)
                    toSend.addMessages("Concretamente se quedó así: " + config['Logs']['mode_verbose'])

            elif onlySendToMe:
                toSend.addMessages("Este bot actualmente solo contesta al administrador")

            elif actUser.id in spammer:
                toSend.addMessages("Eres un #spammer y estas bloqueado.\n Tu id es: " + str(actUser.id))

            else:
                send_text = "Debes tener un nombre de usuario o alias para usar este bot"
                send_text += "\nPara ello debes acceder a la configuración de tu aplicación de Telegram " \
                             "y posteriormente alias"

                my_text = "El usuario '" + str(actUser.id) + "' ha enviado un mensaje pero no tiene nombre de usario"
                sendMessages(my_text, my_id)

            if send_text != None and send_markup == None:
                sendMessages(send_text, chat_id)
                toSend.sendAll()
            elif send_text != None and send_markup != None:
                sendMessages(send_text, chat_id, send_markup)
                toSend.sendAll()
            elif toSend.status():
                toSend.sendAll()
            elif regularCheck(message, inConv, cType='private'):
                sendMessages(help(), chat_id)
            else:
                print("Mensaje recibido y no respondido de: " + str(actUser.id))

            LAST_UPDATE_ID = update_id + 1


def regularCheck(message, inConv, cText=None, cType=None, cUName=[], cUid=[], cOption="None_Null", cOptValue=None):
    actText = message.text
    actType = message.chat.type
    chat_id = message.chat.id
    actUser = message.from_user

    result = True

    if cType != None:
        result = result and actType == cType

    if cUName != []:
        if actUser.username not in cUName:
            result = False

    if cUid != []:
        if actUser.id not in cUid:
            result = False

    if cText != None:
        result = result and actText.startswith(cText)

    if cOption != "None_Null":
        if cOption != None:
            result = result and inConv.containOption(actUser, cOption, chat_id, cOptValue=cOptValue)
        else:
            result = result and not inConv.status(actUser, chat_id)

    return result


def showList(header, contains, positions=None, separation=None):
    result = str(header)
    if contains is not None:
        for a in contains:
            result += "\n " + telegram.Emoji.SMALL_BLUE_DIAMOND
            if positions is not None:
                for i in range(len(positions)):
                    result += str(a[positions[i]])
                    if separation is not None:
                        result += separation[i]
                    else:
                        result += " "
            else:
                try:
                    result += " " + str(a[:]) + " "
                except:
                    result += " " + str(a) + " "
    return result


# def periodicCheck():
#
#     ## Remove periodic comida
#     actDate = datetime.now().strftime("%d-%m-%y")
#     actComida = findByEvent('comida')
#
#     for a in actComida:
#         if a[0] != actDate:
#             removeFromEvent('comida', a[2])


def help():
    header = "Elige una de las opciones: "
    contain = [['/help', 'Ayuda'], ['/rkfichas', 'Estado de fichas'], ['/ficha', 'Añadir fichas']]
    contain = contain + [['/rkfantasmas', 'Estado de fantasmas'], ['/fantasma', 'Añadir fantasma']]
    contain = contain + [['/cancel', 'Cancela la sesión actual'], ['/me', 'Mi información']]
    contain = contain + [['/advancedhelp', 'Ayuda avanzada']]
    return showList(header, contain, [0, 1])


def helpTesting():
    header = "Elige una de las opciones: "
    contain = [['/advancedhelp', 'Ayuda avanzada'], ['/lunaFichas', 'Cambia quien puede poner fichas']]
    contain = contain + [['/verbosemode', 'Modo chivato'], ['/luna-id', 'Dime el id de Luna']]
    contain = contain + [['/backupDB', 'BackUp de la base de datos'], ['/cleanFichas', 'Limpia la tabla de fichas']]
    contain = contain + [['/addSpammer + id', 'Añadir a la lista spammer'], ['/delSpammer + id', 'Añadir a la lista spammer']]
    contain = contain + [['/listSpammer', 'Lista los spammer'], ['/sqlInjection', 'Inyectar query en base de datos']]
    contain = contain + [['/stop!', 'Convierte el bot en privado'], ['/start!', 'Hace el bot público']]
    return showList(header, contain, [0, 1])


def help_show():
    header = "Puedes realizar las siguientes acciones: "
    contain = [['/cancel', 'Cancela la selección'], ['/verbosemode', 'Chiva cuando otros hablen']]
    contain = contain + [['/spendEdit', 'Edita el gasto']]
    contain = contain + [['/relationEdit', 'Edita los usuarios relacionados con el gasto']]
    contain = contain + [['/spendDel', 'Elimina el gasto']]
    return showList(header=header, contains=contain, positions=[0, 1])


def getUpdates(LAST_UPDATE_ID, timeout=30):
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
                #        except urllib2.URLError as error: # Doesn't work in python 3
        except urllib.error.URLError as error:
            print("URLError! Retrying...")
            time.sleep(3)
        except KeyboardInterrupt as error:
            print("Stopping bot...")
            raise
        except:
            print('Ignore errors :' + str(sys.exc_info()[0]))
            time.sleep(1)
            pass
            # raise
        else:
            break
    return updates


def sendMessages(send_text, chat_id, send_markup=None):
    while True:
        try:
            bot.sendMessage(chat_id=chat_id, text=send_text, reply_markup=send_markup)
            print("Mensaje enviado a id: " + str(chat_id))
            break
        except telegram.TelegramError as error:
            if error.message == "Timed out":
                print("Timed out! Retrying...")
            else:
                print(error)
        # except urllib.URLError as error:
        #     print("URLError! Retrying to send message...")
        #     time.sleep(1)
        except:
            print('Ignore exception:' + str(sys.exc_info()[0]))
            pass


if __name__ == '__main__':
    main()
