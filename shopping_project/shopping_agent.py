import json
import os
import sqlite3
from typing import Optional

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langchain_groq import ChatGroq
import base64

from reviews_api import get_product_ratings

load_dotenv()

DB_PATH = os.path.join(os.path.dirname(__file__), "store.db")

llm = ChatGroq(model="qwen/qwen3.8-27b",temperature=0)
vision_llm = ChatGroq(model="qwen/qwen3.8-27b",temperature=0, modality="vision")

@tool
def search_products(query: str, max_price: Optional[float] = None, is_organic: Optional[bool] = None) -> str:
    """Search the product catalog by name or description, with optional filters."""
    sql = """
        SELECT name, description, price, is_organic
        FROM products
        WHERE (name LIKE ? OR description LIKE ?)
    """
    params = [f"%{query}%", f"%{query}%"]

    if max_price is not None:
        sql += " AND price <= ?"
        params.append(max_price)
    if is_organic is not None:
        sql += " AND is_organic = ?"
        params.append(int(is_organic))
    sql += " ORDER BY name"

    try:
        with sqlite3.connect(DB_PATH) as connection:
            rows = connection.execute(sql, params).fetchall()
    except sqlite3.Error as exc:
        return json.dumps({"error": f"Unable to search products: {exc}"})

    products = [
        {
            "name": name,
            "description": description,
            "price": price,
            "is_organic": bool(organic),
        }
        for name, description, price, organic in rows
    ]
    return json.dumps({"products": products})

@tool
def get_rating(product_id:int) -> str:
    """
    get the average customer rating and total review count for a product by its ID.
    Return a json object with: product_id, average_rating,review_count.
    """
    result = get_product_ratings(product_id)
    return json.dumps(result)

@tool
def checkout(product_id: int) -> str:
    """
    Place an order for the given product id.Saves the order to the database and returns
    a confimation message with the order ID, product name, and price.
    """
    try:
        with sqlite3.connect(DB_PATH) as connection:
            product = connection.execute(
                "SELECT name, price FROM products WHERE product_id = ?",
                (product_id,),
            ).fetchone()
            if product is None:
                return json.dumps({"error": f"Product {product_id} was not found."})

            cursor = connection.execute(
                "INSERT INTO orders (product_id) VALUES (?)",
                (product_id,),
            )
            order_id = cursor.lastrowid
    except sqlite3.Error as exc:
        return json.dumps({"error": f"Unable to place order: {exc}"})

    name, price = product
    return json.dumps({
        "message": "Order placed successfully.",
        "order_id": order_id,
        "product_name": name,
        "price": price,
    })


### Agent Setup
agent = create_agent(
    tools=[search_products, get_rating, checkout],
    model=llm,
    system_prompt="You are a helpful shopping assistant. You can search for products, get product ratings, and place orders.",
)

def describe_product_image(image_path: str) -> str:
    """Analyze the product image and return a description of the product."""
    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("ascii")

    ext = os.path.splitext(image_path)[1].lower().lstrip(".")
    mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"
    image_message = HumanMessage(
        content=[
            {"type": "text", "text": "Describe this product image."},
            {
                "type": "image_url",
                "image_url": {"url": f"data:{mime};base64,{image_data}"},
            },
        ]
    )
    response = vision_llm.invoke([image_message])
    return str(response.content)


if __name__ == "__main__":
    result = agent.invoke(
        {
            "messages":[
                {
                    "role":"user",
                    "content":"I want to buy organic honey under $10. Can you find some options for me?"
                }
            ]
        }
    )
    print(result["messages"][-1].content)