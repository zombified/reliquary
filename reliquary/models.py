from sqlalchemy import Boolean, Column, Integer, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from zope.sqlalchemy import ZopeTransactionExtension

DBSession = scoped_session(sessionmaker(extension=ZopeTransactionExtension()))
Base = declarative_base()


class Relic(Base):
    __tablename__ = "relics"
    uid = Column(Integer, primary_key=True)
    dirty = Column(Boolean, default=True)

    channel = Column(Text)
    index = Column(Text)
    name = Column(Text)
    mtime = Column(Text)
    size = Column(Integer)
