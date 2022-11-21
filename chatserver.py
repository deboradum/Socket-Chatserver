import socket as s
import select as sel
import datetime

HELPTEXT = (" Welcome to the Jochem-ChatServer, available commands are:\n"
            "\t   /nick <new_nick> :: Set a new username.\n"
            "\t   /say <text> | <text> :: Send a message to every"
            "online user.\n"
            "\t   /whisper <receiver_nick> <text> :: Send a message to"
            "a specific user.\n"
            "\t   /list :: Get a list of every user currenyly online."
            "\n\t   /whois <user_nick> :: Receive the IP address of "
            "the specified user.\n"
            "\t   /kick <user_nick> :: Kick the specified user from "
            "the chatroom\n")


class Server:

    # Constructor
    def __init__(self, port, connections):
        # Inits socket.
        self.serverSocket = s.socket(s.AF_INET, s.SOCK_STREAM)
        self.serverSocket.setsockopt(s.SOL_SOCKET, s.SO_REUSEADDR, 1)
        self.serverSocket.bind(('', port))
        self.serverSocket.listen(connections)
        self.serverSocket.setblocking(0)

        # Inits input and output socket list for select module.
        self.connectedSockets = [self.serverSocket]
        self.onlineUsers = []
        self.bannedIps = []

    # Returns the server socket.
    def getServerSocket(self):
        return self.serverSocket

    # Returns the list with all connected sockets.
    def getConnectedSockets(self):
        return self.connectedSockets

    # Appends the list of connected sockets if it is not already in the list.
    def appendConnectedSockets(self, sock):
        if sock not in self.connectedSockets:
            self.connectedSockets.append(sock)

    # Removes the given socket from the list of connected sockets if it is in.
    def removeConnectedSockets(self, sock):
        if sock in self.connectedSockets:
            self.connectedSockets.remove(sock)

    # Sends message to every user.
    def sendMessageAll(self, messageToSend):
        for sock in self.connectedSockets:
            if sock is not self.serverSocket:
                try:
                    sock.send(messageToSend.encode())
                except Exception:
                    sock.close()
                    self.removeConnectedSockets(sock)

    # Sends message to a specific socket.
    def sendMessageOne(self, messageToSend, receiverSocket):
        if receiverSocket is not self.serverSocket:
            try:
                receiverSocket.send(messageToSend.encode())
            except Exception:
                receiverSocket.close()
                self.removeConnectedSockets(receiverSocket)

    # Adds a user dict to the list of online users.
    def addOnlineUser(self, socket, address, nickname):
        userDict = {}
        userDict['socket'] = socket
        userDict['address'] = address
        userDict['nickname'] = nickname
        self.onlineUsers.append(userDict)

    # Removes a user from the list of online users.
    def removeOnlineUser(self, user):
        if user is None:
            return
        if user in self.onlineUsers:
            self.onlineUsers.remove(user)

    # Returns the list of online users.
    def getOnlineUsers(self):
        return self.onlineUsers

    # Returns the user dict associated with a the given socket.
    def getUserFromSock(self, socket):
        try:
            u = list(filter(lambda user: user['socket'] == socket,
                     self.getOnlineUsers()))[0]
        except Exception:
            u = None
        return u

    # Returns the user dict associated with the given nickname.
    def getUserFromNick(self, nickname):
        try:
            u = list(filter(lambda user: user['nickname'] == nickname,
                     self.getOnlineUsers()))[0]
        except Exception:
            u = None
        return u

    # Returns the current time in the format for messages.
    def time(self):
        time = datetime.datetime.now().strftime("%H:%M:%S")
        return time

    # Handles the say command.
    def handleSay(self, message):
        finalMess = f"[{self.time()}] {message.getSender()}:"
        finalMess += f" {message.getText()}\n"
        self.sendMessageAll(finalMess)

    # Handles the list command.
    def handleList(self, message, receiveSock):
        finalMess = f"[{self.time()}] "
        count = 0
        for onlineU in self.getOnlineUsers():
            if count == 0:
                line = f"{onlineU['nickname']} {onlineU['address']}\n"
            else:
                line = f"\t   {onlineU['nickname']} {onlineU['address']}\n"
            finalMess += line
            count += 1
        self.sendMessageOne(finalMess, receiveSock)

    # Handls the help command.
    def handleHelp(self, message, receiveSock):
        text = "[" + self.time() + "]" + HELPTEXT
        self.sendMessageOne(text, receiveSock)

    # Handles the nick command.
    def handleNick(self, receiveSock, newNick):
        # Checks if username is in use.
        for user in self.getOnlineUsers():
            if user['nickname'] == newNick:
                mess = f"[{self.time()}] username {newNick} already in use\n"
                self.sendMessageOne(mess, receiveSock)
                return
        # Changes username
        user = self.getUserFromSock(receiveSock)
        if user is None:
            mess = f"[{self.time()}] Error changing username.\n"
            self.sendMessageOne(mess, receiveSock)
            return
        for u in self.onlineUsers:
            if user is u:
                oldNick = u['nickname']
                u['nickname'] = newNick
        # Notifies users of name change.
        message = f"[{self.time()}] user {oldNick} changed name to {newNick}\n"
        self.sendMessageAll(message)

    # Handles the whoIs command.
    def handleWhoIs(self, message, receiveSock):
        nickname = message.getNick()
        user = self.getUserFromNick(nickname)
        if user is None:
            finalMess = f"[{self.time()}] Could not find user {nickname}.\n"
        else:
            ip = user['address']
            finalMess = f"[{self.time()}] {nickname} has address {ip}\n"
        self.sendMessageOne(finalMess, receiveSock)

    # Handles the kick command.
    def handleKick(self, message, receiveSock):
        nickname = message.getNick()
        kickedUser = self.getUserFromNick(nickname)
        if kickedUser is None:
            finalMess = f"[{self.time()}] Could not find user {nickname}.\n"
            self.sendMessageOne(finalMess, receiveSock)
        else:
            kickerUser = self.getUserFromSock(receiveSock)
            if kickerUser is None:
                return
            kickerNickname = kickerUser['nickname']
            kickedSock = kickedUser['socket']
            kickedMess = f"[{self.time()}] You have been kicked by "
            kickedMess += f"{kickerNickname}\n"
            self.sendMessageOne(kickedMess, kickedSock)
            self.removeOnlineUser(kickedUser)
            self.removeConnectedSockets(kickedSock)
            kickedSock.close()
            finalMess = f"[{self.time()}] {nickname} has been kicked by "
            finalMess += f"{kickerNickname}\n"
            self.sendMessageAll(finalMess)

    # Handles the whisper command.
    def handleWhisper(self, message, sendSock):
        receiveNickname = message.nick
        receiveUser = self.getUserFromNick(receiveNickname)
        sendUser = self.getUserFromSock(sendSock)
        if receiveUser is None or sendUser is None:
            finalMess = f"[{self.time()}] Could not find user "
            finalMess += f"{receiveNickname}.\n"
            self.sendMessageOne(finalMess, sendSock)
        else:
            sendNick = sendUser['nickname']
            senderMess = f"[{self.time()}] whisper to "
            senderMess += f"{receiveUser['nickname']}: {message.getText()}\n"
            receiveMess = f"[{self.time()}] {sendNick} whispers: "
            receiveMess += f"{message.getText()}\n"
            receiveSock = receiveUser['socket']
            self.sendMessageOne(senderMess, sendSock)
            self.sendMessageOne(receiveMess, receiveSock)

    # Handles the ipBan command.
    def handleIpBan(self, message, sendSock):
        bannedNickname = message.nick
        bannedUser = self.getUserFromNick(bannedNickname)
        if bannedUser is None:
            finalMess = f"[{self.time()}] Could not find user "
            finalMess += f"{bannedNickname}.\n"
            self.sendMessageOne(finalMess, sendSock)
        else:
            sendUser = self.getUserFromSock(sendSock)
            if sendUser is None:
                return
            sendNick = sendUser['nickname']
            bannedIp = bannedUser['address']
            if bannedIp in self.bannedIps:
                mess = f"[{self.time()}] IP already banned.\n"
                self.sendMessageOne(mess, sendSock)
                return
            usersToRemove = []
            for sockU in self.getOnlineUsers():
                if sockU["address"] == bannedIp:
                    sock = sockU['socket']
                    mess = f"[{self.time()}] You have been IP "
                    mess += "banned.\n"
                    usersToRemove.append(sockU)
                    self.sendMessageOne(mess, sock)
                    self.removeConnectedSockets(sock)
                    sock.close()
            for user in usersToRemove:
                self.removeOnlineUser(user)
            if sendUser['address'] == bannedIp:
                mess = f"[{self.time()}] You have been IP banned.\n"
                self.sendMessageOne(mess, sendSock)
                self.removeConnectedSockets(sendSock)
                self.removeOnlineUser(sendUser)
                sendSock.close()
            globalMess = f"[{self.time()}] {sendNick} has banned IP"
            globalMess += f" {bannedIp}\n"
            self.sendMessageAll(globalMess)
            self.bannedIps.append(bannedIp)


