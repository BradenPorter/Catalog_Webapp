import os
import sys
import datetime
from sqlalchemy import Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

# Then we make 2 classes to correspond to the 2 tables we want in our database


class Categories(Base):
    __tablename__ = 'categories'

    # Below is a mapper
    # Nullable is false because we need a name
    name = Column(String(80), nullable=False)
    id = Column(Integer, primary_key=True)

    @property
    def serialize(self):
        return {
            'name': self.name,
            'id': self.id
        }


class Items(Base):
    __tablename__ = 'items'

    # Below is the second mapper
    # Nullable is false because we need a name
    name = Column(String(80), nullable=False)
    id = Column(Integer, primary_key=True)
    course = Column(String(250))
    description = Column(String(250))
    price = Column(String(8))
    category = Column(String, ForeignKey('categories.name'), nullable=False)
    categories = relationship(Categories)
    # We added this serialize function to be able to send JSON objects in a
    # serializable format

    @property
    def serialize(self):
        return {
            'category': self.category,
            'name': self.name,
            'description': self.description,
            'id': self.id,
            'price': self.price,
            'course': self.course
        }

engine = create_engine('sqlite:///categorymenu.db')
Base.metadata.create_all(engine)

# We create our database session
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

# Item categories/ restaurants
categories = [
    {'name': 'The CRUDdy Crab', 'id': '1'},
    {'name': 'Blue Burgers', 'id': '2'},
    {'name': 'Taco Hut', 'id': '3'}
]


# Menu Items
items = [
    {'category': 'Blue Burgers', 'name': 'Cheese Pizza',
        'description': 'made with fresh cheese', 'price': '$5.99', 'course': 'Entree', 'id': '1'},
    {'category': 'Blue Burgers', 'name': 'Chocolate Cake',
        'description': 'made with Dutch Chocolate', 'price': '$3.99', 'course': 'Dessert', 'id': '2'},
    {'category': 'Taco Hut', 'name': 'Caesar Salad', 'description': 'with fresh organic vegetables',
        'price': '$5.99', 'course': 'Entree', 'id': '3'},
    {'category': 'The CRUDdy Crab', 'name': 'Iced Tea', 'description': 'with lemon',
        'price': '$.99', 'course': 'Beverage', 'id': '4'},
    {'category': 'The CRUDdy Crab', 'name': 'Spinach Dip',
        'description': 'creamy dip with fresh spinach', 'price': '$1.99', 'course': 'Appetizer', 'id': '5'}
]
if __name__ == '__main__':
    # Below we add everything to our database
    for cat in categories:
        newCategory = Categories(name=cat['name'], id=cat['id'])
        session.add(newCategory)
        session.commit()

    for item in items:
        newItem = Items(category=item['category'], name=item['name'], description=item[
                        'description'], price=item['price'], course=item['course'], id=item['id'])
        session.add(newItem)
        session.commit()
