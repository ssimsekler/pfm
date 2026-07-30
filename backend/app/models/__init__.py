"""Models package — re-exports every ORM class so `import app.models as m`
resolves `m.<Model>` (used by export/import and other services).

Grouped by module. Keep this in sync when adding new models.
"""

from app.models.base import Base, BaseEntity, TimestampMixin
from app.models.meta import (
    AppConfig,
    AuditLog,
    CodeList,
    CodeValue,
    EventOutbox,
    IdSequence,
)
from app.models.security import AppUser, Household, Role, UserRole
from app.models.reference import Country, Currency, Institution
from app.models.financial import (
    Account,
    Attachment,
    Beneficiary,
    CashFlowItem,
    CurrencyRate,
    EntityTag,
    ExpenseCategory,
    Partner,
    Tag,
    Transaction,
    TransactionSplit,
    TransferGroup,
)
from app.models.scheduling import (
    AmortizationSchedule,
    Goal,
    HolidayCalendar,
    HolidayCalendarDay,
    InstallmentPlan,
    InstallmentSchedule,
    Loan,
    RecurrenceProfile,
)
from app.models.automation import (
    CategorizationRule,
    FeatureLlmBinding,
    IntegrationEndpoint,
    InvestmentHolding,
    LlmProvider,
    ValuationHistory,
)
from app.models.budgeting import Budget, BudgetLine
from app.models.imports import DocumentImport, DocumentImportRow
from app.models.notifications import Notification

__all__ = [
    "Base",
    "BaseEntity",
    "TimestampMixin",
    # meta
    "AppConfig",
    "IdSequence",
    "CodeList",
    "CodeValue",
    "EventOutbox",
    "AuditLog",
    # security
    "Household",
    "AppUser",
    "Role",
    "UserRole",
    # reference
    "Currency",
    "Country",
    "Institution",
    # financial
    "Account",
    "Partner",
    "Beneficiary",
    "ExpenseCategory",
    "CashFlowItem",
    "TransferGroup",
    "Transaction",
    "TransactionSplit",
    "Tag",
    "EntityTag",
    "Attachment",
    "CurrencyRate",
    # scheduling
    "RecurrenceProfile",
    "HolidayCalendar",
    "HolidayCalendarDay",
    "InstallmentPlan",
    "InstallmentSchedule",
    "Loan",
    "AmortizationSchedule",
    "Goal",
    # automation
    "LlmProvider",
    "FeatureLlmBinding",
    "IntegrationEndpoint",
    "CategorizationRule",
    "InvestmentHolding",
    "ValuationHistory",
    # budgeting
    "Budget",
    "BudgetLine",
    # imports
    "DocumentImport",
    "DocumentImportRow",
    # notifications
    "Notification",
]