class Message:

    # Constructor.
    def __init__(self, message, sender):
        message = message.strip()
        # If message starts with "/", assign the command, otherwise command is
        # "/say".
        self.correctMessage = self.__checkMessageCorrect(message)
        if self.correctMessage is False:
            return None

        self.sender = sender

        # Sets the used command.
        if message.split(" ", 1)[0].startswith("/"):
            self.command = message.split(" ", 1)[0]
        else:
            self.command = "/say"

        if self.command == "/nick":
            self.nick = message.split(" ")[1]
            self.text = None
        elif self.command == "/say":
            self.nick = None
            if message.startswith("/say"):
                self.text = message.split(" ", 1)[1]
            else:
                self.text = message
        elif self.command == "/whisper":
            self.nick = message.split(" ", 2)[1]
            self.text = message.split(" ", 2)[2]
        elif self.command == "/list":
            self.nick = None
            self.text = None
        elif self.command == "/help" or self.command == "/?":
            self.nick = None
            self.text = None
        elif self.command == "/whois":
            self.nick = message.split(" ")[1]
            self.text = None
        elif self.command == "/kick":
            self.nick = message.split(" ")[1]
            self.text = None
        elif self.command == "/ipban":
            self.nick = message.split(" ")[1]
            self.text = None

    # Returns False if command is invalid, True otherwise.
    def __checkMessageCorrect(self, message):
        if message.startswith("/nick"):
            if len(message.split(" ", 2)) != 2:
                return False
        elif message.startswith("/say"):
            if len(message.split(" ", 2)) < 2:
                return False
        elif message.startswith("/whisper"):
            if len(message.split(" ", 2)) != 3:
                return False
        elif message.startswith("/list"):
            if len(message.split(" ")) != 1:
                return False
        elif message.startswith("/help"):
            if len(message.split(" ")) != 1:
                return False
        elif message.startswith("/?"):
            if len(message.split(" ")) != 1:
                return False
        elif message.startswith("/whois"):
            if len(message.split(" ", 2)) != 2:
                return False
        elif message.startswith("/kick"):
            if len(message.split(" ", 2)) != 2:
                return False
        elif message.startswith("/ipban"):
            if len(message.split(" ", 2)) != 2:
                return False

        return True

    # Returns the correct message.
    def getCorrectMessage(self):
        return self.correctMessage

    # Returns the message sender.
    def getSender(self):
        return self.sender

    # Returns the command.
    def getCommand(self):
        return self.command

    # Returns the nickname for e.g. kick commands.
    def getNick(self):
        return self.nick

    # Returns the text in the command.
    def getText(self):
        return self.text


