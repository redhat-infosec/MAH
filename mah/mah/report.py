"""
Enable sending of suspicious authentication reports to administrators.
"""
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
from mah.verification import Verification
from mah.config import config
from mah.log import log

_message_body = """
The following suspicious MAH authentication interaction has been reported:

Report date: {time} UTC
Reported by (uid): {reporter}
Suspicious authentication:
{auth}

*** Start Report ***
{report}
*** End Report ***


Please investigate and take appropriate action.

"""[1:]

def email_report(text, reporter_uid, auth):
    """
    A email a report of a suspicious authentication interaction.
    The destination email address, from address, subject and mail server is
    read from a configuration file.

    :param text: the text of the report
    :param reporter_uid: the uid (user id) of the reporter
    :param auth: the authentication id (a uniquely identifying int)
    """
    msg = MIMEText(_message_body.format(
        time=str(datetime.utcnow()),
        reporter=reporter_uid,
        auth=str(Verification.by_id(auth)),
        report=text
    ))
    msg['Subject'] = config.report.email_subject
    msg['To'] = ', '.join(config.report.email_to)
    msg['From'] = config.report.email_from
    try:
        s = smtplib.SMTP(config.report.smtp_server)
        s.sendmail(
            config.report.email_from,
            config.report.email_to,
            msg.as_string()
        )
        s.quit()
        log.info(
            'Emailed suspicious interaction '
            'report {src} to {dst} via {server}'.format(
                src=config.report.email_from,
                dst=', '.join(config.report.email_to),
                server=config.report.smtp_server
            )
        )
    except Exception:
        log.error('Failed to send suspicious interaction report via email.')
        raise
