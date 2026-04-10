from typing import Any, Dict, Optional
from app.db import DatabaseConnectionError, DatabaseQueryError, run_query
from app.logger import logger
from app.llm import get_llm,safe_llm_call
from pydantic import BaseModel, Field

class CustomerQueryExtraction(BaseModel):
    customer_name: Optional[str] = Field(
        default=None,
        description="Full or partial customer name mentioned in the query, if any."
    )
    include_profile: bool = Field(
        default=False,
        description="Whether the user is asking for customer profile details."
    )
    include_tickets: bool = Field(
        default=False,
        description="Whether the user is asking for support ticket details."
    )
    include_orders: bool = Field(
        default=False,
        description="Whether the user is asking for order details."
    )

def extract_customer_query_info(query: str) -> Optional[str]:
    logger.info("LLM_CALL | extracting customer name and requested sections from query")

    llm = get_llm()
    structured_llm = llm.with_structured_output(CustomerQueryExtraction)

    prompt = f"""
        You are an information extraction assistant.

        Extract:
        1. customer_name
        2. whether the user wants profile details
        3. whether the user wants support ticket details
        4. whether the user wants order details

        Rules:
        - include_profile = true if the user asks for profile, customer details, or overview of the customer
        - include_tickets = true if the user asks for ticket, issue, complaint, support history, or support details
        - include_orders = true if the user asks for order, purchase, shipment, or buying history
        - Return false for anything not clearly requested
        - Return null for customer_name if no customer name is clearly mentioned

        Examples:
        - "Give me a quick overview of customer Ema's profile" ->
        customer_name="Ema", include_profile=true, include_tickets=false, include_orders=false

        - "Show Ravi Sharma's order history" ->
        customer_name="Ravi Sharma", include_profile=false, include_tickets=false, include_orders=true

        - "Give me Alan Brown's profile and past support ticket details" ->
        customer_name="Alan Brown", include_profile=true, include_tickets=true, include_orders=false

        - "What is the refund policy?" ->
        customer_name=null, include_profile=false, include_tickets=false, include_orders=false

        User query:
        {query}
        """


    result = safe_llm_call(lambda: structured_llm.invoke(prompt))
    logger.info(
        "LLM_RESULT | "
        f"customer_name={result.customer_name} | "
        f"include_profile={result.include_profile} | "
        f"include_tickets={result.include_tickets} | "
        f"include_orders={result.include_orders}"
    )
    return result

def _query_customer_profile(first: Optional[str], customer_name: str):
    if first:
        where_condition = "LOWER(c.first_name) = LOWER(%s)"
        match_name = first
    else:
        where_condition = "LOWER(c.first_name || ' ' || c.last_name) = LOWER(%s)"
        match_name = customer_name
    return run_query(
        f"""
        SELECT *
        FROM customers c
        WHERE {where_condition}
        LIMIT 1
        """,
        (match_name,),
    )

def _query_customer_tickets(first: Optional[str], customer_name: str):
    if first:
        where_condition = "LOWER(c.first_name) = LOWER(%s)"
        match_name = first
    else:
        where_condition = "LOWER(c.first_name || ' ' || c.last_name) = LOWER(%s)"
        match_name = customer_name

    return run_query(
        f"""
        SELECT *
        FROM support_tickets t
        JOIN customers c ON c.customer_id = t.customer_id
        WHERE {where_condition}
        ORDER BY t.ticket_created DESC
        LIMIT 4
        """,
        (match_name,),
    )


def _query_customer_orders(first: Optional[str], customer_name: str):
    if first:
        where_condition = "LOWER(c.first_name) = LOWER(%s)"
        match_name = first
    else:
        where_condition = "LOWER(c.first_name || ' ' || c.last_name) = LOWER(%s)"
        match_name = customer_name
    return run_query(
        f"""
        SELECT *
        FROM orders o
        JOIN customers c ON c.customer_id = o.customer_id
        WHERE {where_condition}
        ORDER BY o.order_date DESC
        LIMIT 4
        """,
        (match_name,),
    )


def _query_open_ticket_summary():
    return run_query(
        """
        SELECT COUNT(*) AS open_tickets
        FROM support_tickets
        """
    )

def lookup_customer_support_data(query: str) -> Dict[str, Any]:
    logger.info("TOOL_CALL | SQL tool invoked")

    try:
        extracted = extract_customer_query_info(query)
    except Exception as exc:
        logger.exception("Failed to extract structured customer query info")
        return {
            "error": "Could not interpret the customer lookup request.",
            "summary": {},
        }

    customer_name = extracted.customer_name.strip() if extracted.customer_name else None

    try:
        if customer_name:

            logger.info("CUSTOMER_MATCH | %s", customer_name)
            parts = customer_name.split()
            first = parts[0] if len(parts) == 1 else None

            response: Dict[str, Any] = {"error": None}

            if extracted.include_profile:
                customer = _query_customer_profile(first, customer_name)
                response["customer"] = customer[0] if customer else {}

            if extracted.include_tickets:
                tickets = _query_customer_tickets(first, customer_name)
                response["tickets"] = tickets

            if extracted.include_orders:
                orders = _query_customer_orders(first, customer_name)
                response["orders"] = orders

            logger.info("TOOL_RESULT | SQL | keys_returned=%s", list(response.keys()))
            return response

        logger.info("CUSTOMER_MATCH | none")
        logger.info("FALLBACK | returning generic support summary")
        open_tickets = _query_open_ticket_summary()
        logger.info("TOOL_RESULT | SQL fallback | rows=%s", len(open_tickets))
        return {
            "summary": open_tickets[0] if open_tickets else {},
            "error": None,
        }
    except DatabaseConnectionError as exc:
        logger.warning("Database unavailable during SQL tool call: %s", exc)
        return {
            "error": "Database is temporarily unavailable.",
            "summary": {},
        }
    except DatabaseQueryError as exc:
        logger.warning("Database query failed during SQL tool call: %s", exc)
        return {
            "error": "Could not complete the database lookup.",
            "summary": {},
        }
    except Exception as exc:
        logger.exception("Unexpected SQL tool failure")
        return {
            "error": "Unexpected error while retrieving customer support data.",
            "summary": {},
        }
