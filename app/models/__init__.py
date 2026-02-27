# Import all models here so Alembic can detect them via Base.metadata
from app.models.property import Property  # noqa: F401
from app.models.booking import Booking  # noqa: F401
from app.models.bank_transaction import BankTransaction  # noqa: F401
from app.models.import_run import ImportRun  # noqa: F401
from app.models.account import Account  # noqa: F401
from app.models.journal_entry import JournalEntry  # noqa: F401
from app.models.journal_line import JournalLine  # noqa: F401
from app.models.expense import Expense  # noqa: F401
from app.models.loan import Loan  # noqa: F401
