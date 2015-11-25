from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db_setup import Base, Categories, Items, session
from flask import session as login_session
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

app = Flask(__name__)

# Open the json file from our google webapp
CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']

APPLICATION_NAME = "catalog"


@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    # return "The current session state is %s" % login_session['state']
    return render_template('login.html', STATE=state)


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['credentials'] = credentials
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    # Display user info
    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output

# Logout function


@app.route('/disconnect')
def disconnect():
    credentials = login_session.get('credentials')
    print 'In disconnect credentials are %s' % credentials
    print 'User name is: '
    print login_session['username']
    # Notify user if not connected
    if credentials is None:
        print 'Credentials are None'
        response = make_response(json.dumps(
            'Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = credentials.access_token
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    print 'result is '
    print result
    # Delete login info
    if result['status'] == '200':
        del login_session['credentials']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        flash("Successful logout!")
        return redirect('/catalog')
    else:
        flash('Failed to logout. Could not revoke token for given user.')
        response.headers['Content-Type'] = 'application/json'
        return redirect('/catalog')

# JSON for all categories and items


@app.route("/catalog/JSON")
def catalogJSON():
    categories = session.query(Categories)
    items = session.query(Items)
    return jsonify(Categories=[c.serialize for c in categories], Items=[i.serialize for i in items])

# JSON for all items in category


@app.route("/catalog/<string:category>/JSON")
def catalogCategoryJSON(category):
    items = session.query(Items).filter_by(category=category).all()
    return jsonify(Items=[i.serialize for i in items])

# JSON for single item


@app.route("/catalog/<string:category>/<string:item>/JSON")
def categoryItemJSON(category, item):
    items = session.query(Items).filter_by(name=item)
    return jsonify(Items=[i.serialize for i in items])

# Main page with categories and items


@app.route("/")
@app.route("/catalog")
def catalog():
    categories = session.query(Categories)
    items = session.query(Items)
    return render_template('catalog.html', categories=categories, items=items)

# Display categories and all items for a given category


@app.route("/catalog/<string:category>")
def catalogCategory(category):
    categories = session.query(Categories)
    items = session.query(Items)
    return render_template('category.html', categories=categories, category=category, items=items)

# Display an item and its info


@app.route("/catalog/<string:category>/<string:item>")
def categoryItem(category, item):
    items = session.query(Items)
    return render_template('item.html', item=item, items=items)

# Display form for adding a new item and its info


@app.route("/catalog/new", methods=['GET', 'POST'])
def newItem():
    # First we make sure we are loged in
    if 'username' not in login_session:
        return redirect('/login')
    # Then we process the request, creating and item
    categories = session.query(Categories)
    if request.method == 'POST':
        new = Items(name=request.form['name'], description=request.form[
                    'description'], price=request.form['price'], category=request.form['category'])
        session.add(new)
        session.commit()
        flash("New item created!")
        # Go back to main page and notify user
        return redirect(url_for('catalog'))
    else:
        # Display form
        return render_template('new.html', categories=categories)

#


@app.route("/catalog/<string:category>/<string:item>/edit", methods=['GET', 'POST'])
def editItem(category, item):
    # First we make sure we are loged in
    if 'username' not in login_session:
        return redirect('/login')
    categories = session.query(Categories)
    items = session.query(Items)
    editedItem = session.query(Items).filter_by(name=item).one()
    # Process the request and make sure everything is there then we update
    if request.method == 'POST':
        if request.form['name']:
            editedItem.name = request.form['name']
        if request.form['description']:
            editedItem.description = request.form['description']
        if request.form['price']:
            editedItem.price = request.form['price']
        if request.form['category']:
            editedItem.category = request.form['category']
        session.add(editedItem)
        session.commit()
        flash("Item edited!")
        return redirect(url_for('catalog'))
    else:
        return render_template('edit.html', categories=categories, category=category, item=item, items=items)


@app.route("/catalog/<string:category>/<string:item>/delete", methods=['GET', 'POST'])
def deleteItem(category, item):
    # First we make sure we are loged in
    if 'username' not in login_session:
        return redirect('/login')
    # Then we delete
    itemToDelete = session.query(Items).filter_by(name=item).one()
    if request.method == 'POST':
        session.delete(itemToDelete)
        session.commit()
        flash("Item deleted!")
        return redirect(url_for('catalog'))
    else:
        return render_template('delete.html', category=category, item=item)

if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
