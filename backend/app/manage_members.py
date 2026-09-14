"""Operator-only invite management: python -m app.manage_members invite ORG EMAIL."""
import argparse
from sqlalchemy import select, delete
from .db import Session
from .models import Organization, Membership, LoginSession

def main():
    p = argparse.ArgumentParser()
    p.add_argument('action', choices=['invite','remove'])
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
        if a.action == 'invite' and member is None:
            db.add(Membership(org_id=a.org,email=email))
        elif a.action == 'remove' and member is not None:
            if member.user_id:
                db.execute(delete(LoginSession).where(LoginSession.user_id==member.user_id,LoginSession.org_id==a.org))
            db.delete(member)
    print('Membership updated')

if __name__ == '__main__':
    main()
