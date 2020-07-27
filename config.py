import os

game_name = u"Jeopardy"
currency = u"¢"

storage = u"dict"

database = os.path.join(os.path.abspath(os.getcwd()), u"data", u"database.db")

app_secret = u"secret!"

debug = True
questions = 1
round_ = 3

testing_address = "127.0.0.1:5000"