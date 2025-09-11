"""
Event Validation System for Xline Trading System
File: xline/core/events/validation.py

Provides comprehensive validation for events using Pydantic models.
Includes business rule validation and error handling.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator
from pydantic_core import PydanticCustomError

from .types import (
    Event,
    EventType,
    OrderEvent,
    TradeEvent,
    RiskEvent,
    AccountEvent,
    SystemEvent,
    OrderSide,
    OrderType,
    OrderStatus,
    RiskSeverity,
)

logger = logging.getLogger(__name__)


class EventValidationError(Exception):
    """Exception raised for event validation failures"""
    
    def __init__(self, message: str, errors: list[dict[str, Any]] | None = None):
        super().__init__(message)
        self.errors = errors or []


class ValidationSeverity(str, Enum):
    """Validation error severity levels"""
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationResult:
    """Result of event validation"""
    
    is_valid: bool
    errors: list[dict[str, Any]]
    warnings: list[dict[str, Any]]
    
    @property
    def has_errors(self) -> bool:
        """Check if validation has errors"""
        return len(self.errors) > 0
    
    @property
    def has_warnings(self) -> bool:
        """Check if validation has warnings"""
        return len(self.warnings) > 0


# Pydantic models for event validation

class BaseEventModel(BaseModel):
    """Base Pydantic model for event validation"""
    
    id: str = Field(..., min_length=1, description="Event ID")
    type: EventType = Field(..., description="Event type")
    source: str = Field(..., min_length=1, description="Event source")
    timestamp: str = Field(..., description="Event timestamp")
    data: dict[str, Any] = Field(default_factory=dict, description="Additional data")
    correlation_id: str | None = Field(None, description="Correlation ID")
    version: str = Field(default="1.0", pattern=r"^\d+\.\d+(\.\d+)?$", description="Event version")
    
    @field_validator('id')
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Validate event ID"""
        if not v or not v.strip():
            raise PydanticCustomError(
                'empty_id',
                'Event ID cannot be empty',
                {}
            )
        return v.strip()
    
    @field_validator('source')
    @classmethod
    def validate_source(cls, v: str) -> str:
        """Validate event source"""
        if not v or not v.strip():
            raise PydanticCustomError(
                'empty_source',
                'Event source cannot be empty',
                {}
            )
        return v.strip()


class OrderEventModel(BaseEventModel):
    """Pydantic model for OrderEvent validation"""
    
    order_id: str = Field(..., min_length=1, description="Order ID")
    account_id: str = Field(..., min_length=1, description="Account ID")
    symbol: str = Field(..., min_length=1, description="Trading symbol")
    side: OrderSide = Field(..., description="Order side")
    quantity: Decimal = Field(..., gt=0, description="Order quantity")
    price: Decimal = Field(..., ge=0, description="Order price")
    order_type: OrderType = Field(..., description="Order type")
    status: OrderStatus = Field(..., description="Order status")
    
    # Optional fields
    stop_price: Decimal | None = Field(None, ge=0, description="Stop price")
    time_in_force: str = Field(default="GTC", description="Time in force")
    client_order_id: str | None = Field(None, description="Client order ID")
    exchange: str | None = Field(None, description="Exchange")
    filled_quantity: Decimal = Field(default=Decimal('0'), ge=0, description="Filled quantity")
    remaining_quantity: Decimal | None = Field(None, ge=0, description="Remaining quantity")
    average_fill_price: Decimal | None = Field(None, ge=0, description="Average fill price")
    
    @field_validator('symbol')
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        """Validate trading symbol"""
        if not v or not v.strip():
            raise PydanticCustomError(
                'empty_symbol',
                'Symbol cannot be empty',
                {}
            )
        
        # Basic symbol format validation
        symbol = v.strip().upper()
        if len(symbol) < 2:
            raise PydanticCustomError(
                'invalid_symbol',
                'Symbol must be at least 2 characters',
                {}
            )
        
        return symbol
    
    @field_validator('quantity')
    @classmethod
    def validate_quantity(cls, v: Decimal) -> Decimal:
        """Validate order quantity"""
        if v <= 0:
            raise PydanticCustomError(
                'invalid_quantity',
                'Quantity must be positive',
                {}
            )
        
        # Check decimal places (max 8 for most exchanges)
        if v.as_tuple().exponent < -8:
            raise PydanticCustomError(
                'too_many_decimals',
                'Quantity has too many decimal places (max 8)',
                {}
            )
        
        return v
    
    @field_validator('filled_quantity')
    @classmethod
    def validate_filled_quantity(cls, v: Decimal) -> Decimal:
        """Validate filled quantity"""
        if v < 0:
            raise PydanticCustomError(
                'negative_filled',
                'Filled quantity cannot be negative',
                {}
            )
        return v


