import os
import pandas as pd
import numpy as np

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, date
import re

from helpers import apology, login_required, lookup, usd

import json

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite databases
db = SQL(os.getenv("DATABASE_URL"))

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():

    """get user_id from session"""
    user_id = session["user_id"]

    """Show portfolio of stocks owned by user"""
    portfolio = db.execute("SELECT stock, numShares, price FROM symbols WHERE id = :user_id", user_id = user_id)
    cash = db.execute("SELECT cash FROM users WHERE id = :user_id", user_id = user_id)

    try:
        print(portfolio[0])
    except:
        return render_template("index.html", cash = cash)



    """Get a list of unique tickers to search for"""

    user_tickers = db.execute("""
                            SELECT DISTINCT stock
                            FROM symbols
                            WHERE id = :user_id""", user_id = user_id)

    typeof = type(user_tickers)
    print(f"type of user_tickers : {typeof}")


    sum_sharevalue = db.execute('SELECT stock, SUM(numShares) AS sumofshares, SUM(numShares*price) AS sumtotal FROM symbols WHERE id = :user_id GROUP BY stock', user_id = user_id)

    '''
    for stock in sum_sharevalue:
        print(f"""
        Stock : {stock['stock']},
        numShares : {stock['SUM(numShares)']},
        SUM_value : {stock["SUM(numShares*price)"]}
        """)
    '''



    """iterate through database to find 1. SUM of numShares of each stock
                                        2. SUM of total value of each stock"""

    sum_shares = db.execute("SELECT stock, numShares, price FROM symbols WHERE id = :user_id", user_id = user_id)






    """1. select from unique stock (tickers)

        2. work out SUM of total value of shares of each ticker
           SUM(  numShares * purchase price)

    """



    ''' might not need
    stock_list = []
    for i in range(5):
        stock_list.append(user_tickers[i]["stock"])
        print(stock_list[i])
    '''



    """Look up prices for each ticker and assign it to a list"""
    current_prices = []

    for i in range(len(user_tickers)):
        price_dict = lookup(user_tickers[i]["stock"])
        current_prices.append(price_dict["price"])


    """1. For each summed PnL, assign key/value to each stock list (sum_sharevalue)
        2. Error checking - see if sum_sharevalue[i]["stock"] == stock['stock']
    """

    sum_counter = 0
    for i in range(len(sum_sharevalue)):
        currentvalue = (sum_sharevalue[i]["sumofshares"]*current_prices[sum_counter])
        pnl_value = (currentvalue - sum_sharevalue[i]["sumtotal"])
        total_cost = sum_sharevalue[i]["sumtotal"]

        #sum_sharevalue[i]["TotalCost"] = sum_sharevalue[i]["sumtotal"]

        sum_sharevalue[i]['CurrentValue'] = currentvalue
        sum_sharevalue[i]['PnL'] = pnl_value
        #print(f"temp_dict {temp_dict}")
        print(i)
        sum_counter += 1




    '''
    for stock in sum_sharevalue:
        print(f"""
        Stock : {stock['stock']},
        numShares : {stock['SUM(numShares)']},
        SUM_value : {stock["SUM(numShares*price)"]}
        """)
    '''


    #return render_template("index.html", Stock = stock, Ticker = ticker, Shares, Cost, Current_Price)
    return render_template("index.html", Stock = sum_sharevalue, Prices = current_prices, cash = cash)

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    """get user_id from session"""
    user_id = session["user_id"]

    if request.method == "POST":

        if not request.form.get("symbol"):
            return apology("must provide symbol, 400")

        if not lookup(request.form.get("symbol")):
            return apology("symbol does not exist")

        if not request.form.get("shares"):
            return apology ("must provide number of shares", 400)

        '''check if numeric first'''
        """convert shares class type from str to int"""
        try:
            shares = int(request.form.get("shares"))
            if not shares >= 0:
                return apology ("shares must be positve!", 400)
        except:
            return apology ("shares must be an integer", 400)


        cash = db.execute("SELECT cash FROM users WHERE id = :user_id", user_id = user_id)


        #actual cash value
        cash_value = cash[0]["cash"]

        #lookup cost of each share
        symbol_dict = lookup(request.form.get("symbol"))
        symbol_price = symbol_dict["price"]
        symbol = symbol_dict['symbol']


        #give apology if user does not have enough cash
        total_cost = shares * symbol_price
        print('Total cost: %s' % total_cost)

        if total_cost > cash_value:
            return apology("You don't have enough money, you're such a bum")
        else:
            #create new table if doesnt exist already
            #add buy entry, update user balance in table 1
            #add shares ownership to table 2


            """adding shares bought, at what price, to database"""
            db.execute("INSERT into symbols (id, stock, numShares, price) VALUES(?, ?, ?, ?)", user_id, symbol, shares, symbol_price)


            """update transaction history here"""
            today = date.today()
            now = datetime.now()
            db.execute("INSERT into transactions (buy, stock, numShares, price, date, time, id) VALUES(?, ?, ?, ?, ?, ?, ?)", 1, symbol, shares, symbol_price, today.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"), user_id)


            """updating cash balance from users table"""
            db.execute("UPDATE users SET cash = cash - :total_cost WHERE id= :user_id", total_cost = total_cost, user_id = user_id)

            #cash = db.execute("SELECT cash FROM users WHERE id = :user_id", user_id = user_id)


            return redirect("/")
        """
        print("hello!")
        print(user_id)
        print(cash[0]["cash"])
        print(type(cash))
        print(type(cash[0]))
        print(type(cash[0]["cash"]))
        """

    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    """get user_id from session"""
    user_id = session["user_id"]

    history = db.execute("SELECT stock, buy, numShares, price, totalvalue, date, time FROM transactions WHERE id = :user_id", user_id = user_id)






    return render_template("history.html", history = history)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():

    if request.method == "POST":

        #Check if symbol field is empty
        if not request.form.get("symbol"):
            return apology("Symbol field must not be empty!", 400)

        my_string = request.form.get("symbol")

        #check for all characters being either an alphabetic or numeric char
        if any(c.isalnum() for c in my_string) == False:
            return apology("Symbol must only contain letters or numbers!", 400)

        #check for valid symbol
        if lookup(my_string) == None:
            return apology("Invalid ticker!", 400)


        symbol = request.form.get("symbol")
        symbol_dict = {}
        symbol_dict = lookup(symbol)
        #symbol_list = list(symbol_dict.items())


        #print(symbol_list['name'])

        print(symbol_dict["symbol"])
        print(symbol_dict["price"])

        #print(symbol_list)

        #for key, value in symbol_list.items():
        #    print(key, ' : ', value)


        return render_template("quote.html", Name=symbol_dict["name"], Price=symbol_dict["price"], Symbol=symbol_dict["symbol"])

    else:
        return render_template("quote.html")

    """Complete the implementation of quote in such a way that it allows a user to look up a stock’s current price.

Require that a user input a stock’s symbol, implemented as a text field whose name is symbol.
Submit the user’s input via POST to /quote.
Odds are you’ll want to create two new templates (e.g., quote.html and quoted.html).
When a user visits /quote via GET, render one of those templates, inside of which should be an HTML form
that submits to /quote via POST. In response to a POST, quote can render that second template,
embedding within it one or more values from lookup."""


@app.route("/register", methods=["GET", "POST"])
def register():

    def check_blanks(myString):
        #my string is not None and is not empty or blank
        if myString and myString.strip():
            return False
        else:
            return True


    if request.method == "POST":

        #Check if username is empty
        if not request.form.get('username'):
            return apology("Username must not be empty!")
        #Check if username doesn't just contain a whitespace
        elif check_blanks(request.form.get('username')):
            return apology("Username must contain valid characters!")

        #Check if password is empty
        if not request.form.get('password'):
            return apology("Password must not be empty!")
        #Check if passwords match

        if not request.form.get('password') == request.form.get('confirmation'):
            return apology("Passwords are not the same")


        username = request.form.get('username')

        '''extract list of users from database'''
        users_list = db.execute("SELECT username FROM users")
        #Check if the username is duplicate

        for item in users_list:
            if item["username"] == username:
                return apology("User already exists!")

        #generate hash of password
        password = generate_password_hash(request.form.get('password'))

        #insert username and hashed password into database
        db.execute("INSERT into users (username, hash ) VALUES(?, ?)", username, password)

        return redirect("/login")


    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock

        1. the user does not own any shares of that stock.
      2. if the user does not own that many shares of the stock.
    Submit the user’s input via POST to /sell.
    When a sale is complete, redirect the user back to the index page.
    You don’t need to worry about race conditions (or use transactions).

    """

    """Buy shares of stock"""

    """get user_id from session"""

    user_id = session["user_id"]

    """get list of stocks owned"""
    stocks_owned = db.execute("SELECT DISTINCT stock FROM symbols WHERE id = :user_id", user_id = user_id)


    if request.method == "POST":

        if not request.form.get("symbol"):
            return apology("must provide symbol, 403")

        if not lookup(request.form.get("symbol")):
            return apology("symbol does not exist")

        if not request.form.get("shares"):
            return apology ("must provide number of shares, 403")

        """convert shares class type from str to int"""
        shares_sell = int(request.form.get("shares"))
        if not (shares_sell > 0):
            return apology("number of shares must be a positive integer")

        """Get stock name"""
        stock = request.form.get("symbol")


        """get amount of cash"""
        cash = db.execute("SELECT cash FROM users WHERE id = :user_id", user_id = user_id)


        """get stock name, total shares, total value"""
        sum_sharevalues = db.execute("SELECT stock, SUM(numShares) AS sumofshares, SUM(numShares*price) AS sumtotal FROM symbols WHERE id = :user_id GROUP BY stock", user_id = user_id)
        for s_list in sum_sharevalues:
            if s_list["stock"] == stock:
                shares_list = s_list

        """Get amount of specific shares owned"""
        sum_shares_2 = shares_list["sumofshares"]
        print(f"sumshares : {sum_shares_2}")


        """return error if user owns less shares than shares being sold"""
        if sum_shares_2 < shares_sell:
            return apology("You do not have enough shares to sell")

        #actual cash value
        cash_value = cash[0]["cash"]

        #lookup cost of each share
        symbol_dict = lookup(request.form.get("symbol"))
        symbol_price = symbol_dict["price"]
        symbol = symbol_dict['symbol']

        #list containing primary_key, stock... see below
        shares_owned_listdict = db.execute("SELECT primary_key, stock, numShares, price , (numShares*price) AS "(numshares*price)" FROM symbols WHERE id = :user_id AND stock = :stock", stock = stock, user_id = user_id)
        shares_owned = shares_owned_listdict[0]
        print(f"Shares owned : {shares_owned}")
        print(f"type of shares_owned {type(shares_owned)}")



        """Sell shares
            1. Get total number of shares user wants to sell (shares_sell)
            2. Select shares from database, highlight for "destruction"
                extract share value from shares_owned["numShares*price"],
                if it satisfies selling pressure, cancel loop
            3. Get primary keys of those shares, tag them
            4. delete from SQL database
        """


        """tagging mechanism

            1. check if shares_owned["numShares*price"] <= shares_sell
                tag for destruction
            if not, prepare to minus it from database

            2. if shares_sell counter = 0
                stop loop
        """


        def sell_shares(s):
            sell_counter = s

            def inner_sell(number):
                inner_counter = number
                if inner_counter <= 0:
                    return redirect("/")

                for item in shares_owned_listdict:

                    #lets say, 2 shares owned and 3 to sell
                    #if one data value is overwhelmed by selling pressure
                    if item["numShares"] <= inner_counter and item["numShares"] != 0:
                        """actually im going to delete table row from symbols"""
                        db.execute("DELETE FROM symbols WHERE primary_key = :primary_key", primary_key=item['primary_key'])


                        print("Delete success!")


                        '''update transaction history here'''
                        '''set time and date variables'''
                        today = date.today()
                        now = datetime.now()

                        """update transaction history here"""
                        db.execute("INSERT into transactions (buy, stock, numShares, price, date, time, id) VALUES(?, ?, ?, ?, ?, ?, ?)", 0, symbol, item["numShares"] , symbol_price, today.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"), user_id)



                        value = item["numShares"] * symbol_price
                        db.execute("UPDATE users SET cash = cash + :value WHERE id= :user_id", value = value, user_id = user_id)


                        print(f"inner_counter before : {inner_counter} to minus numshares {item['numShares']}")
                        inner_counter = inner_counter - item["numShares"]
                        print(f"inner_counter now: {inner_counter} to minus numshares {item['numShares']}")


                        print(f'inner counter (does it say 1?) : {inner_counter} item["numShares"] {item["numShares"]}')
                        #inner_sell(inner_counter)

                    #if data value is bigger than selling pressure
                    else:

                        print(f"sell counter else loop  : {inner_counter} which is SMALLER than {item['numShares']}")
                        db.execute("UPDATE symbols SET numShares = numShares - :inner_sell WHERE primary_key = :primary_key", inner_sell = inner_counter, primary_key = item['primary_key'])
                        final_price = inner_counter * symbol_price
                        db.execute("UPDATE users SET cash = cash + :value WHERE id= :user_id", value = final_price, user_id = user_id)

                        today = date.today()
                        now = datetime.now()

                        """update transaction history here"""
                        db.execute("INSERT into transactions (buy, stock, numShares, price, date, time, id) VALUES(?, ?, ?, ?, ?, ?, ?)", 0, symbol, inner_counter, symbol_price, today.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"), user_id)
                        inner_counter = inner_counter - item["numShares"]
                        return redirect("/")

            inner_sell(sell_counter)

            print("all sold")
            return

        sell_shares(shares_sell)
        return redirect("/")


    else:
        return render_template("sell.html", stocks_owned = stocks_owned)


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
