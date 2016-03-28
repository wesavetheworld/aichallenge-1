import logging
import os.path
import re
import shutil
import subprocess as sp
from contextlib import contextmanager

from flask.ext.login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from flask import request
from werkzeug import secure_filename
import sqlalchemy as db
from sqlalchemy.orm import backref, relationship
from sqlalchemy.ext.declarative import declarative_base


from battlebots import config
from battlebots.database import engine, session

Base = declarative_base()

NICKNAME_LENGTH = (1, 32)
PASSWORD_LENGTH = (1, 32)
BOTNAME_LENTGH = (1, 32)


class User(Base, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    nickname = db.Column(db.String(NICKNAME_LENGTH[1]), index=True,
                         unique=True, nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password = db.Column(db.String(120), index=True, nullable=False)

    def __repr__(self):
        return '<User {}>'.format(self.nickname)

    def __init__(self, nickname, email, password):
        self.nickname = nickname
        self.email = email
        self.set_password(password)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)


class Bot(Base):
    __tablename__ = 'bot'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = relationship(User, backref='bots')
    name = db.Column(db.String(BOTNAME_LENTGH[1]), nullable=False,
                     index=True, unique=True)
    matches = relationship('Match', secondary='match_participation',
                           back_populates='bots')
    compile_cmd = db.Column(db.String(200))
    run_cmd = db.Column(db.String(200), nullable=False)

    # These two fields can be filled in by the compiler/ranker/arbiter
    compile_errors = db.Column(db.Text)
    run_errors = db.Column(db.Text)
    # TODO make run_errors an association proxy to errors of MatchParticipation
    # objects

    def __repr__(self):
        return '<Bot {}>'.format(self.full_name)

    @property
    def code_path(self):
        return os.path.join(config.BOT_CODE_DIR, self.user.nickname, self.name)

    @property
    def full_name(self):
        """Return bot and owner name without spaces (but underscores)."""
        full_name_with_spaces = '{bot} ({owner})'.format(
            bot=self.name, owner=self.user.nickname)
        return re.sub(r'\s+', '_', full_name_with_spaces)

    def compile(self, timeout=20):
        """Return True if compilation succeeds, False otherwise."""

        # TODO run in sandbox & async
        # TODO set some "already compiled" flag so we don't compile each time
        with _in_dir(self.code_path):
            try:
                sp.run(self.compile_cmd, stdout=sp.PIPE, stderr=sp.PIPE,
                       shell=True, check=True, timeout=timeout)
                return True
            except sp.SubprocessError as error:
                self.compile_errors = str(error)
                self.compile_errors += 'STDOUT:\n' + error.stdout
                self.compile_errors += 'STDERR:\n' + error.stderr
                return False

    @property
    def sandboxed_run_cmd(self):
        # TODO
        return 'cd "%s" && %s' % (self.code_path, self.run_cmd)

    @property
    def win_percentage(self):
        all_matches = len(self.matches)
        if all_matches is not 0:
            won_matches = len(self.matches_won)
            return round(won_matches / all_matches * 100, 2)
        else:
            return None


class Match(Base):
    __tablename__ = 'match'
    id = db.Column(db.Integer, primary_key=True)
    bots = relationship(Bot, secondary='match_participation',
                        back_populates='matches')
    winner_id = db.Column(db.Integer, db.ForeignKey('bot.id'))
    winner = relationship(Bot, backref='matches_won')
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        return '<Match between {bots}; {winner} won; log: {logfile}>'.format(
            bots=self.bots, winner=self.winner, logfile=self.logfile)

    @property
    def log_path(self):
        return os.path.join(config.MATCH_LOG_DIR, str(self.id))

    def save_log(self, content):
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        with open(self.log_path, 'w') as logfile:
            logfile.write(content)


class MatchParticipation(Base):
    __tablename__ = 'match_participation'
    match_id = db.Column(db.Integer, db.ForeignKey('match.id'),
                         primary_key=True)
    bot_id = db.Column(db.Integer, db.ForeignKey('bot.id'), primary_key=True)

    match = relationship(Match, backref=backref('participations',
                                                cascade='all, delete-orphan'))
    bot = relationship(Bot, backref=backref('participations',
                                            cascade='all, delete-orphan'))

    errors = db.Column(db.Text)

    def __repr__(self):
        return ('<MatchParticipation of {bot} in {match}; errors: {errors}>'
                .format(bot=self.bot, match=self.match, errors=self.errors))


def add_bot(user, form):
    # Save code to <BOT_CODE_DIR>/<user>/<botname>/<codename>
    files = request.files.getlist('files')
    parent = os.path.join(config.BOT_CODE_DIR, user.nickname,
                          form.botname.data)
    os.makedirs(parent, exist_ok=True)

    #  TODO replace files
    for file in files:
        filename = secure_filename(file.filename)
        code_path = os.path.join(parent, filename)
        file.save(code_path)

    bot = Bot(user=user, name=form.botname.data,
              compile_cmd=form.compile_cmd.data, run_cmd=form.run_cmd.data)

    session.add(bot)
    session.commit()


def remove_bot(user, botname):
    code_dir = os.path.join(config.BOT_CODE_DIR, user.nickname, botname)
    try:
        shutil.rmtree(code_dir)
    except FileNotFoundError:
        # Don't crash if for some reason this dir doesn't exist anymore
        logging.warning('Code dir of bot %s:%s not found (%s)'
                        % (user.nickname, botname, code_dir))
        pass

    bot = session.query(Bot).filter_by(user=user, name=botname).one()
    session.delete(bot)
    session.commit()


@contextmanager
def _in_dir(directory):
    prev_dir = os.getcwd()
    os.chdir(directory)
    yield
    os.chdir(prev_dir)


Base.metadata.create_all(engine)
