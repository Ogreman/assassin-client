import os
from datetime import datetime

from flask import request, redirect, url_for, session, render_template, Flask, flash
from flask_wtf import Form
from wtforms import TextField, SelectField, validators
from unipath import Path

import requests


TEMPLATE_DIR = Path(__file__).ancestor(1).child("templates")

SERVER_URL = 'http://127.0.0.1:5001'
TARGET_API = SERVER_URL + '/api/targets/{0}'
USERS_API = SERVER_URL + '/api/users/'
USER_API = SERVER_URL + '/api/users/{0}'
ATTACK_API = SERVER_URL + '/api/hit/'


app = Flask(__name__, template_folder=TEMPLATE_DIR)
app.secret_key = os.environ.get('SECRET_KEY', 'something-secret-this-way-comes')


class PlayerForm(Form):
    email = TextField('Email Address', [validators.Length(min=6, max=35)])


class TargetForm(Form):
    target = SelectField('Target', choices=[])


@app.route("/", methods=["GET", "POST"])
def index():
    if 'player_id' in session:
        return redirect(url_for('game'))

    form = PlayerForm(request.form)
    if request.method == 'POST' and form.validate():
        try:
            response = requests.post(
                USERS_API,
                data={
                    'email': form.email.data,
                }
            )
        except requests.exceptions.ConnectionError:
            flash('Issue connecting to server')
        else:
            if response.status_code in [200, 201]:
                flash('Registered with id #{id}!'.format(
                    id=response.json().get('id')
                ))
                session['player_id'] = response.json().get('id')
                return redirect(url_for('game'))
            else:
                flash('Failed to register')
    return render_template("index.html", form=form)


@app.route('/game', methods=["GET", "POST"])
def game():
    form = TargetForm(request.form)
    if request.method == 'POST':
        """
        TODO: Instead, users could enter in secret ID obtained from person.
        """
        response = attack_target(form.target.data)
        if response.status_code == 200:
            try:
                if response.json()['hit']:
                    flash('HIT! You now have the pot!')
                    session['pot'] = True
                else:
                    flash('MISS!')
            except KeyError:
                flash('Unexpected response')
        else:
            flash('Failed to send attack')

    if 'pot' not in session:
        response = check_targets()
        if response.status_code == 200:
            users = response.json()
            try:
                form.target.choices = [
                    (str(user['id']), user['email'])
                    for user in users
                ]
            except KeyError:
                flash('Unexpected response')
        else:
            flash('Failed to get targets')
    return render_template("game.html", form=form)


@app.before_request
def check_pot():
    if 'player_id' in session:
        response = check_user(redirect_error='game')
        if response.status_code == 200:
            try:
                if response.json()['pot']:
                    flash('You have the pot!')
                    session['pot'] = True
                else:
                    session.pop('pot', None)
                session['score'] = response.json()['score']
            except KeyError:
                flash('Unexpected response')
        else:
            flash('Failed to check the pot')


def attack_target(target, redirect_error='game', redirect_user='index'):
    try:
        response = requests.post(
            ATTACK_API, data={
                'id': session['player_id'],
                'target': target,
            }
        )
    except requests.exceptions.ConnectionError:
        flash('Issue connecting to server')
        return redirect(url_for(redirect_error))
    except KeyError:
        flash('Not registered')
        return redirect(url_for(redirect_user))
    else:
        return response


def check_user(redirect_error='index', redirect_user='index'):
    try:
         response = requests.get(
            USER_API.format(session['player_id'])
        )
    except requests.exceptions.ConnectionError:
        flash('Issue connecting to server')
        return redirect(url_for(redirect_error))
    except KeyError:
        flash('Not registered')
        return redirect(url_for(redirect_user))
    else:
        return response


def check_users(redirect_error='index', redirect_user='index'):
    try:
         response = requests.get(USERS_API)
    except requests.exceptions.ConnectionError:
        flash('Issue connecting to server')
        return redirect(url_for(redirect_error))
    except KeyError:
        flash('Not registered')
        return redirect(url_for(redirect_user))
    else:
        return response


def check_targets(redirect_error='index', redirect_user='index'):
    try:
         response = requests.get(
            TARGET_API.format(session['player_id'])
        )
    except requests.exceptions.ConnectionError:
        flash('Issue connecting to server')
        return redirect(url_for(redirect_error))
    except KeyError:
        flash('Not registered')
        return redirect(url_for(redirect_user))
    else:
        return response


@app.route('/logout')
def logout():
    session.pop('player_id', None)
    flash('Logged out')
    return redirect(url_for('index'))


if __name__ == "__main__":
    app.run(debug=True, port=5000)