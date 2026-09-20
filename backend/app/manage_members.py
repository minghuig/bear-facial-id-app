"""Operator-only invite management: python -m app.manage_members invite ORG EMAIL."""
import argparse
from sqlalchemy import delete
from .db import Session
from .models import Organization, Membership, LoginSession, User

def main():
    p = argparse.ArgumentParser()
    p.add_argument('action', choices=['invite','remove','lookup-sub'])
    p.add_argument('org', choices=['internal-testing','mcneil'])
    p.add_argument('email')
    a = p.parse_args()
    email = a.email.strip().lower()
    if '@' not in email:
        p.error('A Google account email is required')
    with Session.begin() as db:
        if not db.get(Organization,a.org):
            p.error('Run database migrations first')
        member = db.get(Membership, (a.org,email))
        if a.action == 'lookup-sub':
            if member is None or member.user_id is None:
                p.error('This member must sign in before their Google sub can be looked up')
            print(db.get(User, member.user_id).google_sub)
            return
        if a.action == 'invite' and member is None:
            db.add(Membership(org_id=a.org,email=email))
        elif a.action == 'remove' and member is not None:
            if member.user_id:
                db.execute(delete(LoginSession).where(LoginSession.user_id==member.user_id,LoginSession.org_id==a.org))
            db.delete(member)
    print('Membership updated')

if __name__ == '__main__':
    main()
