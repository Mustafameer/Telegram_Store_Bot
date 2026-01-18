#!/usr/bin/env python3
"""
Script to drop and recreate auction tables in PostgreSQL cloud database
This ensures the tables are created with the correct schema
"""

import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    print("❌ ERROR: DATABASE_URL not found in environment variables!")
    exit(1)

try:
    # Connect to the database
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    print("🔌 Connected to PostgreSQL cloud database")
    
    # Drop tables in reverse order of creation (respecting foreign keys)
    tables_to_drop = [
        'AuctionProducts',
        'AuctionResults',
        'AuctionBids',
        'AuctionBidders',
        'Auctions'
    ]
    
    print("\n🗑️ Dropping existing auction tables...")
    for table in tables_to_drop:
        try:
            cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
            print(f"  ✅ Dropped {table}")
        except Exception as e:
            print(f"  ⚠️ Error dropping {table}: {e}")
    
    conn.commit()
    
    # Recreate tables with correct PostgreSQL syntax
    print("\n🔨 Creating auction tables with correct schema...")
    
    # 1. Auctions
    cursor.execute("""
        CREATE TABLE Auctions(
            AuctionID SERIAL PRIMARY KEY,
            ProductID INTEGER NOT NULL,
            OriginalSellerID INTEGER NOT NULL,
            AuctionStoreID INTEGER NOT NULL,
            StartPrice REAL NOT NULL,
            AuctionStartAt TIMESTAMP NOT NULL,
            AuctionEndAt TIMESTAMP NOT NULL,
            Status TEXT DEFAULT 'active',
            CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UpdatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ProductID) REFERENCES Products(ProductID),
            FOREIGN KEY (OriginalSellerID) REFERENCES Sellers(SellerID),
            FOREIGN KEY (AuctionStoreID) REFERENCES Sellers(SellerID)
        )
    """)
    print("  ✅ Created Auctions table")
    
    # 2. AuctionBidders
    cursor.execute("""
        CREATE TABLE AuctionBidders(
            BidderID SERIAL PRIMARY KEY,
            AuctionID INTEGER NOT NULL,
            BidderName TEXT NOT NULL,
            BidderPhone TEXT NOT NULL,
            TelegramID BIGINT,
            RegistrationTime TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (AuctionID) REFERENCES Auctions(AuctionID),
            UNIQUE(AuctionID, BidderPhone)
        )
    """)
    print("  ✅ Created AuctionBidders table")
    
    # 3. AuctionBids
    cursor.execute("""
        CREATE TABLE AuctionBids(
            BidID SERIAL PRIMARY KEY,
            AuctionID INTEGER NOT NULL,
            BidderID INTEGER NOT NULL,
            BidAmount REAL NOT NULL,
            BidTime TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (AuctionID) REFERENCES Auctions(AuctionID),
            FOREIGN KEY (BidderID) REFERENCES AuctionBidders(BidderID)
        )
    """)
    print("  ✅ Created AuctionBids table")
    
    # 4. AuctionResults
    cursor.execute("""
        CREATE TABLE AuctionResults(
            ResultID SERIAL PRIMARY KEY,
            AuctionID INTEGER NOT NULL UNIQUE,
            WinnerBidderID INTEGER,
            WinnerName TEXT,
            WinnerPhone TEXT,
            FinalPrice REAL,
            AuctionEndedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (AuctionID) REFERENCES Auctions(AuctionID),
            FOREIGN KEY (WinnerBidderID) REFERENCES AuctionBidders(BidderID)
        )
    """)
    print("  ✅ Created AuctionResults table")
    
    # 5. AuctionProducts
    cursor.execute("""
        CREATE TABLE AuctionProducts(
            AuctionProductID SERIAL PRIMARY KEY,
            AuctionID INTEGER NOT NULL,
            ProductID INTEGER NOT NULL,
            AuctionStoreProductID INTEGER,
            CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (AuctionID) REFERENCES Auctions(AuctionID),
            FOREIGN KEY (ProductID) REFERENCES Products(ProductID),
            FOREIGN KEY (AuctionStoreProductID) REFERENCES Products(ProductID)
        )
    """)
    print("  ✅ Created AuctionProducts table")
    
    conn.commit()
    print("\n✅ All auction tables recreated successfully!")
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    if conn:
        conn.rollback()
finally:
    if conn:
        cursor.close()
        conn.close()
        print("🔌 Database connection closed")
