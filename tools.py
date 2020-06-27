import models
from database import SessionLocal, engine
from models import Stock, Option
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc
import math

def get_option_prop(symbol, strikes_list, put_call, obj_property, dte):
    db = SessionLocal()
    options = db.query(Option)

    options_data = (options
        .filter(and_(Option.symbol == symbol, Option.strike.in_(strikes_list), Option.putCall == put_call, Option.daysToExpiration == dte))
        .all()
    )

    props = []
    for prop in options_data:
        props.append(float(getattr(prop, obj_property)))
    
    return props

def strike_increments(symbol, dte):

    # returns an array of all the strikes
    db = SessionLocal()
    options = db.query(Option.symbol, Option.strike)
    # get a distinct list of the strikes, then order it
    ordered_options = (options
        .filter(and_(Option.symbol == symbol, Option.daysToExpiration == dte, Option.bid != 0, Option.ask != 0))
        .order_by(asc(Option.strike))
        .distinct()
        .all()
    )
    
    strikes = []
    for opt in ordered_options:
        strikes.append(float(opt.strike)) 

    # print('strikes')
    # print(strikes)
    return strikes

def find_atm_strike_index(strikes, underlying_price):
    atm_price = min(strikes, key=lambda x:abs(x - float(underlying_price)))
    print('atm_price')
    print(atm_price)
    return strikes.index(atm_price)


def custom_round(x, base):
    return base * round(x / base)
    
        