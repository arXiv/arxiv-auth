"""SQLAlchemy models for database integration."""

from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, Enum, \
    ForeignKey, Index, Integer, SmallInteger, String, Text, text
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

from arxiv import taxonomy
from ... import domain

Base = declarative_base()


class DBClient(Base):
    """Persistence for :class:`domain.Client`."""

    __tablename__ = 'client'

    client_id = Column(Integer, primary_key=True, autoincrement=True)
    owner_id = Column(Integer)
    created = Column(DateTime, default=datetime.now)

    name = Column(String(255))
    url = Column(String(255))
    description = Column(Text)
    redirect_uri = Column(String(255), nullable=True)

    authorizations = relationship('DBClientAuthorization',
                                  back_populates='client', lazy='joined')
    credential = relationship('DBClientCredential', uselist=False,
                              back_populates='client', lazy='joined')
    grant_types = relationship('DBClientGrantType', back_populates='client',
                               lazy='joined')


class DBClientCredential(Base):
    """Persistence for :class:`domain.ClientCredential`."""

    __tablename__ = 'client_credential'

    credential_id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(ForeignKey('client.client_id'))
    client_secret = Column(String(255))
    created = Column(DateTime, default=datetime.now)

    client = relationship('DBClient', back_populates='credential',
                          uselist=False)


class DBClientAuthorization(Base):
    """Persistence for :class:`domain.ClientAuthorization`."""

    __tablename__ = 'client_authorization'

    authorization_id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(ForeignKey('client.client_id'))
    requested = Column(DateTime, default=datetime.now)
    authorized = Column(DateTime, nullable=True)
    scope = Column(String(2056))
    client = relationship('DBClient', back_populates='authorizations')


class DBClientGrantType(Base):
    """Persistence for :class:`domain.ClientGrantType`."""

    __tablename__ = 'client_grant_type'

    grant_type_id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(ForeignKey('client.client_id'))
    requested = Column(DateTime, default=datetime.now)
    authorized = Column(DateTime, nullable=True)
    grant_type = Column(Enum(*domain.ClientGrantType.GRANT_TYPES))
    client = relationship('DBClient', back_populates='grant_types')
