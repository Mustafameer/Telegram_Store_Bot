
def test_parsing():
    query = """
        INSERT INTO Orders (BuyerID, SellerID, Total, DeliveryAddress, Notes, PaymentMethod, FullyPaid) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    query += " RETURNING OrderID"
    
    # Logic from CursorWrapper
    stripped = query.strip().upper()
    is_insert = stripped.startswith("INSERT")
    has_returning = "RETURNING" in query.upper()
    
    print(f"Query: {query}")
    print(f"Stripped Upper: {stripped[:50]}...")
    print(f"Is Insert: {is_insert}")
    print(f"Has Returning: {has_returning}")
    
    if is_insert and has_returning:
        print("✅ CursorWrapper logic WOULD trigger.")
    else:
        print("❌ CursorWrapper logic WOULD NOT trigger.")

if __name__ == "__main__":
    test_parsing()
