from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from flask import Flask, render_template, request, abort, json

engine = create_engine('postgresql://myapp:dbpass@localhost:15432/spatial', echo=True)
Session = sessionmaker(bind=engine)
app = Flask(__name__)
app.config.from_pyfile('config.py')
session = Session()

import webapp.views