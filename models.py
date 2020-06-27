from sqlalchemy import Boolean, Column, ForeignKey, Numeric, Integer, String
from sqlalchemy.orm import relationship

from database import Base

class Stock(Base):
    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, unique=True, index=True)
    price = Column(Numeric(10, 2))
    forward_pe = Column(Numeric(10, 2))
    forward_eps = Column(Numeric(10, 2))
    dividend_yield = Column(Numeric(10, 2))
    ma50 = Column(Numeric(10, 2))
    ma200 = Column(Numeric(10, 2))

class Option(Base):
    __tablename__ = "options"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String)
    underlyingPrice = Column(Numeric(10, 2))
    expirationDate = Column(String)
    daysToExpiration = Column(Integer)
    strike = Column(Numeric(10, 2))
    putCall = Column(String)
    bid = Column(Numeric(10, 2))
    ask = Column(Numeric(10, 2))
    openInterest = Column(Numeric(10, 2))
    volume = Column(Numeric(10, 2))
    delta = Column(Numeric(10, 2))
    gamma = Column(Numeric(10, 2))
    theta = Column(Numeric(10, 2))
    vega = Column(Numeric(10, 2))
    impliedVolatility = Column(Numeric(10, 2))
    quoteDateTime = Column(String)
    creationDate = Column(String)
    batch = Column(Integer)
    

class ExpectedMove(Base):
    __tablename__ = "expected_moves"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String)
    underlyingPrice = Column(Numeric(10, 2))
    expirationDate = Column(String)
    daysToExpiration = Column(String)
    expectedMoveIV = Column(Numeric(10, 2))
    expectedMovePremium = Column(Numeric(10, 2))
    batch = Column(Integer)
    calculationDate = Column(String)

class Skew(Base):
    __tablename__ = "skews"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String)
    underlyingPrice = Column(Numeric(10, 2))
    expirationDate = Column(String)
    daysToExpiration = Column(Integer)
    quad1 = Column(Numeric(10, 2))
    quad2 = Column(Numeric(10, 2))
    quad3 = Column(Numeric(10, 2))
    quad4 = Column(Numeric(10, 2))
    maxQuadDiff = Column(Numeric(10, 2))
    quad1v2 = Column(Numeric(10, 2))
    quad1v3 = Column(Numeric(10, 2))
    quad1v4 = Column(Numeric(10, 2))
    quad2v3 = Column(Numeric(10, 2))
    quad2v4 = Column(Numeric(10, 2))
    quad3v4 = Column(Numeric(10, 2))
    calculationDate = Column(String)
    batch = Column(Integer)

class HistOption(Base):
    __tablename__ = "hist_options"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String)
    strike = Column(Numeric(10, 2))
    expirationDate = Column(String)
    daysToExpiration = Column(String)
    putCall = Column(String)
    open = Column(Numeric(10, 2))
    high = Column(Numeric(10, 2))
    low = Column(Numeric(10, 2))
    close = Column(Numeric(10, 2))
    volume = Column(Integer)
    date = Column(String)

class HistStock(Base):
    __tablename__ = "hist_stocks"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String)
    date = Column(String)
    open = Column(Numeric(10, 2))
    high = Column(Numeric(10, 2))
    low = Column(Numeric(10, 2))
    close = Column(Numeric(10, 2))
    volume = Column(Integer)

class HistExpectedMove(Base):
    __tablename__ = "hist_expected_moves"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String)
    start_date = Column(String)
    end_date = Column(String)
    expected_move = Column(Numeric(10, 2))
    actual_move = Column(Numeric(10, 2))
    delta = Column(Numeric(10, 2))
    expected_move_touches = Column(Numeric(10, 2))