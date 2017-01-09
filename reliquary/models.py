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

    # additional debinfo if relic is a debian file
    debinfo = relationship("DebInfo", uselist=False, backref="relic", cascade="all, delete-orphan")


class DebInfo(Base):
    __tablename__ = "debinfo"
    uid = Column(Integer, primary_key=True)
    relic_id = Column(Integer, ForeignKey('relics.uid'))

    filename = Column(Text)                         # Packages index: mandatory
    #size = Column(Integer)                          # Packages index: mandatory -- see Relic.size
    md5sum = Column(Text, nullable=True)            # Packages index: recommended
    sha1 = Column(Text, nullable=True)              # Packages index: recommended
    sha256 = Column(Text, nullable=True)            # Packages index: recommended
    sha512 = Column(Text, nullable=True)            # Packages index: recommended
    description_md5 = Column(Text, nullable=True)   # Packages index: optional

    multi_arch = Column(Text, nullable=True)        # Packages index: if exists in control, needs to match exactly

    package = Column(Text)                          # mandatory
    source = Column(Text, nullable=True)            # optional
    version = Column(Text)                          # mandatory
    section = Column(Text, nullable=True)           # recommended
    priority = Column(Text, nullable=True)          # recommended
    architecture = Column(Text)                     # mandatory
    essential = Column(Text, nullable=True)         # optional
    depends = Column(Text, nullable=True)           # "depends et al" - Packages index: if exists in control, mandatory and needs to match exactly
    recommends = Column(Text, nullable=True)        # "depends et al" - Packages index: if exists in control, mandatory and needs to match exactly
    suggests = Column(Text, nullable=True)          # "depends et al" - Packages index: if exists in control, mandatory and needs to match exactly
    enhances = Column(Text, nullable=True)          # "depends et al" - Packages index: if exists in control, mandatory and needs to match exactly
    pre_depends = Column(Text, nullable=True)       # "depends et al" - Packages index: if exists in control, mandatory and needs to match exactly
    installed_size = Column(Integer, nullable=True) # "depends et al" - Packages index: if exists in control, mandatory and needs to match exactly
    maintainer = Column(Text)                       # mandatory
    description = Column(Text)                      # mandatory
    homepage = Column(Text, nullable=True)          # optional
    built_using = Column(Text, nullable=True)       # optional
