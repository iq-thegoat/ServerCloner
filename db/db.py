from sqlalchemy import create_engine, ForeignKey, Column, String, Integer, DateTime,LargeBinary
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime
import io
from dotenv import load_dotenv
import os

global base
Base = declarative_base()


class DbStruct:
    class messages(Base):
        __tablename__ = "messages"
        id = Column("id",Integer,autoincrement=True,primary_key=True)
        message_id= Column("messaage_id",Integer)       

        date = Column("date",DateTime,default=datetime.datetime.utcnow())
        
        def __init__(self,message_id,date=None):
            self.message_id = message_id
            self.date = date if date else datetime.datetime.utcnow()

class BotDb:
    def __init__(self) -> None:
        engine = create_engine("sqlite:///db/database.db")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        self.session = Session() 
