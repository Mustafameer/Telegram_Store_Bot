from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class User:
    user_id: Optional[int]
    telegram_id: int
    user_name: Optional[str]
    user_type: Optional[str]
    phone_number: Optional[str]
    full_name: Optional[str]

    @classmethod
    def from_tuple(cls, data):
        if not data: return None
        # Adjust indices based on your distinct table schema
        # Assuming: UserID, TelegramID, UserName, UserType, PhoneNumber, FullName
        return cls(
            user_id=data[0],
            telegram_id=data[1],
            user_name=data[2],
            user_type=data[3],
            phone_number=data[4],
            full_name=data[5] if len(data) > 5 else None
        )

@dataclass
class Seller:
    seller_id: int
    telegram_id: int
    user_name: Optional[str]
    store_name: Optional[str]
    status: Optional[str]
    image_path: Optional[str]

    @classmethod
    def from_tuple(cls, data):
        if not data: return None
        return cls(
            seller_id=data[0],
            telegram_id=data[1],
            user_name=data[2],
            store_name=data[3],
            status=data[4] if len(data) > 4 else None,
            image_path=data[9] if len(data) > 9 else None # ImagePath is 10th column in init_db (index 9)
        )

@dataclass
class Category:
    category_id: int
    seller_id: int
    name: str
    order_index: int = 0
    image_path: Optional[str] = None

    @classmethod
    def from_tuple(cls, data):
        if not data: return None
        return cls(
            category_id=data[0],
            seller_id=data[1],
            name=data[2],
            order_index=data[3] if len(data) > 3 else 0,
            image_path=data[4] if len(data) > 4 else None
        )

@dataclass
class Product:
    product_id: int
    seller_id: int
    category_id: Optional[int]
    name: str
    description: Optional[str]
    price: float
    wholesale_price: Optional[float]
    quantity: int
    image_path: Optional[str]
    status: str = 'active'

    @classmethod
    def from_tuple(cls, data):
        if not data: return None
        return cls(
            product_id=data[0],
            name=data[1], # Note: Check actual SQL order in bot.py
            description=data[2] if len(data) > 2 else None,
            price=data[3] if len(data) > 3 else 0.0,
            wholesale_price=data[4] if len(data) > 4 else None,
            quantity=data[5] if len(data) > 5 else 0,
            image_path=data[6] if len(data) > 6 else None,
            # Adjust these indices heavily based on your actual SELECT * queries
            # This is a placeholder; we need to verify the exact column order from bot.py queries
            seller_id=0, # Placeholder
            category_id=0 # Placeholder
        )

@dataclass
class Order:
    order_id: int
    buyer_id: Optional[int]
    seller_id: int
    total: float
    status: str
    created_at: str
    delivery_address: Optional[str]
    notes: Optional[str]
    payment_method: str = 'cash'
    fully_paid: bool = False

    @classmethod
    def from_tuple(cls, data):
        if not data: return None
        return cls(
            order_id=data[0],
            buyer_id=data[1],
            seller_id=data[2],
            total=data[3],
            status=data[4],
            created_at=data[5],
            delivery_address=data[6] if len(data) > 6 else None,
            notes=data[7] if len(data) > 7 else None,
            payment_method=data[8] if len(data) > 8 else 'cash',
            fully_paid=bool(data[9]) if len(data) > 9 else False
        )
