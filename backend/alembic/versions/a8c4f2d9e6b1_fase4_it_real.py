"""fase4 it real

Revision ID: a8c4f2d9e6b1
Revises: f3a7c9d2e1b0
Create Date: 2026-05-25
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a8c4f2d9e6b1"
down_revision: Union[str, None] = "f3a7c9d2e1b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    inspector = sa.inspect(bind)
    json_type = "JSONB" if dialect == "postgresql" else "JSON"
    text_type = "TEXT"
    now_expr = "CURRENT_TIMESTAMP"
    bool_true = "TRUE" if dialect == "postgresql" else "1"
    bool_false = "FALSE" if dialect == "postgresql" else "0"

    def execute(sql: str) -> None:
        op.execute(sa.text(sql))

    if dialect == "postgresql" and inspector.has_table("it_tickets"):
        execute("ALTER TABLE IF EXISTS it_tickets RENAME COLUMN requester_id TO requester_user_id")
        execute("ALTER TABLE IF EXISTS it_tickets RENAME COLUMN assignee_id TO assigned_to_user_id")
        execute("ALTER TABLE IF EXISTS it_tickets RENAME COLUMN card_id TO kanban_card_id")

        ticket_columns = [
            ("ticket_number", "VARCHAR(20)"),
            ("category", "VARCHAR(40) DEFAULT 'OUTRO' NOT NULL"),
            ("suspension_reason", "VARCHAR(40)"),
            ("sla_policy_id", "INTEGER"),
            ("due_at", "TIMESTAMP"),
            ("first_response_at", "TIMESTAMP"),
            ("resolved_at", "TIMESTAMP"),
        ]
        for name, ddl in ticket_columns:
            execute(f"ALTER TABLE IF EXISTS it_tickets ADD COLUMN IF NOT EXISTS {name} {ddl}")
        execute("CREATE SEQUENCE IF NOT EXISTS it_ticket_number_seq")
        execute(
            """
            UPDATE it_tickets
            SET ticket_number = 'TI-' || lpad(nextval('it_ticket_number_seq')::text, 6, '0')
            WHERE ticket_number IS NULL
            """
        )
        execute("ALTER TABLE IF EXISTS it_tickets ALTER COLUMN ticket_number SET NOT NULL")
        execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_it_tickets_ticket_number ON it_tickets(ticket_number)")

    if dialect == "postgresql" and inspector.has_table("it_certificates"):
        execute("ALTER TABLE IF EXISTS it_certificates RENAME COLUMN expiration_date TO expires_at")
    else:
        # SQLite de desenvolvimento/teste cria as tabelas por Base.metadata.
        pass

    execute(
        f"""
        CREATE TABLE IF NOT EXISTS it_sla_policies (
            id INTEGER PRIMARY KEY,
            name VARCHAR NOT NULL,
            category VARCHAR(40),
            priority VARCHAR(20) NOT NULL DEFAULT 'MEDIA',
            response_minutes INTEGER NOT NULL DEFAULT 240,
            resolution_minutes INTEGER NOT NULL DEFAULT 1440,
            is_active BOOLEAN NOT NULL DEFAULT {bool_true},
            created_at TIMESTAMP NOT NULL DEFAULT {now_expr},
            updated_at TIMESTAMP NOT NULL DEFAULT {now_expr}
        )
        """
    )
    execute("CREATE INDEX IF NOT EXISTS ix_it_sla_policies_priority ON it_sla_policies(priority)")

    execute(
        f"""
        CREATE TABLE IF NOT EXISTS it_tickets (
            id INTEGER PRIMARY KEY,
            ticket_number VARCHAR(20) NOT NULL UNIQUE,
            title VARCHAR(180) NOT NULL,
            description {text_type} NOT NULL,
            requester_user_id INTEGER NOT NULL REFERENCES users(id),
            assigned_to_user_id INTEGER REFERENCES users(id),
            status VARCHAR(30) NOT NULL DEFAULT 'ABERTO',
            priority VARCHAR(20) NOT NULL DEFAULT 'MEDIA',
            category VARCHAR(40) NOT NULL DEFAULT 'OUTRO',
            suspension_reason VARCHAR(40),
            sla_policy_id INTEGER REFERENCES it_sla_policies(id),
            due_at TIMESTAMP,
            first_response_at TIMESTAMP,
            resolved_at TIMESTAMP,
            closed_at TIMESTAMP,
            kanban_card_id INTEGER REFERENCES kanban_cards(id),
            created_at TIMESTAMP NOT NULL DEFAULT {now_expr},
            updated_at TIMESTAMP NOT NULL DEFAULT {now_expr}
        )
        """
    )
    for column in ["requester_user_id", "assigned_to_user_id", "status", "priority", "category", "created_at", "due_at", "kanban_card_id"]:
        execute(f"CREATE INDEX IF NOT EXISTS ix_it_tickets_{column} ON it_tickets({column})")

    execute(
        f"""
        CREATE TABLE IF NOT EXISTS it_ticket_comments (
            id INTEGER PRIMARY KEY,
            ticket_id INTEGER NOT NULL REFERENCES it_tickets(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            comment {text_type} NOT NULL,
            is_internal BOOLEAN NOT NULL DEFAULT {bool_false},
            created_at TIMESTAMP NOT NULL DEFAULT {now_expr},
            updated_at TIMESTAMP NOT NULL DEFAULT {now_expr},
            deleted_at TIMESTAMP
        )
        """
    )
    execute("CREATE INDEX IF NOT EXISTS ix_it_ticket_comments_ticket_id ON it_ticket_comments(ticket_id)")

    execute(
        f"""
        CREATE TABLE IF NOT EXISTS it_ticket_checklists (
            id INTEGER PRIMARY KEY,
            ticket_id INTEGER NOT NULL REFERENCES it_tickets(id) ON DELETE CASCADE,
            title VARCHAR NOT NULL,
            category VARCHAR(40),
            position INTEGER NOT NULL DEFAULT 0,
            created_by_user_id INTEGER NOT NULL REFERENCES users(id),
            created_at TIMESTAMP NOT NULL DEFAULT {now_expr},
            updated_at TIMESTAMP NOT NULL DEFAULT {now_expr}
        )
        """
    )
    execute("CREATE INDEX IF NOT EXISTS ix_it_ticket_checklists_ticket_id ON it_ticket_checklists(ticket_id)")

    if dialect == "postgresql":
        execute("ALTER TABLE IF EXISTS it_ticket_checklist_items RENAME COLUMN ticket_id TO checklist_id")
    execute(
        f"""
        CREATE TABLE IF NOT EXISTS it_ticket_checklist_items (
            id INTEGER PRIMARY KEY,
            checklist_id INTEGER NOT NULL REFERENCES it_ticket_checklists(id) ON DELETE CASCADE,
            text VARCHAR NOT NULL,
            is_done BOOLEAN NOT NULL DEFAULT {bool_false},
            position INTEGER NOT NULL DEFAULT 0,
            created_by_user_id INTEGER NOT NULL REFERENCES users(id),
            completed_by_user_id INTEGER REFERENCES users(id),
            completed_at TIMESTAMP,
            created_at TIMESTAMP NOT NULL DEFAULT {now_expr},
            updated_at TIMESTAMP NOT NULL DEFAULT {now_expr}
        )
        """
    )
    execute("CREATE INDEX IF NOT EXISTS ix_it_ticket_checklist_items_checklist_id ON it_ticket_checklist_items(checklist_id)")

    execute(
        f"""
        CREATE TABLE IF NOT EXISTS it_checklist_templates (
            id INTEGER PRIMARY KEY,
            category VARCHAR(40) NOT NULL,
            title VARCHAR NOT NULL,
            items {json_type} NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT {bool_true},
            created_at TIMESTAMP NOT NULL DEFAULT {now_expr},
            updated_at TIMESTAMP NOT NULL DEFAULT {now_expr},
            CONSTRAINT uq_it_checklist_template_category_title UNIQUE(category, title)
        )
        """
    )

    execute(
        f"""
        CREATE TABLE IF NOT EXISTS it_ticket_time_logs (
            id INTEGER PRIMARY KEY,
            ticket_id INTEGER NOT NULL REFERENCES it_tickets(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            started_at TIMESTAMP NOT NULL DEFAULT {now_expr},
            ended_at TIMESTAMP,
            duration_seconds INTEGER,
            note {text_type},
            created_at TIMESTAMP NOT NULL DEFAULT {now_expr}
        )
        """
    )

    execute(
        f"""
        CREATE TABLE IF NOT EXISTS it_ticket_attachments (
            id INTEGER PRIMARY KEY,
            ticket_id INTEGER NOT NULL REFERENCES it_tickets(id) ON DELETE CASCADE,
            comment_id INTEGER REFERENCES it_ticket_comments(id),
            file_id INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
            uploaded_by_user_id INTEGER NOT NULL REFERENCES users(id),
            created_at TIMESTAMP NOT NULL DEFAULT {now_expr},
            deleted_at TIMESTAMP
        )
        """
    )

    execute(
        f"""
        CREATE TABLE IF NOT EXISTS it_assets (
            id INTEGER PRIMARY KEY,
            asset_tag VARCHAR UNIQUE,
            name VARCHAR NOT NULL,
            asset_type VARCHAR(30) NOT NULL DEFAULT 'OUTRO',
            status VARCHAR(30) NOT NULL DEFAULT 'DISPONIVEL',
            assigned_to_user_id INTEGER REFERENCES users(id),
            location VARCHAR,
            serial_number VARCHAR UNIQUE,
            manufacturer VARCHAR,
            model VARCHAR,
            purchase_date TIMESTAMP,
            warranty_until TIMESTAMP,
            notes {text_type},
            created_at TIMESTAMP NOT NULL DEFAULT {now_expr},
            updated_at TIMESTAMP NOT NULL DEFAULT {now_expr}
        )
        """
    )

    execute(
        f"""
        CREATE TABLE IF NOT EXISTS it_access_catalog (
            id INTEGER PRIMARY KEY,
            system_name VARCHAR NOT NULL,
            access_type VARCHAR,
            url VARCHAR,
            owner_user_id INTEGER REFERENCES users(id),
            responsible_team VARCHAR,
            description {text_type},
            how_to_request {text_type},
            is_active BOOLEAN NOT NULL DEFAULT {bool_true},
            created_at TIMESTAMP NOT NULL DEFAULT {now_expr},
            updated_at TIMESTAMP NOT NULL DEFAULT {now_expr}
        )
        """
    )

    execute(
        f"""
        CREATE TABLE IF NOT EXISTS it_access_requests (
            id INTEGER PRIMARY KEY,
            requester_user_id INTEGER NOT NULL REFERENCES users(id),
            target_user_id INTEGER NOT NULL REFERENCES users(id),
            system_name VARCHAR NOT NULL,
            access_type VARCHAR NOT NULL,
            reason {text_type} NOT NULL,
            status VARCHAR(30) NOT NULL DEFAULT 'ABERTA',
            ticket_id INTEGER REFERENCES it_tickets(id),
            created_at TIMESTAMP NOT NULL DEFAULT {now_expr},
            updated_at TIMESTAMP NOT NULL DEFAULT {now_expr}
        )
        """
    )

    execute(
        f"""
        CREATE TABLE IF NOT EXISTS it_credentials_vault (
            id INTEGER PRIMARY KEY,
            title VARCHAR NOT NULL,
            system_name VARCHAR NOT NULL,
            username VARCHAR,
            secret_encrypted {text_type} NOT NULL,
            secret_hint VARCHAR,
            url VARCHAR,
            notes {text_type},
            owner_user_id INTEGER REFERENCES users(id),
            visibility_level VARCHAR(30) NOT NULL DEFAULT 'IT_MANAGER',
            is_active BOOLEAN NOT NULL DEFAULT {bool_true},
            created_by_user_id INTEGER NOT NULL REFERENCES users(id),
            updated_by_user_id INTEGER REFERENCES users(id),
            created_at TIMESTAMP NOT NULL DEFAULT {now_expr},
            updated_at TIMESTAMP NOT NULL DEFAULT {now_expr},
            last_revealed_at TIMESTAMP,
            last_revealed_by_user_id INTEGER REFERENCES users(id)
        )
        """
    )

    if dialect == "postgresql" and inspector.has_table("it_certificates"):
        execute("ALTER TABLE IF EXISTS it_certificates ADD COLUMN IF NOT EXISTS domain_or_system VARCHAR")
        execute("ALTER TABLE IF EXISTS it_certificates ADD COLUMN IF NOT EXISTS provider VARCHAR")
        execute("ALTER TABLE IF EXISTS it_certificates ADD COLUMN IF NOT EXISTS responsible_user_id INTEGER REFERENCES users(id)")
        execute("ALTER TABLE IF EXISTS it_certificates ADD COLUMN IF NOT EXISTS status VARCHAR(30) DEFAULT 'VALIDO' NOT NULL")
        execute("ALTER TABLE IF EXISTS it_certificates ADD COLUMN IF NOT EXISTS notes TEXT")
        execute("ALTER TABLE IF EXISTS it_certificates ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL")
        execute("UPDATE it_certificates SET domain_or_system = name WHERE domain_or_system IS NULL")
        execute("ALTER TABLE IF EXISTS it_certificates ALTER COLUMN domain_or_system SET NOT NULL")
    execute(
        f"""
        CREATE TABLE IF NOT EXISTS it_certificates (
            id INTEGER PRIMARY KEY,
            name VARCHAR NOT NULL,
            domain_or_system VARCHAR NOT NULL,
            issuer VARCHAR,
            provider VARCHAR,
            expires_at TIMESTAMP NOT NULL,
            responsible_user_id INTEGER REFERENCES users(id),
            status VARCHAR(30) NOT NULL DEFAULT 'VALIDO',
            notes {text_type},
            created_at TIMESTAMP NOT NULL DEFAULT {now_expr},
            updated_at TIMESTAMP NOT NULL DEFAULT {now_expr}
        )
        """
    )

    execute(
        f"""
        CREATE TABLE IF NOT EXISTS it_network_items (
            id INTEGER PRIMARY KEY,
            name VARCHAR NOT NULL,
            item_type VARCHAR(30) NOT NULL DEFAULT 'OUTRO',
            ip_address VARCHAR,
            location VARCHAR,
            status VARCHAR(30) NOT NULL DEFAULT 'ATIVO',
            notes {text_type},
            created_at TIMESTAMP NOT NULL DEFAULT {now_expr},
            updated_at TIMESTAMP NOT NULL DEFAULT {now_expr}
        )
        """
    )

    execute(
        f"""
        CREATE TABLE IF NOT EXISTS it_maintenance_records (
            id INTEGER PRIMARY KEY,
            asset_id INTEGER REFERENCES it_assets(id),
            network_item_id INTEGER REFERENCES it_network_items(id),
            ticket_id INTEGER REFERENCES it_tickets(id),
            title VARCHAR NOT NULL,
            description {text_type},
            scheduled_at TIMESTAMP,
            completed_at TIMESTAMP,
            performed_by_user_id INTEGER REFERENCES users(id),
            status VARCHAR(30) NOT NULL DEFAULT 'AGENDADA',
            created_at TIMESTAMP NOT NULL DEFAULT {now_expr},
            updated_at TIMESTAMP NOT NULL DEFAULT {now_expr}
        )
        """
    )

    execute(
        f"""
        CREATE TABLE IF NOT EXISTS it_ticket_kanban_links (
            id INTEGER PRIMARY KEY,
            ticket_id INTEGER NOT NULL REFERENCES it_tickets(id) ON DELETE CASCADE,
            kanban_card_id INTEGER NOT NULL REFERENCES kanban_cards(id) ON DELETE CASCADE,
            created_by_user_id INTEGER NOT NULL REFERENCES users(id),
            created_at TIMESTAMP NOT NULL DEFAULT {now_expr},
            CONSTRAINT uq_it_ticket_kanban_link UNIQUE(ticket_id, kanban_card_id)
        )
        """
    )

    execute(
        f"""
        CREATE TABLE IF NOT EXISTS it_activity (
            id INTEGER PRIMARY KEY,
            ticket_id INTEGER REFERENCES it_tickets(id) ON DELETE CASCADE,
            asset_id INTEGER REFERENCES it_assets(id),
            credential_id INTEGER REFERENCES it_credentials_vault(id),
            certificate_id INTEGER REFERENCES it_certificates(id),
            network_item_id INTEGER REFERENCES it_network_items(id),
            actor_user_id INTEGER REFERENCES users(id),
            action VARCHAR NOT NULL,
            metadata {json_type},
            created_at TIMESTAMP NOT NULL DEFAULT {now_expr}
        )
        """
    )
    execute("CREATE INDEX IF NOT EXISTS ix_it_activity_ticket_id ON it_activity(ticket_id)")
    execute("CREATE INDEX IF NOT EXISTS ix_it_activity_action ON it_activity(action)")


def downgrade() -> None:
    for table in [
        "it_activity",
        "it_ticket_kanban_links",
        "it_maintenance_records",
        "it_network_items",
        "it_credentials_vault",
        "it_access_requests",
        "it_access_catalog",
        "it_assets",
        "it_ticket_attachments",
        "it_ticket_time_logs",
        "it_checklist_templates",
        "it_ticket_checklist_items",
        "it_ticket_checklists",
    ]:
        op.execute(sa.text(f"DROP TABLE IF EXISTS {table}"))
