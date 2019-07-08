from mah import app
from mah.config import config
from mah.log import log
from mah.database import database as db
from mah.verification import Verification
from mah.report import email_report
from flask import (
    request, session, flash, url_for, render_template, make_response, redirect
)
from traceback import format_exc
import time, re

def go_home():
    return redirect(url_for('index'))

@app.before_request
def check_authentication():
    # Don't interfere with unauthenticated routes
    if (request.endpoint is None or
        request.endpoint in app.unauthenticated_routes):
        return
    if 'username' not in session or not session.get('logged_in', False):
        log.debug(
            u"{endpoint} requested without a valid session. "
            u"Redirecting to login.".format(endpoint=request.endpoint)
        )
        return redirect(url_for('login'))
    elif session.get('timeout', 0.0) < time.time():
        session['logged_in'] = False
        flash('Your session has expired, please login again.')
        log.info(u'Session expired for user {user}.'.format(
            user=session['username']
        ))
        return redirect(url_for('login'))

@app.after_request
def update_session(response):
    if 'username' in session:
        session['timeout'] = time.time() + config.application.session_timeout
    return response

@app.csrf.exempt
@app.unauthenticated_route('/login', methods=['GET', 'POST'])
def login():
    """
    A form (GET) and the assocaited handler (POST) for validation of user
    credentials.

    It is possible to put the application in testing mode, so that password
    checks are not enforced and the user only need supply a username. This
    should never be enabled in production. (See also: check_password and
    use_radius :doc:`configuration` options.)

    Otherwise, the users authentication credentials will be authenticated
    using the configured authentication module.
    """
    auth = config.login.module.Authentication
    if request.method == 'GET' and session.get('logged_in', False):
        # Login attempt while logged in - just redirect home
        return go_home()
    elif request.method == 'POST':
        session['timeout'] = time.time() + config.application.session_timeout
        session['username'], session['logged_in'] = auth.authenticate(
            request.form
        )
        if session['logged_in']:
            log.info(
                "Authentication successful ({type}) for "
                "user {user} from {ip}".format(
                    type=config.login.type,
                    user=session['username'],
                    ip=request.remote_addr
                )
            )
            flash("Welcome {user}.".format(user=session['username']))
            return go_home()
        else:
            log.info(
                "Authentication failure ({type}) for "
                "user {user} from {ip}".format(
                    type=config.login.type,
                    user=session['username'],
                    ip=request.remote_addr
                )
            )
            flash("Login failed.")
    return render_template(
        'login.html',
        inputs=auth.template_inputs(),
        warning=not auth.for_production()
    )

@app.route('/')
def index():
    """
    The main index/default page. It shows authentication for
    this user, both as the source and the destination (if they exist) and a
    search option.

    If the configuration is bad, only display an error page
    """
    src_auths = Verification.by_src(session['username'])
    dst_auths = Verification.by_dst(session['username'])
    log.debug(
        u'index called by user {user} - auths as source '
        u'({src}) and destination ({dst})'.format(
            user=session['username'],
            src=len(src_auths),
            dst=len(dst_auths)
        )
    )
    response = make_response(
        render_template('index.html', src_auths=src_auths, dst_auths=dst_auths)
    )
    response.headers['Refresh'] = config.application.refresh
    db.done(True)
    return response

