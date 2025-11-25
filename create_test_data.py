"""Create test data for SubTUI."""

import uuid
from datetime import datetime, timedelta

from sub_tui.database import Database
from sub_tui.models import (
    Action,
    ActionStatus,
    AgendaItem,
    AgendaStatus,
    Meeting,
    Note,
    RecurrencePattern,
    Subject,
    SubjectType,
)


def create_test_data():
    """Create sample data for testing."""
    db = Database()

    # Create test subjects
    subjects = [
        Subject(
            id=str(uuid.uuid4()),
            name="Engineering Team",
            code="ENG",
            type=SubjectType.TEAM,
            description="Software engineering team",
            created_at=datetime.now() - timedelta(days=30),
            last_reviewed_at=datetime.now() - timedelta(days=2),
        ),
        Subject(
            id=str(uuid.uuid4()),
            name="Product Roadmap",
            code="PRD",
            type=SubjectType.BOARD,
            description="Product planning and roadmap",
            created_at=datetime.now() - timedelta(days=60),
            last_reviewed_at=datetime.now() - timedelta(days=5),
        ),
        Subject(
            id=str(uuid.uuid4()),
            name="John Doe",
            type=SubjectType.PERSON,
            description="Senior Developer",
            created_at=datetime.now() - timedelta(days=90),
            last_reviewed_at=datetime.now() - timedelta(days=1),
        ),
    ]

    for subject in subjects:
        db.add_subject(subject)

    # Create actions for Engineering Team
    eng_subject = subjects[0]
    actions = [
        Action(
            id=str(uuid.uuid4()),
            subject_id=eng_subject.id,
            title="Review pull request #123",
            description="Code review for authentication feature",
            status=ActionStatus.TODO,
            due_date=datetime.now(),  # Today
            created_at=datetime.now() - timedelta(days=1),
            tags=["code-review", "urgent"],
        ),
        Action(
            id=str(uuid.uuid4()),
            subject_id=eng_subject.id,
            title="Fix bug in login flow",
            description="Users cannot login with email",
            status=ActionStatus.IN_PROGRESS,
            due_date=datetime.now() - timedelta(days=1),  # Overdue
            created_at=datetime.now() - timedelta(days=3),
            tags=["bug", "urgent"],
        ),
        Action(
            id=str(uuid.uuid4()),
            subject_id=eng_subject.id,
            title="Update dependencies",
            description="Update npm packages to latest versions",
            status=ActionStatus.TODO,
            due_date=datetime.now() + timedelta(days=3),  # This week
            created_at=datetime.now() - timedelta(days=5),
            tags=["maintenance"],
        ),
        Action(
            id=str(uuid.uuid4()),
            subject_id=eng_subject.id,
            title="Write unit tests",
            description="Add tests for payment module",
            status=ActionStatus.TODO,
            due_date=datetime.now() + timedelta(days=10),  # Next week
            created_at=datetime.now() - timedelta(days=2),
            tags=["testing"],
        ),
    ]

    for action in actions:
        db.add_action(action)

    # Create actions for Product Roadmap
    prd_subject = subjects[1]
    prd_actions = [
        Action(
            id=str(uuid.uuid4()),
            subject_id=prd_subject.id,
            title="Prepare Q1 roadmap presentation",
            status=ActionStatus.TODO,
            due_date=datetime.now() + timedelta(days=1),  # This week
            created_at=datetime.now() - timedelta(days=7),
            tags=["presentation"],
        ),
        Action(
            id=str(uuid.uuid4()),
            subject_id=prd_subject.id,
            title="Gather user feedback",
            status=ActionStatus.IN_PROGRESS,
            due_date=datetime.now() + timedelta(days=5),  # This week
            created_at=datetime.now() - timedelta(days=10),
            tags=["research", "ux"],
        ),
    ]

    for action in prd_actions:
        db.add_action(action)

    # Create agenda items for Engineering Team
    agenda_items = [
        AgendaItem(
            id=str(uuid.uuid4()),
            subject_id=eng_subject.id,
            title="Sprint retrospective topics",
            priority=8,
            status=AgendaStatus.ACTIVE,
            created_at=datetime.now() - timedelta(days=5),
            is_recurring=True,
            recurrence_pattern=RecurrencePattern.WEEKLY,
        ),
        AgendaItem(
            id=str(uuid.uuid4()),
            subject_id=eng_subject.id,
            title="Discuss new architecture proposal",
            priority=9,
            status=AgendaStatus.ACTIVE,
            created_at=datetime.now() - timedelta(days=3),
        ),
        AgendaItem(
            id=str(uuid.uuid4()),
            subject_id=eng_subject.id,
            title="Code review process improvements",
            priority=5,
            status=AgendaStatus.ACTIVE,
            created_at=datetime.now() - timedelta(days=10),
        ),
    ]

    for item in agenda_items:
        db.add_agenda_item(item)

    # Create a meeting
    meeting = Meeting(
        id=str(uuid.uuid4()),
        subject_id=eng_subject.id,
        date=datetime.now() - timedelta(days=7),
        attendees=["Alice", "Bob", "Charlie"],
        content="""## Sprint Planning

### My Agenda Items

#### Sprint retrospective topics
- Discussed blockers from last sprint
- **Decision**: Implement daily standups
- **Action**: Update team calendar

### Topics Raised by Others

#### CI/CD improvements (raised by Bob)
- Current pipeline is slow
- **Decision**: Investigate GitHub Actions
- **Action**: Bob to create POC
""",
        created_at=datetime.now() - timedelta(days=7),
        updated_at=datetime.now() - timedelta(days=7),
    )

    db.add_meeting(meeting)

    # Create a note
    note = Note(
        id=str(uuid.uuid4()),
        subject_id=eng_subject.id,
        title="Team Guidelines",
        content="""# Engineering Team Guidelines

## Code Review Process

1. All PRs require at least 2 approvals
2. Use conventional commits
3. Update tests and documentation

## Communication

- Use Slack for quick questions
- Email for important announcements
- Weekly team meeting on Mondays
""",
        tags=["guidelines", "onboarding"],
        created_at=datetime.now() - timedelta(days=20),
        updated_at=datetime.now() - timedelta(days=15),
    )

    db.add_note(note)

    db.close()

    print("✅ Test data created successfully!")
    print(f"Created {len(subjects)} subjects")
    print(f"Created {len(actions) + len(prd_actions)} actions")
    print(f"Created {len(agenda_items)} agenda items")
    print("Created 1 meeting and 1 note")


if __name__ == "__main__":
    create_test_data()
