from datetime import date, timedelta, datetime
import datetime
import models
from models import HistOption, HistStock, HistExpectedMove
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc
from database import SessionLocal, engine
import calendar
models.Base.metadata.create_all(bind=engine)

text_file = open("stocks.txt", "r")
stock_list = text_file.read().splitlines()

def weekday_finder(year, day_name):
    d = date(year, 1, 1)                    # January 1st
    if (day_name == 'Monday'):
        d += timedelta(days = 7 - d.weekday())
    if (day_name == 'Friday'):
        d += timedelta(days = 4 - d.weekday()) 
    while d.year == year:
        yield d
        d += timedelta(days = 7)


def get_specific_days(year, day_name):
    dates = []
    for d in weekday_finder(year, day_name):
        dates.append(d)
    return dates

def strike_increments(symbol, expiration_date):
    # returns an array of all the strikes
    db = SessionLocal()
    hist_options = db.query(HistOption.symbol, HistOption.strike)

    # get a distinct list of the strikes, then order it
    ordered_options = (hist_options
        .filter(and_(HistOption.symbol == symbol, HistOption.expirationDate == expiration_date))
        .order_by(asc(HistOption.strike))
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

def get_option_prop(symbol, strikes, put_call, obj_property, start_date, expiration_date):
    db = SessionLocal()
    hist_options = db.query(HistOption)

    options_data = (hist_options
        .filter(and_(HistOption.symbol == symbol, HistOption.strike == strikes, HistOption.putCall == put_call, HistOption.expirationDate == expiration_date, HistOption.date == start_date))
        .all()
    )

    if len(options_data) == 0 or getattr(options_data[0], obj_property) is None:
        return None
    else:
        return float(getattr(options_data[0], obj_property))

def two_ntm_strikes(strikes, underlying_price):

    # find 2 near-the-money strikes
    strike_1 = find_atm_strike_index(strikes, underlying_price)
    if (underlying_price < strikes[strike_1]):
        strike_2 = strike_1 - 1
    else:
        strike_2 = strike_1 + 1

    return sorted([strikes[strike_1], strikes[strike_2]], key=float)

def get_expected_move_alt(symbol, underlying_price, start_date, expiration_date):
    strikes = strike_increments(symbol, expiration_date)

    if len(strikes) == 0:
        return None

    # print('strikes')
    # print(strikes)
    two_atm_strikes = two_ntm_strikes(strikes, underlying_price)
    print('two_atm_strikes')
    print(two_atm_strikes)
    premium_calls_open_1 = get_option_prop(symbol, two_atm_strikes[0], 'CALL', 'open', start_date, expiration_date)
    premium_calls_open_2 = get_option_prop(symbol, two_atm_strikes[1], 'CALL', 'open', start_date, expiration_date)
    premium_puts_open_1 = get_option_prop(symbol, two_atm_strikes[0], 'PUT', 'open', start_date, expiration_date)
    premium_puts_open_2 = get_option_prop(symbol, two_atm_strikes[1], 'PUT', 'open', start_date, expiration_date)

    if premium_calls_open_1 is None or premium_calls_open_2 is None or premium_puts_open_1 is None or premium_puts_open_2 is None:
        return None
    else:
        # Since the underlying price won't be exactly on a strike, calculate the weighted difference between the nearest strikes
        strike_diff = abs(two_atm_strikes[1] - two_atm_strikes[0])
        price_distance = abs(underlying_price - two_atm_strikes[1])
        price_distance_percent = price_distance / strike_diff

        premium_calls_diff = abs(premium_calls_open_1 - premium_calls_open_2)
        premium_puts_diff = abs(premium_puts_open_1 - premium_puts_open_2)
        premium_call = premium_calls_open_1 - (premium_calls_diff * price_distance_percent)
        premium_put = premium_puts_open_2 - (premium_puts_diff * price_distance_percent)

        print('premium_call')
        print(premium_call)
        print('premium_put')
        print(premium_put)

        expected_move_alt = calc_expected_move_alt(underlying_price, premium_call, premium_put)
        return expected_move_alt

def calc_expected_move_alt(underlying_price, prem_call, prem_put):

    # average the two calls and puts premiums
    total_prem = prem_call + prem_put

    expected_move_alt_percent = total_prem * 85 / underlying_price
    expected_move_calc = expected_move_alt_percent / 100 * underlying_price

    print('expected_move_calc')
    print(expected_move_calc)
    return expected_move_calc

def third_fridays(d, n):
    """Given a date, calculates n next third fridays
   https://stackoverflow.com/questions/28680896/how-can-i-get-the-3rd-friday-of-a-month-in-python/28681097"""
 
    def next_third_friday(d):
        """ Given a third friday find next third friday"""
        d += timedelta(weeks=4)
        return d if d.day >= 15 else d + timedelta(weeks=1)
 
    # Find closest friday to 15th of month
    s = date(d.year, d.month, 15)
    result = [s + timedelta(days=(calendar.FRIDAY - s.weekday()) % 7)]
 
    # This month's third friday passed. Find next.
    if result[0] < d:
        result[0] = next_third_friday(result[0])
 
    for i in range(n - 1):
        result.append(next_third_friday(result[-1]))
 
    return result

db = SessionLocal()

year = 2015
year_prefix = str(year) + '_'

# Get every monday in the year. Mondays will be our "starting point" for most of our analysis
all_mondays = get_specific_days(year, 'Monday')
end_dates = {}

# Get every 3rd friday since most options have major monthly expirations on those days
for m in range(1, 13):
    third_friday = third_fridays(date(year, m, 1), 1)[0]
    end_dates[year_prefix + str(m)] = third_friday

# start_dates = []
# start_dates.append(all_mondays[0])
# # Get all the mondays immediately after the option expiration date.
# # This way we can get as much as a full month before the next expiration
# for index, fri in enumerate(end_dates):
#     start_date = [mon for mon in all_mondays if mon > end_dates[fri]]
#     start_dates.append(min(start_date))

for symbol in stock_list:
    # Exception is with the first week of Jan and the week after the Dec expiration
    # for index, value in enumerate(start_dates):
        # start_date = start_dates[index]
        # print('----------------------------------------------')
        # print('Start Date: ' + str(start_date))
        # if start_date > end_dates[year_prefix + str(start_date.month)] and start_date.month < 12:
        #     print('End Date: ' + str(end_dates[year_prefix + str(start_date.month + 1)]))
        #     end_date = str(end_dates[year_prefix + str(start_date.month + 1)])
        # elif start_date > end_dates[year_prefix + str(start_date.month)] and start_date.month >= 12:
        #     print('End Date: NEXT YEAR')
        #     break
        # else:
        #     print('End Date: ' + str(end_dates[year_prefix + str(start_date.month)]))
        #     end_date = str(end_dates[year_prefix + str(start_date.month)])
        
    for key, value in end_dates.items():
        
        end_date = datetime.datetime.strftime(value, '%Y-%m-%d')

        now = datetime.datetime.now().date()
        beg_of_current_week = now - timedelta(days=now.weekday())
        
        if key == str(year) + '_1':
            options_data = db.query(HistOption).filter(and_(HistOption.symbol == symbol, HistOption.date < end_date, HistOption.open.isnot(None))).order_by(asc(HistOption.date)).all()
            start_date = datetime.datetime.strptime(options_data[0].date, '%Y-%m-%d').date()
        else:
            options_data = db.query(HistOption).filter(and_(HistOption.symbol == symbol, HistOption.date < end_date, HistOption.date >= start_date, HistOption.open.isnot(None))).order_by(asc(HistOption.date)).all()
            start_date = datetime.datetime.strptime(options_data[0].date, '%Y-%m-%d').date()
        

        # for row in options_data:
        #     print(row)

        print('---------Start Date: ' + str(start_date))
        # There won't be historical data for the current week
        if start_date < beg_of_current_week:
            # Get the stock price on the start_date so we can later compare it with the options ATM premiums EM
            stock_data = db.query(HistStock).filter(and_(HistStock.symbol == symbol, HistStock.date == start_date)).all()

            # # If the Monday falls on a holiday, just use the next day, Tuesday
            # if len(stock_data) == 0:
            #     start_date = start_date + datetime.timedelta(days=1)
            #     stock_data = db.query(HistStock).filter(and_(HistStock.symbol == symbol, HistStock.date < start_date)).all()

            # Get the stock price at the same day of the expiration
            stock_data2 = db.query(HistStock).filter(and_(HistStock.symbol == symbol, HistStock.date == end_date)).all()

            # If the Friday falls on a holiday, just use the previous day, Thursday
            if len(stock_data2) == 0:
                end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d') - datetime.timedelta(days=1)
                end_date = datetime.datetime.strftime(end_date, '%Y-%m-%d')
                stock_data2 = db.query(HistStock).filter(and_(HistStock.symbol == symbol, HistStock.date == end_date)).all()

            print('----------End Date: ' + str(end_date))

            # Get a range of stock data so we can evaluate whether the stock "touched" the expected move at any point
            stock_data3 = db.query(HistStock).filter(and_(HistStock.symbol == symbol, HistStock.date >= start_date, HistStock.date <= end_date)).all()
            
            underlying_price = float(stock_data[0].open)
            underlying_price2 = float(stock_data2[0].close)
            print('Stock Price: ' + str(underlying_price))

            # Get the expected move
            em = get_expected_move_alt(symbol, underlying_price, start_date, end_date)

            if em is not None:
                actual_move = round((underlying_price2 - underlying_price), 2)
            
                # Calculate the amount of times the stock price passed through the expected move's upper or lower bounds
                # Thought: a good way to measure how often a stock "graviates" towards its' expected move
                num_of_touches = 0
                for price in stock_data3:
                    # print(str(price.low) + ' < ' + str(underlying_price + em) + ' < ' + str(price.high))
                    if float(price.low) <= float(underlying_price + em) <= float(price.high):
                        num_of_touches = num_of_touches + 1
                    if float(price.low) <= float(underlying_price - em) <= float(price.high):
                        num_of_touches = num_of_touches + 1


                print(stock_data[0].symbol)
                print('Stock Price Start: ' + str(underlying_price))
                print('Stock Price End: ' + str(underlying_price2))
                print('Exp Move: ' +  str(round(em, 2)))
                print('Actual Move: ' +  str(actual_move))
                print('Num of Touches: ' + str(num_of_touches))

                # insert data into database
                em_data = HistExpectedMove()
                em_data.symbol = stock_data[0].symbol
                em_data.start_date = start_date
                em_data.end_date = end_date
                em_data.expected_move = round(em, 2)
                em_data.actual_move = actual_move
                em_data.delta = abs(actual_move) - abs(round(em, 2))
                em_data.expected_move_touches = num_of_touches
                db.add(em_data)
                db.commit()

            start_date = end_date # for the next loop, update the start_date
                