@app.route('/auth', methods=['POST'])
def authenticate():
    """
    A form handler which creates an authentication for the existing user
    (determined via the 'username' term of session) to another user
    (accepted as a form input variable). On success, it returns a page,
    showing the user details of the newly created authentication.

    It has several logic checks, which may cause and error (or abort):

    * The source and destination uid are not identical.
    * The authentication doesn't already exist, that is, a non-expired
      authentication with the same source and destination is not already
      present.
    * There is also a check (within the authentication code) that will
      cause and exception if the destination is not within the staff
      directory. This should only occur if the client is tampering with
      the request variables, not through valid use of this app.

    """
    # The following conversions to have been implemented as a
    # workaround to the limitations in the python-ldap library
    # which appears to not correctly handle UTF8
    src = session['username'].encode('ascii', 'ignore')
    if 'authselect' in request.form:
        dst = request.form['authselect'].encode('ascii','ignore')
    else:
        flash(u"No user selected to authenticate.")
        return go_home()
    if src == dst:
        log.debug(
            u'Illegal authenication attempted with identical '
            u'source ({src}) and destination ({dst})'.format(
                src=src,
                dst=dst
            )
        )
        flash(u"You can't authenticate yourself.")
        return go_home()
    if Verification.exists(src, dst):
        log.debug(
            u'Duplicate authentication attempted with '
            u'source ({src}) and destination ({dst})'.format(
                src=src,
                dst=dst
            )
        )
        flash("Authentication already exists.")
        return go_home()
    log.info(u'Authentication created by {src} for {dst} from {ip}'.format(
        src=src,
        dst=dst,
        ip=request.remote_addr
    ))
    try:
        verification = Verification(src, dst)
        db.session.add(verification) # pylint: disable=E1101
    except Exception:
        log.error("Authentication creation error: {trace}".format(
            trace=format_exc()
        ))
        db.done(False)
        flash('Failed to create authentication! Please try again later.')
        return go_home()
    response = make_response(render_template('auth.html', auth=verification))
    db.done(True)
    response.headers['Refresh'] = (
        '{refresh}; {url}'.format(
            refresh=config.application.refresh, url=url_for('index')
        )
    )
    return response

@app.route('/search', methods=['GET', 'POST'])
def search():
    """
    The method displays a search form (GET) and searches the staff
    directory for a user (POST) and returns the results to the user. The
    initial implmentation uses LDAP as the staff directory server.
    """
    if request.method == 'POST':
        search = request.form['searchstr'].strip()
        if len(search) > 2 and re.match(r'^[a-zA-Z0-9\s]+\Z', search):
            staff = config.directory.module.Directory()
            res = staff.search(search)
            log.debug(
                u"user {user} searched for string '{search}', which "
                u"matched {count} directory record(s)".format(
                    user=session['username'],
                    search=search,
                    count=len(res)
                )
            )
        else:
            log.info(
                u"user {user} searched for illegal string '{search}'".format(
                    user=session['username'],
                    search=search
                )
            )
            res = []
            search = ''
            flash(u"Search words must be longer than 2 "
                  u"characters and only contain alpha-numeric " +
                  u"characters (0-9a-zA-Z) and white space")
        return render_template(
            'search.html',
            search=search,
            results=res,
            attribute_names=config.directory.attribute_names
        )
    else:
        return render_template('search.html')

@app.route('/report', methods=['GET', 'POST'])
def report():
    """
    This method provides a facility for users to report authentication
    interactions which they consider suspicious. The results are logged and
    emailed to a configurable address.
    """
    if request.method == 'GET':
        rep_auth, all_auths = None, None
        if 'auth_id' in request.args:
            rep_auth_id = request.args['auth_id']
            if not rep_auth_id.isdigit() and int(rep_auth_id) < 0:
                raise Exception(
                    'non-positive integer auth_id provided to report method'
                )
            rep_auth = Verification.by_id(rep_auth_id)
        if rep_auth is None:
            all_auths = Verification.all(session['username'])
        response = render_template(
            'report.html', auth=rep_auth, all_auths=all_auths
        )
    else:
        reason = request.form['reason']
        report = request.form['reported_auth_id']
        log.info(
            u"user {user} reported authentication with "
            u"id '{report}' as suspicious with reason: {reason}".format(
                user=session['username'],
                report=report,
                reason=re.sub(r'[\n\r]+', ' ', reason)
            )
        )
        email_report(reason, session['username'], report)
        response = render_template('report-submitted.html')
    db.done(True)
    return response

@app.route('/logout')
def logout():
    """
    Log out from the application which de-authenticates the session then
    redirects back to the index page.

    Attempts to go to the logout page without already having logged in will
    redirect to /login
    """
    if 'username' in session:
        session['logged_in'] = False
        log.info(u"Logout of user {user}.".format(
            user=session.pop('username')
        ))
        flash('You have been logged out')
    return go_home()

@app.unauthenticated_route('/help')
def help():
    """
    Display the online help page. This is available to un-authenticated
    users.
    """
    return render_template('help.html')