def serve(port, cert, key):
    """
    Chat server entry point.
    port: The port to listen on.
    cert: The server public certificate.
    key: The server private key.
    """

    # Initialises socket.
    server = Server(port, 20)

    while server.getConnectedSockets():
        readable, writable, error = sel.select(server.getConnectedSockets(),
                                               [], [])

        for sock in readable:
            # Adds new socket to the server and notifies users.
            if sock is server.getServerSocket():
                connectionSock, addr = sock.accept()
                if addr[0] in server.bannedIps:
                    connectionSock.close()
                else:
                    connectionSock.setsockopt(s.SOL_SOCKET, s.SO_REUSEADDR, 1)
                    connectionSock.setblocking(0)
                    server.appendConnectedSockets(connectionSock)
                    nickname = "Jochem-" + str(len(server.getOnlineUsers())+1)
                    server.addOnlineUser(connectionSock, addr[0], nickname)
                    mess = f"[{server.time()}] {addr[0]} connected with name "
                    mess += f"{nickname}\n"
                    server.sendMessageAll(mess)
            else:
                data = sock.recv(1024)

                # Removes socket from the server and notifies users.
                if not data:
                    user = server.getUserFromSock(sock)
                    if user is not None:
                        name = user['nickname']
                        # naar iedereen sturen
                        mess = f"[{server.time()}] {name} disconnected\n"
                        server.removeOnlineUser(user)
                        server.removeConnectedSockets(sock)
                        sock.close()
                        server.sendMessageAll(mess)
                else:
                    data = data.decode()
                    user = server.getUserFromSock(sock)
                    if user is not None:
                        sender = user['nickname']
                        messageParsed = Message(data, sender)
                        # Checks if message syntax is correct.
                        if messageParsed.getCorrectMessage() is False:
                            mess = "Incorrect syntax. Type '/?' for info.\n"
                            server.sendMessageOne(mess, sock)
                            continue
                        command = messageParsed.getCommand()
                        if command == "/say":
                            server.handleSay(messageParsed)
                        elif command == "/nick":
                            server.handleNick(sock, messageParsed.getNick())
                        elif command == "/whisper":
                            server.handleWhisper(messageParsed, sock)
                        elif command == "/list":
                            server.handleList(messageParsed, sock)
                        elif command == "/help" or command == "/?":
                            server.handleHelp(messageParsed, sock)
                        elif command == "/whois":
                            server.handleWhoIs(messageParsed, sock)
                        elif command == "/kick":
                            server.handleKick(messageParsed, sock)
                        elif command == "/ipban":
                            server.handleIpBan(messageParsed, sock)
                        else:
                            mess = "Unknown command. Type '/?' for info.\n"
                            server.sendMessageOne(mess, sock)


# Command line parser.
if __name__ == '__main__':
    import sys
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--port', help='port to listen on', default=12345, type=int)
    p.add_argument('--cert', help='server public cert',
                   default='public_html/cert.pem')
    p.add_argument('--key', help='server private key', default='key.pem')
    args = p.parse_args(sys.argv[1:])
    serve(args.port, args.cert, args.key)
