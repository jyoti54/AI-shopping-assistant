"""
Reviews Api- reads from the 'reviews' table in store.db and returns
aggregated rating information for products.
"""
    
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "store.db")

def get_product_ratings(product_id: int) -> dict:

    """Return the average rating and number of reviews for a product."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT AVG(rating), COUNT(*) FROM reviews WHERE product_id = ?",
        (product_id,),
    )
    row = cursor.fetchone()
    conn.close()

    avg = round(row[0], 2) if row and row[0] is not None else 0.0
    count = row[1] if row else 0
    
    return {
        "product_id": product_id,
        "average_rating": avg,
        "review_count": count,
    }
    
def get_ratings_for_products(product_ids: list[int]) -> list[dict]:
    """Return ratings for a list of product IDs."""

    if not product_ids:
        return []

    placeholders = ", ".join("?" for _ in product_ids)
    conn = sqlite3.connect(DB_PATH)
    try:
        rows = conn.execute(
            f"""
            SELECT product_id, AVG(rating), COUNT(*)
            FROM reviews
            WHERE product_id IN ({placeholders})
            GROUP BY product_id
            """,
            product_ids,
        ).fetchall()
    finally:
        conn.close()

    ratings_by_product = {
        product_id: {"average_rating": 0.0, "review_count": 0}
        for product_id in product_ids
    }
    ratings_by_product.update(
        {
            row[0]: {
                "average_rating": round(row[1], 2) if row[1] is not None else 0.0,
                "review_count": row[2],
            }
            for row in rows
        }
    )

    return [
        {"product_id": product_id, **ratings_by_product[product_id]}
        for product_id in product_ids
    ]
    
if __name__ == "__main__":
    # Test ratings for one product, then for several products.
    print("Single product:")
    print(get_product_ratings(1))

    print("Multiple products:")
    print(get_ratings_for_products([1, 2, 3]))
    