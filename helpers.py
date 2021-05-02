from functools import wraps
from flask import redirect, session, g


def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:

            # #temporarily login user
            # session["user_id"] = 3
            # return redirect("/")

            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

def formatpcnt(value):
    return f"{value:,.2f}"