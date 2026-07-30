"""SQLAlchemy ORM models.

Import order matters for Alembic autogenerate & relationship resolution.
"""

from app.models.base import Base, TimestampMixin, BaseEntity  # noqa: F401
from app.models.meta import (  # noqa: F401
    AppConfig,
    IdSequence,
    CodeList,
    CodeValue,
    EventOutbox,
    AuditLog,
)
from app.models.security import Household, AppUser, Role, UserRole  # noqa: F401
from app.models.reference import Currency, Country, Institution  # noqa: F401
from app.models.financial import (  # noqa: F401
    Account,
    Partner,
    Beneficiary,
    ExpenseCategory,
    CashFlowItem,
    TransferGroup,
    Transaction,
    TransactionSplit,
    Tag,
    EntityTag,
    Attachment,
    CurrencyRate,
)
from app.models.scheduling import (  # noqa: F401
    HolidayCalendar,
    HolidayCalendarDay,
    RecurrenceProfile,
    InstallmentPlan,
    InstallmentSchedule,
    Loan,
    AmortizationSchedule,
    Goal,
)
from app.models.automation import (  # noqa: F401
    LlmProvider,
    FeatureLlmBinding,
    IntegrationEndpoint,
    CategorizationRule,
    InvestmentHolding,
    ValuationHistory,
)
