"""Request-scoped organization filtering; worker requests use explicit job ownership."""
from sqlalchemy import event
from sqlalchemy.orm import Session, with_loader_criteria
from .models import OrgScoped

@event.listens_for(Session, 'do_orm_execute')
def scope_reads(execution):
    org = execution.session.info.get('org_id')
    if org and execution.is_select:
        execution.statement = execution.statement.options(
            with_loader_criteria(OrgScoped, lambda cls: cls.org_id == org, include_aliases=True))

@event.listens_for(Session, 'before_flush')
def scope_writes(db, context, instances):
    org = db.info.get('org_id')
    if not org:
        return
    for obj in db.new | db.dirty | db.deleted:
        if isinstance(obj, OrgScoped):
            if obj in db.new and obj.org_id is None:
                obj.org_id = org
            if obj.org_id != org:
                raise ValueError('Cross-organization write rejected')