class TradeEventModel(BaseEventModel):
    """Pydantic model for TradeEvent validation"""
    
    trade_id: str = Field(..., min_length=1, description="Trade ID")
    order_id: str = Field(..., min_length=1, description="Order ID")
    account_id: str = Field(..., min_length=1, description="Account ID")
    symbol: str = Field(..., min_length=1, description="Trading symbol")
    side: OrderSide = Field(..., description="Trade side")
    quantity: Decimal = Field(..., gt=0, description="Trade quantity")
    price: Decimal = Field(..., gt=0, description="Trade price")
    fee: Decimal = Field(..., ge=0, description="Trade fee")
    commission: Decimal = Field(..., ge=0, description="Commission")
    
    # Optional fields
    exchange: str | None = Field(None, description="Exchange")
    trade_time: str | None = Field(None, description="Trade time")
    settlement_date: str | None = Field(None, description="Settlement date")
    counterparty: str | None = Field(None, description="Counterparty")
    
    @field_validator('price')
    @classmethod
    def validate_price(cls, v: Decimal) -> Decimal:
        """Validate trade price"""
        if v <= 0:
            raise PydanticCustomError(
                'invalid_price',
                'Trade price must be positive',
                {}
            )
        return v


class RiskEventModel(BaseEventModel):
    """Pydantic model for RiskEvent validation"""
    
    account_id: str = Field(..., min_length=1, description="Account ID")
    rule_type: str = Field(..., min_length=1, description="Risk rule type")
    severity: RiskSeverity = Field(..., description="Risk severity")
    threshold: Decimal = Field(..., ge=0, description="Risk threshold")
    current_value: Decimal = Field(..., description="Current value")
    message: str = Field(..., min_length=1, description="Risk message")
    
    # Optional fields
    rule_id: str | None = Field(None, description="Rule ID")
    position_id: str | None = Field(None, description="Position ID")
    symbol: str | None = Field(None, description="Symbol")
    action_required: bool = Field(default=False, description="Action required")
    auto_action_taken: str | None = Field(None, description="Auto action taken")
    
    @field_validator('message')
    @classmethod
    def validate_message(cls, v: str) -> str:
        """Validate risk message"""
        if not v or not v.strip():
            raise PydanticCustomError(
                'empty_message',
                'Risk message cannot be empty',
                {}
            )
        return v.strip()


class AccountEventModel(BaseEventModel):
    """Pydantic model for AccountEvent validation"""
    
    account_id: str = Field(..., min_length=1, description="Account ID")
    account_type: str = Field(..., min_length=1, description="Account type")
    status: str = Field(..., min_length=1, description="Account status")
    
    # Optional fields
    balance: Decimal | None = Field(None, ge=0, description="Account balance")
    currency: str | None = Field(None, min_length=3, max_length=3, description="Currency")
    margin_available: Decimal | None = Field(None, ge=0, description="Margin available")
    previous_status: str | None = Field(None, description="Previous status")
    reason: str | None = Field(None, description="Status change reason")
    
    @field_validator('currency')
    @classmethod
    def validate_currency(cls, v: str | None) -> str | None:
        """Validate currency code"""
        if v is not None:
            v = v.strip().upper()
            if len(v) != 3:
                raise PydanticCustomError(
                    'invalid_currency',
                    'Currency must be 3 characters (ISO 4217)',
                    {}
                )
        return v


