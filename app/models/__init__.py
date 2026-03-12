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
from app.models.reconciliation import ReconciliationMatch  # noqa: F401
from app.models.resort_submission import ResortSubmission  # noqa: F401
from app.models.communication_log import CommunicationLog  # noqa: F401
from app.models.channex_property import ChannexProperty  # noqa: F401
from app.models.channex_message import ChannexMessage  # noqa: F401
from app.models.channex_review import ChannexReview  # noqa: F401
from app.models.channex_webhook_event import ChannexWebhookEvent  # noqa: F401
from app.models.message_template import MessageTemplate  # noqa: F401
from app.models.triggered_message_log import TriggeredMessageLog  # noqa: F401
from app.models.guidebook import Guidebook  # noqa: F401
from app.models.cleaning_task import CleaningTask  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.owner_access import OwnerAccess  # noqa: F401

# Feature parity models (migration 013)
from app.models.booking_group import BookingGroup  # noqa: F401
from app.models.room_type import RoomType  # noqa: F401
from app.models.room import Room  # noqa: F401
from app.models.guest import Guest  # noqa: F401
from app.models.extra import Extra, BookingExtra  # noqa: F401
from app.models.invoice import Invoice, InvoiceItem  # noqa: F401
from app.models.payment import Payment  # noqa: F401
from app.models.rate_plan import RatePlan, RateDate  # noqa: F401
from app.models.tax_type import TaxType  # noqa: F401
from app.models.custom_field import CustomFieldDefinition, CustomFieldValue  # noqa: F401
from app.models.night_audit import NightAuditLog  # noqa: F401
from app.models.booking_audit import BookingAuditLog  # noqa: F401

# Dynamic pricing + analytics models
from app.models.market_event import MarketEvent  # noqa: F401
from app.models.pricing_rule import PricingRule  # noqa: F401
from app.models.price_recommendation import PriceRecommendation  # noqa: F401
from app.models.comp_set import CompSet, CompSetProperty  # noqa: F401
from app.models.market_snapshot import MarketSnapshot  # noqa: F401
from app.models.portfolio_metric import PortfolioMetric  # noqa: F401
from app.models.listing_analysis import ListingAnalysis  # noqa: F401
