from typing import Annotated, TypeVar

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import declared_attr, DeclarativeBase,  mapped_column

from .config import settings


intpk = Annotated[int, mapped_column(primary_key=True, unique=True)]
strpk = Annotated[str, mapped_column(primary_key=True, unique=True)]
int_uniq = Annotated[int, mapped_column(unique=True)]
str_uniq = Annotated[str, mapped_column(unique=True)]
int_empty = Annotated[int, mapped_column(nullable=True)]
str_empty = Annotated[str, mapped_column(nullable=True)]
bool_empty = Annotated[bool, mapped_column(nullable=True)]


class Base(DeclarativeBase):

    @declared_attr
    def __tablename__(cls):
        return cls.__name__


ModelType = TypeVar('ModelType', bound=Base)
async_engine = create_async_engine(settings.database_url)
async_session_factory = async_sessionmaker(async_engine)