class SystemEventModel(BaseEventModel):
    """Pydantic model for SystemEvent validation"""
    
    component: str = Field(..., min_length=1, description="System component")
    status: str = Field(..., min_length=1, description="Component status")
    message: str = Field(..., min_length=1, description="System message")
    
    # Optional fields
    error_code: str | None = Field(None, description="Error code")
    stack_trace: str | None = Field(None, description="Stack trace")
    severity: RiskSeverity = Field(default=RiskSeverity.LOW, description="Severity")
    recovery_action: str | None = Field(None, description="Recovery action")


# Validation model registry
VALIDATION_MODEL_REGISTRY: dict[type[Event], type[BaseEventModel]] = {
    OrderEvent: OrderEventModel,
    TradeEvent: TradeEventModel,
    RiskEvent: RiskEventModel,
    AccountEvent: AccountEventModel,
    SystemEvent: SystemEventModel,
}


class EventValidator:
    """
    Comprehensive event validator with business rules.
    
    Provides both structural validation (using Pydantic) and
    business rule validation for events.
    """
    
    def __init__(self) -> None:
        """Initialize event validator"""
        self._business_rules: dict[type[Event], list[Callable[[Event], ValidationResult]]] = {}
        self._register_default_business_rules()
    
    def _register_default_business_rules(self) -> None:
        """Register default business validation rules"""
        # Order event business rules
        self.register_business_rule(OrderEvent, self._validate_order_quantity_consistency)
        self.register_business_rule(OrderEvent, self._validate_order_price_reasonableness)
        
        # Trade event business rules
        self.register_business_rule(TradeEvent, self._validate_trade_amounts)
        
        # Risk event business rules
        self.register_business_rule(RiskEvent, self._validate_risk_thresholds)
    
    def register_business_rule(
        self,
        event_type: type[Event],
        rule_func: Callable[[Event], ValidationResult]
    ) -> None:
        """Register a business validation rule for an event type"""
        if event_type not in self._business_rules:
            self._business_rules[event_type] = []
        
        self._business_rules[event_type].append(rule_func)
        logger.info(f"Registered business rule for {event_type.__name__}")
    
    def validate_event(self, event: Event) -> ValidationResult:
        """
        Validate an event with both structural and business rules.
        
        Args:
            event: Event to validate
            
        Returns:
            ValidationResult with validation details
        """
        errors = []
        warnings = []
        
        try:
            # Structural validation using Pydantic
            structural_result = self._validate_structure(event)
            errors.extend(structural_result.errors)
            warnings.extend(structural_result.warnings)
            
            # Business rule validation
            business_result = self._validate_business_rules(event)
            errors.extend(business_result.errors)
            warnings.extend(business_result.warnings)
            
        except Exception as e:
            logger.error(f"Validation error: {e}")
            errors.append({
                'type': 'validation_exception',
                'message': str(e),
                'severity': ValidationSeverity.CRITICAL.value
            })
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def _validate_structure(self, event: Event) -> ValidationResult:
        """Validate event structure using Pydantic models"""
        errors = []
        warnings = []
        
        # Get appropriate validation model
        event_type = type(event)
        validation_model = VALIDATION_MODEL_REGISTRY.get(event_type)
        
        if validation_model is None:
            errors.append({
                'type': 'unknown_event_type',
                'message': f'No validation model for event type: {event_type}',
                'severity': ValidationSeverity.ERROR.value
            })
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)
        
        try:
            # Convert event to dict and validate
            event_data = event.to_dict()
            validation_model(**event_data)
            
        except ValidationError as e:
            for error in e.errors():
                errors.append({
                    'type': 'structural_validation',
                    'field': '.'.join(str(loc) for loc in error['loc']),
                    'message': error['msg'],
                    'input': error.get('input'),
                    'severity': ValidationSeverity.ERROR.value
                })
        
        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)
    
    def _validate_business_rules(self, event: Event) -> ValidationResult:
        """Validate event using business rules"""
        errors = []
        warnings = []
        
        event_type = type(event)
        rules = self._business_rules.get(event_type, [])
        
        for rule in rules:
            try:
                result = rule(event)
                errors.extend(result.errors)
                warnings.extend(result.warnings)
            except Exception as e:
                logger.error(f"Business rule error: {e}")
                errors.append({
                    'type': 'business_rule_exception',
                    'message': f'Business rule failed: {e}',
                    'severity': ValidationSeverity.ERROR.value
                })
        
        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)
    
    # Default business rule implementations
    
    def _validate_order_quantity_consistency(self, event: OrderEvent) -> ValidationResult:
        """Validate order quantity consistency"""
        errors = []
        warnings = []
        
        # Check if filled quantity doesn't exceed total quantity
        if event.filled_quantity > event.quantity:
            errors.append({
                'type': 'quantity_inconsistency',
                'message': f'Filled quantity ({event.filled_quantity}) exceeds total quantity ({event.quantity})',
                'severity': ValidationSeverity.ERROR.value
            })
        
        # Check remaining quantity consistency
        if event.remaining_quantity is not None:
            expected_remaining = event.quantity - event.filled_quantity
            if abs(event.remaining_quantity - expected_remaining) > Decimal('0.00000001'):
                errors.append({
                    'type': 'remaining_quantity_mismatch',
                    'message': f'Remaining quantity mismatch: expected {expected_remaining}, got {event.remaining_quantity}',
                    'severity': ValidationSeverity.ERROR.value
                })
        
        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)
    
    def _validate_order_price_reasonableness(self, event: OrderEvent) -> ValidationResult:
        """Validate order price reasonableness"""
        errors = []
        warnings = []
        
        # Check for obviously unreasonable prices
        if event.price > Decimal('1000000'):  # $1M per unit
            warnings.append({
                'type': 'high_price',
                'message': f'Order price is very high: {event.price}',
                'severity': ValidationSeverity.WARNING.value
            })
        
        if event.price < Decimal('0.0001') and event.order_type in [OrderType.LIMIT, OrderType.STOP_LIMIT]:
            warnings.append({
                'type': 'low_price',
                'message': f'Order price is very low: {event.price}',
                'severity': ValidationSeverity.WARNING.value
            })
        
        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)
    
    def _validate_trade_amounts(self, event: TradeEvent) -> ValidationResult:
        """Validate trade amount calculations"""
        errors = []
        warnings = []
        
        # Check if fees are reasonable (< 10% of trade value)
        trade_value = event.quantity * event.price
        total_fees = event.fee + event.commission
        
        if total_fees > trade_value * Decimal('0.1'):
            warnings.append({
                'type': 'high_fees',
                'message': f'Total fees ({total_fees}) exceed 10% of trade value ({trade_value})',
                'severity': ValidationSeverity.WARNING.value
            })
        
        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)
    
    def _validate_risk_thresholds(self, event: RiskEvent) -> ValidationResult:
        """Validate risk threshold breaches"""
        errors = []
        warnings = []
        
        # Check if current value actually breaches threshold for certain rule types
        if event.rule_type in ['position_limit', 'loss_limit', 'exposure_limit']:
            if event.current_value <= event.threshold:
                warnings.append({
                    'type': 'threshold_not_breached',
                    'message': f'Current value ({event.current_value}) does not breach threshold ({event.threshold})',
                    'severity': ValidationSeverity.WARNING.value
                })
        
        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)


# Global validator instance
event_validator = EventValidator()


def validate_event(event: Event) -> ValidationResult:
    """
    Convenience function to validate an event.
    
    Args:
        event: Event to validate
        
    Returns:
        ValidationResult with validation details
    """
    return event_validator.validate_event(event)


def validate_event_data(event_data: dict[str, Any]) -> ValidationResult:
    """
    Validate event data dictionary.
    
    Args:
        event_data: Event data to validate
        
    Returns:
        ValidationResult with validation details
    """
    try:
        from .types import create_event_from_dict
        event = create_event_from_dict(event_data)
        return validate_event(event)
    except Exception as e:
        return ValidationResult(
            is_valid=False,
            errors=[{
                'type': 'event_creation_error',
                'message': f'Failed to create event from data: {e}',
                'severity': ValidationSeverity.ERROR.value
            }],
            warnings=[]
        )
