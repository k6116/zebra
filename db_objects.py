from models import Stock, Option, ExpectedMove, Skew
import datetime

def create_option_obj(symbol, option_data, underlying_price, batch, strike, expiration_date, days_to_expiration):
    option = Option()
    option.symbol = symbol
    option.underlyingPrice = underlying_price
    option.expirationDate = expiration_date
    option.daysToExpiration = days_to_expiration
    option.strike = strike
    option.putCall = option_data['putCall']
    option.bid = option_data['bid']
    option.ask = option_data['ask']
    option.openInterest = option_data['openInterest']
    option.volume = option_data['totalVolume']
    option.delta = option_data['delta']
    option.gamma = option_data['gamma']
    option.vega = option_data['vega']
    option.theta = option_data['theta']
    option.impliedVolatility = option_data['volatility']
    option.quoteDateTime = datetime.datetime.fromtimestamp(option_data['quoteTimeInLong'] / 1e3)
    option.creationDate = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    option.batch = batch
    return option

def create_em_obj(symbol, underlying_price, expiration_date, days_to_expiration, batch, em_iv, em_premium):
    expected_move = ExpectedMove()
    expected_move.symbol = symbol
    expected_move.underlyingPrice = underlying_price
    expected_move.expirationDate = expiration_date
    expected_move.daysToExpiration = days_to_expiration
    expected_move.expectedMoveIV = em_iv
    expected_move.expectedMovePremium = em_premium
    expected_move.batch = batch
    expected_move.calculationDate = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return expected_move