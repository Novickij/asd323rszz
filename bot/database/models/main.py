from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy import Column, Integer, String, ForeignKey, Table, UniqueConstraint, BigInteger
from sqlalchemy import Float, DateTime, Boolean
from bot.database.main import engine  # Импортируем engine как функцию
from bot.misc.util import CONFIG
from sqlalchemy.ext.asyncio import async_sessionmaker

# Базовый класс для моделей
class Base(DeclarativeBase):
    pass

# Таблица для связи между Persons и PromoCode
message_button_association = Table(
    'person_promocode_association',
    Base.metadata,
    Column('promocode_id', Integer, ForeignKey('promocode.id', ondelete='CASCADE')),
    Column('users_id', Integer, ForeignKey('users.id', ondelete='CASCADE')),
    Column('use', Boolean, default=False),
    UniqueConstraint('promocode_id', 'users_id', name='uq_users_promocode')
)

# Модель Groups
class Groups(Base):
    __tablename__ = 'groups'
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, unique=True)
    locations = relationship('Location', back_populates="group_tabel")
    users = relationship('Persons', back_populates="group_tabel")

# Модель Persons
class Persons(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    tgid = Column(BigInteger, unique=True)
    banned = Column(Boolean, default=False)
    trial_period = Column(Boolean, default=False)
    special_offer = Column(Boolean, default=False)
    username = Column(String)
    fullname = Column(String)
    referral_user_tgid = Column(BigInteger, nullable=True)
    referral_balance = Column(Integer, default=0)
    lang = Column(String, default=CONFIG.languages)
    lang_tg = Column(String, nullable=True)
    blocked = Column(Boolean, default=False)
    group = Column(
        String,
        ForeignKey("groups.name", ondelete='SET NULL'),
        nullable=True
    )
    group_tabel = relationship(Groups, back_populates="users")
    payment = relationship('Payments', back_populates='payment_id')
    promocode = relationship(
        'PromoCode',
        secondary='person_promocode_association',
        back_populates='person'
    )
    withdrawal_requests = relationship(
        'WithdrawalRequests',
        back_populates='person'
    )
    keys = relationship(
        'Keys',
        back_populates='person'
    )

# Модель Keys
class Keys(Base):
    __tablename__ = 'keys'
    id = Column(Integer, primary_key=True, index=True)
    person = relationship(Persons, back_populates="keys")
    user_tgid = Column(BigInteger, ForeignKey("users.tgid"))
    subscription = Column(BigInteger)
    notion_oneday = Column(Boolean, default=False)
    switch_location = Column(Integer, default=0)
    id_payment = Column(String, nullable=True)
    trial_period = Column(Boolean, default=False)
    free_key = Column(Boolean, default=False)
    server = Column(
        Integer,
        ForeignKey("servers.id", ondelete='SET NULL'),
        nullable=True
    )
    server_table = relationship("Servers", back_populates="keys")
    notification_sent = Column(Boolean, default=False)  # Добавлено новое поле

# Модель Donate
class Donate(Base):
    __tablename__ = 'donate'
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String)
    price = Column(Float)

# Модель Servers
class Servers(Base):
    __tablename__ = 'servers'
    id = Column(Integer, primary_key=True, index=True)
    type_vpn = Column(Integer, nullable=False)
    outline_link = Column(String, unique=True)
    ip = Column(String, nullable=True)
    connection_method = Column(Boolean)
    panel = Column(String)
    inbound_id = Column(Integer)
    password = Column(String)
    login = Column(String)
    actual_space = Column(Integer, default=0)
    keys = relationship(Keys, back_populates="server_table")
    work = Column(Boolean, default=True)
    free_server = Column(Boolean, default=False)
    static = relationship("StaticPersons", back_populates="server_table")
    vds = Column(
        Integer,
        ForeignKey("vds.id"),
        nullable=False
    )
    vds_table = relationship('Vds', back_populates="servers")

    @classmethod
    def create_server(cls, data):
        return cls(**data)

# Модель Vds
class Vds(Base):
    __tablename__ = 'vds'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    ip = Column(String, nullable=False, unique=True)
    vds_password = Column(String)
    work = Column(Boolean, default=True)
    max_space = Column(Integer, default=0)
    servers = relationship(Servers, back_populates="vds_table")
    location = Column(
        Integer,
        ForeignKey("location.id"),
        nullable=False
    )
    location_table = relationship('Location', back_populates="vds")

    @classmethod
    def create_vds(cls, data):
        return cls(**data)

# Модель Location
class Location(Base):
    __tablename__ = 'location'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    work = Column(Boolean, default=True)
    pay_switch = Column(Boolean, default=False)
    group = Column(
        String,
        ForeignKey("groups.name", ondelete='SET NULL'),
        nullable=True
    )
    group_tabel = relationship(Groups, back_populates="locations")
    vds = relationship(Vds, back_populates="location_table")

    @classmethod
    def create_location(cls, data):
        return cls(**data)

# Модель Payments
class Payments(Base):
    __tablename__ = 'payments'
    id = Column(Integer, primary_key=True, index=True)
    user = Column(Integer, ForeignKey("users.id"))
    payment_id = relationship(Persons, back_populates="payment")
    id_payment = Column(String, nullable=True)
    month_count = Column(Integer, nullable=True)
    payment_system = Column(String)
    amount = Column(Float)
    data = Column(DateTime)

# Модель StaticPersons
class StaticPersons(Base):
    __tablename__ = 'static_persons'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    server = Column(Integer, ForeignKey("servers.id", ondelete='SET NULL'))
    server_table = relationship("Servers", back_populates="static")

# Модель PromoCode
class PromoCode(Base):
    __tablename__ = 'promocode'
    id = Column(Integer, primary_key=True, index=True)
    text = Column(String, unique=True, nullable=False)
    percent = Column(Integer, nullable=False)
    count_use = Column(Integer, nullable=False)
    person = relationship(
        'Persons',
        secondary='person_promocode_association',
        back_populates='promocode',
    )

# Модель WithdrawalRequests
class WithdrawalRequests(Base):
    __tablename__ = 'withdrawal_requests'
    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Integer, nullable=False)
    payment_info = Column(String, nullable=False)
    communication = Column(String)
    check_payment = Column(Boolean, default=False)
    user_tgid = Column(BigInteger, ForeignKey("users.tgid"))
    person = relationship("Persons", back_populates="withdrawal_requests")

# Функция для создания всех таблиц
async def create_all_table():
    # Вызываем engine() для получения объекта AsyncEngine
    async_engine = engine()
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Закрываем соединение после создания таблиц
    await async_engine.dispose()

# Создание сессии (используем вызов engine())
async_session = async_sessionmaker(engine(), expire_on_commit=False)