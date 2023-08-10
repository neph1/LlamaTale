"""
Player account code.

'Tale' mud driver, mudlib and interactive fiction framework
Copyright by Irmen de Jong (irmen@razorvine.net)
"""

import datetime
import hashlib
import random
import re
import sqlite3
import time
import json
from typing import Set, Tuple, List, Dict, Any, Optional
import serpent

from . import base
from . import lang
from . import mud_context
from . import player
from . import util

__all__ = ["Account", "MudAccounts"]


class Account:
    def __init__(self, name: str, email: str, pw_hash: str, pw_salt: str, privileges: Set[str],
                 created: datetime.datetime, logged_in: Optional[datetime.datetime], banned: bool,
                 stats: base.Stats, story_data: Dict[Any, Any]) -> None:
        # validation on the suitability of names, emails etc is taken care of by the creating code
        if not isinstance(stats, base.Stats):
            raise TypeError("stats must be of type Stats")
        self.name = name
        self.email = email
        self.pw_hash = pw_hash
        self.pw_salt = pw_salt
        self.privileges = privileges or set()  # simply a set of strings
        self.created = created
        self.logged_in = logged_in
        self.stats = stats
        self.banned = banned
        self.story_data = story_data


class MudAccounts:
    """
    Handles the accounts (login, creation, etc) of mud users

    Database:
        account(name, email, pw_hash, pw_salt, created, logged_in, locked)
        privilege(account, privilege)
        charstat(account, gender, stat1, stat2,...)
    """

    def __init__(self, databasefile: str) -> None:
        self.sqlite_dbpath = databasefile
        self._create_database()

    def _sqlite_connect(self) -> sqlite3.Connection:
        urimode = self.sqlite_dbpath.startswith("file:")
        conn = sqlite3.connect(self.sqlite_dbpath, detect_types=sqlite3.PARSE_DECLTYPES, timeout=5, uri=urimode)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def _create_database(self) -> None:
        try:
            with self._sqlite_connect() as conn:
                table_exists = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Account'").fetchone()
                if not table_exists:
                    print("%s: Creating new user accounts database." % mud_context.config.name)
                    print("Location:", self.sqlite_dbpath, "\n")
                    # create the schema
                    conn.execute("""
                        CREATE TABLE Account(
                            id integer PRIMARY KEY,
                            name varchar NOT NULL,
                            email varchar NOT NULL,
                            pw_hash varchar NOT NULL,
                            pw_salt varchar NOT NULL,
                            created timestamp NOT NULL,
                            logged_in timestamp NULL,
                            banned integer NOT NULL
                        );""")
                    conn.execute("CREATE INDEX idx_account_name ON Account(name)")
                    conn.execute("""
                        CREATE TABLE Privilege(
                            id integer PRIMARY KEY,
                            account integer NOT NULL,
                            privilege varchar NOT NULL,
                            FOREIGN KEY(account) REFERENCES Account(id)
                        );""")
                    conn.execute("CREATE INDEX idx_privilege_account ON Privilege(account)")
                    conn.execute("""
                        CREATE TABLE CharStat(
                            id integer PRIMARY KEY,
                            account integer NOT NULL,
                            gender char(1) NOT NULL,
                            race varchar NULL,
                            level integer NOT NULL,
                            xp integer NOT NULL,
                            hp integer NOT NULL,
                            ac integer NOT NULL,
                            wc integer NOT NULL,
                            maxhp_dice varchar NULL,
                            attack_dice varchar NULL,
                            alignment integer NOT NULL,
                            strength integer NOT NULL,
                            dexterity integer NOT NULL,
                            FOREIGN KEY(account) REFERENCES Account(id)
                        );
                        """)
                    conn.execute("""
                        CREATE TABLE StoryData(
                            id integer PRIMARY KEY,
                            account integer NOT NULL,
                            format varchar NOT NULL,
                            data varchar NOT NULL,
                            FOREIGN KEY(account) REFERENCES Account(id)
                        );
                        """)
                    # note: stats not stored in the database are the following:
                    #       bodytype, language, weight, and size.
                    #       Those are all static and will be initialized from the races table.
                    conn.commit()
        except sqlite3.Error as x:
            print("%s: Can't open or create the user accounts database." % mud_context.config.name)
            print("Location:", self.sqlite_dbpath)
            print("Error:", repr(x))
            raise SystemExit("Cannot launch mud mode without a user accounts database.")

    def get(self, name: str) -> Account:
        with self._sqlite_connect() as conn:
            result = conn.execute("SELECT id FROM Account WHERE name=?", (name,)).fetchone()
            if not result:
                raise LookupError(name)
            return self._fetch_account(conn, result["id"])

    def _fetch_account(self, conn: sqlite3.Connection, account_id: int) -> Account:
        acc = conn.execute("SELECT * FROM Account WHERE id=?", (account_id,)).fetchone()
        priv_result = conn.execute("SELECT privilege FROM Privilege WHERE account=?", (account_id,)).fetchall()
        privileges = {pr["privilege"] for pr in priv_result}
        storydata_result = conn.execute("SELECT format, data FROM StoryData WHERE account=?", (account_id,)).fetchone()
        if storydata_result:
            if storydata_result["format"] == "json":
                storydata = json.loads(storydata_result["data"], encoding="utf-8")
            elif storydata_result["format"] == "serpent":
                storydata = serpent.loads(storydata_result["data"])
            else:
                raise ValueError("invalid storydata format in database: " + storydata_result["format"])
            if not isinstance(storydata, dict):
                raise TypeError("storydata should be a dict")
        else:
            storydata = {}
        stats_result = dict(conn.execute("SELECT * FROM CharStat WHERE account=?", (account_id,)).fetchone() or {})
        del stats_result["id"]
        del stats_result["account"]
        stats = base.Stats()
        for key, value in stats_result.items():
            if hasattr(stats, key):
                setattr(stats, key, value)
            else:
                raise AttributeError("stats doesn't have attribute: " + key)
        stats.set_stats_from_race()   # initialize static stats from races table
        return Account(acc["name"], acc["email"], acc["pw_hash"], acc["pw_salt"], privileges,
                       acc["created"], acc["logged_in"], bool(acc["banned"]), stats, storydata)

    def all_accounts(self, having_privilege: str="") -> List[Account]:
        with self._sqlite_connect() as conn:
            if having_privilege:
                result = conn.execute("SELECT a.id FROM Account a INNER JOIN Privilege p ON p.account=a.id AND p.privilege=? "
                                      "ORDER BY a.name",  (having_privilege,)).fetchall()
            else:
                result = conn.execute("SELECT id FROM Account ORDER BY name").fetchall()
            account_ids = [ar["id"] for ar in result]
            accounts = [self._fetch_account(conn, account_id) for account_id in account_ids]
            return accounts

    def logged_in(self, name: str) -> None:
        timestamp = datetime.datetime.now().replace(microsecond=0)
        with self._sqlite_connect() as conn:
            conn.execute("UPDATE Account SET logged_in=? WHERE name=?", (timestamp, name))

    def valid_password(self, name: str, password: str) -> None:
        with self._sqlite_connect() as conn:
            result = conn.execute("SELECT pw_hash, pw_salt FROM Account WHERE name=?", (name,)).fetchone()
        if result:
            stored_hash, stored_salt = result["pw_hash"], result["pw_salt"]
            pwhash, _ = self._pwhash(password, stored_salt)
            if pwhash == stored_hash:
                return
        raise ValueError("Invalid name or password.")

    @staticmethod
    def _pwhash(password: str, salt: str="") -> Tuple[str, str]:
        if not salt:
            salt = str(random.random() * time.time() + id(password)).replace('.', '')
        pwhash = hashlib.sha1((salt + password).encode("utf-8")).hexdigest()
        return pwhash, salt

    @staticmethod
    def accept_password(password: str) -> str:
        if len(password) >= 6:
            if re.search("[a-zA-z]", password) and re.search("[0-9]", password):
                return password
        raise ValueError("Password should be minimum length 6, contain letters, at least one number, and optionally other characters.")

    @staticmethod
    def accept_name(name: str) -> str:
        if re.match("[a-z]{3,16}$", name):
            if name in MudAccounts.blocked_names:
                raise ValueError("That name is not available.")
            return name
        raise ValueError("Name should be all lowercase letters [a-z] and length 3 to 16.")

    @staticmethod
    def accept_email(email: str) -> str:
        user, _, domain = email.partition("@")
        if user and domain and user.strip() == user and domain.strip() == domain:
            return email
        raise ValueError("Invalid email address.")

    @staticmethod
    def accept_privilege(priv: str) -> None:
        if priv not in {"wizard"}:
            raise ValueError("Invalid privilege: " + priv)

    def create(self, name: str, password: str, email: str, stats: base.Stats, privileges: Set[str]=set()) -> Account:
        name = name.strip()
        email = email.strip()
        lang.validate_gender(stats.gender)
        if not stats.language:
            raise ValueError("cannot create an account with un-initialized stats")
        self.accept_name(name)
        self.accept_password(password)
        self.accept_email(email)
        privileges = {p.strip() for p in privileges}
        for p in privileges:
            self.accept_privilege(p)
        created = datetime.datetime.now().replace(microsecond=0)
        pwhash, salt = self._pwhash(password)
        with self._sqlite_connect() as conn:
            result = conn.execute("SELECT COUNT(*) FROM Account WHERE name=?", (name,)).fetchone()[0]
            if result > 0:
                raise ValueError("That name is not available.")
            result = conn.execute("INSERT INTO Account('name', 'email', 'pw_hash', 'pw_salt', 'created', 'banned') VALUES (?,?,?,?,?,?)",
                                  (name, email, pwhash, salt, created, 0))
            for privilege in privileges:
                conn.execute("INSERT INTO Privilege(account, privilege) VALUES (?,?)", (result.lastrowid, privilege))
            self._store_stats(conn, result.lastrowid, stats)
        return Account(name, email, pwhash, salt, privileges, created, None, False, stats, {})

    def _store_stats(self, conn: sqlite3.Connection, account_id: int, stats: base.Stats) -> None:
        columns = ["account"]
        values = [account_id]
        stat_vars = dict(vars(stats))
        for not_stored in ["bodytype", "language", "weight", "size"]:
            del stat_vars[not_stored]    # these are not stored, but always initialized from the races table
        for key, value in stat_vars.items():
            columns.append(key)
            values.append(value)
        sql = "INSERT INTO CharStat(" + ",".join(columns) + ") VALUES (" + ",".join('?' * len(columns)) + ")"
        conn.execute(sql, values)

    def change_password_email(self, name: str, old_password: str, new_password: str="", new_email: str="") -> None:
        self.valid_password(name, old_password)
        new_email = new_email.strip() if new_email else ""
        if new_password:
            self.accept_password(new_password)
        if new_email:
            self.accept_email(new_email)
        with self._sqlite_connect() as conn:
            result = conn.execute("SELECT id FROM Account WHERE name=?", (name,)).fetchone()
            if not result:
                raise LookupError("Unknown name.")
            account_id = result["id"]
            if new_password:
                pwhash, salt = self._pwhash(new_password)
                conn.execute("UPDATE Account SET pw_hash=?, pw_salt=? WHERE id=?", (pwhash, salt, account_id))
            if new_email:
                conn.execute("UPDATE Account SET email=? WHERE id=?", (new_email, account_id))

    def save_story_data(self, name: str, story_data: Dict[Any, Any]) -> None:
        if not isinstance(story_data, dict):
            raise TypeError("story data should be a dict")
        with self._sqlite_connect() as conn:
            result = conn.execute("SELECT id FROM Account WHERE name=?", (name,)).fetchone()
            if not result:
                raise LookupError("Unknown name.")
            account_id = result["id"]
            data = serpent.dumps(story_data)
            result = conn.execute("UPDATE StoryData SET format=?, data=? WHERE id=?", ("serpent", data, account_id))
            if result.rowcount == 0:
                # there's no storydata yet, insert it
                conn.execute("INSERT INTO StoryData(account, format, data) VALUES (?,?,?)", (account_id, "serpent", data))

    @util.authorized("wizard")
    def update_privileges(self, name: str, privileges: Set[str], actor: player.Player) -> Set[str]:
        privileges = {p.strip() for p in privileges}
        for p in privileges:
            self.accept_privilege(p)
        with self._sqlite_connect() as conn:
            result = conn.execute("SELECT id FROM Account WHERE name=?", (name,)).fetchone()
            if not result:
                raise LookupError("Unknown name.")
            account_id = result["id"]
            conn.execute("DELETE FROM Privilege WHERE account=?", (account_id,))
            for privilege in privileges:
                conn.execute("INSERT INTO Privilege(account, privilege) VALUES (?,?)", (account_id, privilege))
        return privileges

    @util.authorized("wizard")
    def ban(self, name: str, actor: player.Player) -> None:
        with self._sqlite_connect() as conn:
            updated = conn.execute("UPDATE Account SET banned=1 WHERE name=?", (name,)).rowcount
            if updated == 0:
                raise LookupError("Unknown name.")

    @util.authorized("wizard")
    def unban(self, name: str, actor: player.Player) -> None:
        with self._sqlite_connect() as conn:
            updated = conn.execute("UPDATE Account SET banned=0 WHERE name=?", (name,)).rowcount
            if updated == 0:
                raise LookupError("Unknown name.")

    blocked_names = """irmen
me
you
us
them
they
their
theirs
he
him
his
she
her
hers
it
its
yes
no
god
allah
jesus
jezus
hitler
neuk
fuck
cunt
cock
prick
pik
lul
kut
dick
pussy
twat
cum
milf
anal
sex
ass
asshole
neger
nigger
nigga
jew
muslim
moslim
binladen
chink
cancer
kanker
typhus
tering
soa
aids
bitch
motherfucker
fucker
""".split()
