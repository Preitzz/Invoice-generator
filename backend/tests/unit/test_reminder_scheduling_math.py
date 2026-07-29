from datetime import date, timedelta

from app.core.timezone import ist_end_of_day
from app.services import invoices as invoice_service
from app.services import reminders as reminder_service
from tests.factories import make_line_item


def test_compute_schedule_returns_five_offsets(db_session):
    due = date.today() + timedelta(days=20)
    schedule = reminder_service.compute_schedule(db_session, due)
    assert len(schedule) == 5
    offsets = sorted(rule.offset_days for rule, _ in schedule)
    assert offsets == [-3, 0, 7, 14, 30]

    anchor = ist_end_of_day(due)
    for rule, scheduled_for in schedule:
        assert scheduled_for == anchor + timedelta(days=rule.offset_days)


def test_issuing_invoice_schedules_five_reminder_instances(db_session, customer, admin_user, active_tax_rate):
    from app.models.reminder_instance import ReminderInstance, ReminderInstanceStatus

    draft = invoice_service.create_draft_invoice(
        db_session,
        customer_id=customer.id,
        due_date=date.today() + timedelta(days=15),
        line_items=[make_line_item()],
        actor_id=admin_user.id,
    )
    issued = invoice_service.issue_invoice(db_session, draft.id, actor_id=admin_user.id)

    instances = (
        db_session.query(ReminderInstance).filter(ReminderInstance.invoice_id == issued.id).all()
    )
    assert len(instances) == 5
    assert all(ri.status == ReminderInstanceStatus.scheduled for ri in instances)


def test_due_date_edit_recalculates_scheduled_but_not_sent_instances(
    db_session, customer, admin_user, active_tax_rate
):
    from app.models.reminder_instance import ReminderInstance, ReminderInstanceStatus

    draft = invoice_service.create_draft_invoice(
        db_session,
        customer_id=customer.id,
        due_date=date.today() + timedelta(days=15),
        line_items=[make_line_item()],
        actor_id=admin_user.id,
    )
    issued = invoice_service.issue_invoice(db_session, draft.id, actor_id=admin_user.id)

    instances = (
        db_session.query(ReminderInstance).filter(ReminderInstance.invoice_id == issued.id).all()
    )
    # Simulate one already-sent reminder.
    sent_instance = instances[0]
    sent_instance.status = ReminderInstanceStatus.sent
    original_sent_scheduled_for = sent_instance.scheduled_for
    db_session.flush()
    db_session.commit()

    new_due_date = date.today() + timedelta(days=25)
    invoice_service.update_invoice(db_session, issued.id, actor_id=admin_user.id, due_date=new_due_date)

    db_session.refresh(sent_instance)
    assert sent_instance.scheduled_for == original_sent_scheduled_for  # untouched

    still_scheduled = [
        ri
        for ri in db_session.query(ReminderInstance).filter(ReminderInstance.invoice_id == issued.id)
        if ri.status == ReminderInstanceStatus.scheduled
    ]
    assert len(still_scheduled) == 4
    expected_anchor = ist_end_of_day(new_due_date)
    for ri in still_scheduled:
        expected = expected_anchor + timedelta(days=ri.rule.offset_days)
        assert ri.scheduled_for == expected
