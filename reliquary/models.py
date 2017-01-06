from sqlalchemy import Boolean, Column, Integer, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, scoped_session, sessionmaker
from zope.sqlalchemy import ZopeTransactionExtension

DBSession = scoped_session(sessionmaker(
    extension=ZopeTransactionExtension(),
    expire_on_commit=False))
Base = declarative_base()


class Channel(Base):
    __tablename__ = "channels"
    uid = Column(Integer, primary_key=True)
    dirty = Column(Boolean, default=True)

    name = Column(Text)
    indices = relationship("Index", backref="channel", cascade="all, delete-orphan")


class Index(Base):
    __tablename__ = "indices"
    uid = Column(Integer, primary_key=True)
    dirty = Column(Boolean, default=True)
    channel_id = Column(Integer, ForeignKey('channels.uid'))

    name = Column(Text)
    relics = relationship("Relic", backref="index", cascade="all, delete-orphan")


class Relic(Base):
    __tablename__ = "relics"
    uid = Column(Integer, primary_key=True)
    dirty = Column(Boolean, default=True)
    index_id = Column(Integer, ForeignKey('indices.uid'))

    name = Column(Text)
    mtime = Column(Text)
    size = Column(Integer)
