"""
Utility functions for executing stored procedures in SQL Server.

Provides convenient functions for calling and executing stored procedures
from backend code with proper parameter handling and result processing.
"""

import asyncio
from datetime import datetime, date
from typing import Any, Dict, List, Optional, Tuple, Union

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger

logger = get_logger(__name__)


async def execute_stored_procedure(
    session: AsyncSession,
    procedure_name: str,
    parameters: Optional[Dict[str, Any]] = None,
    fetch_results: bool = True,
    fetch_multiple: bool = False,
) -> Union[List[Dict[str, Any]], List[List[Dict[str, Any]]], None]:
    """
    Execute a stored procedure and optionally fetch results.

    Args:
        session: Database session
        procedure_name: Name of the stored procedure
        parameters: Dictionary of parameter names and values
        fetch_results: Whether to fetch and return results
        fetch_multiple: If True, returns a list of result sets; if False, returns only the first result set

    Returns:
        - If fetch_results=False: None
        - If fetch_multiple=False: List of dictionaries with result rows from first result set
        - If fetch_multiple=True: List of lists, each containing dictionaries with result rows

    Example:
        ```python
        from src.core.stored_procedure_utils import execute_stored_procedure
        from src.database import get_session

        # Single result set
        async with get_session() as session:
            results = await execute_stored_procedure(
                session=session,
                procedure_name="UIActionCreateDonation",
                parameters={
                    "CompanyId": 1,
                    "DonorId": 123,
                    "Amount": 100.00,
                    "PaymentMethod": "credit_card"
                }
            )
            print(f"Procedure returned: {results}")
        
        # Multiple result sets
        async with get_session() as session:
            results = await execute_stored_procedure(
                session=session,
                procedure_name="GetTransactionWithDetails",
                parameters={"TransactionId": 123},
                fetch_multiple=True
            )
            # results[0] = transaction header
            # results[1] = transaction details
        ```
    """
    try:
        params = parameters or {}

        # Build parameter string for EXEC statement
        param_list = []
        for param_name, param_value in params.items():
            # Handle different parameter types
            if param_value is None:
                param_list.append(f"@{param_name} = NULL")
            elif isinstance(param_value, bool):
                param_list.append(f"@{param_name} = {1 if param_value else 0}")
            elif isinstance(param_value, (int, float)):
                param_list.append(f"@{param_name} = {param_value}")
            elif isinstance(param_value, datetime):
                # Format datetime in ISO 8601 format that SQL Server understands
                # Use format: 'YYYY-MM-DDTHH:MM:SS.mmm' for datetime
                formatted_date = param_value.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]  # Trim to milliseconds
                param_list.append(f"@{param_name} = '{formatted_date}'")
            elif isinstance(param_value, date):
                # Format date in ISO 8601 format: 'YYYY-MM-DD'
                formatted_date = param_value.strftime('%Y-%m-%d')
                param_list.append(f"@{param_name} = '{formatted_date}'")
            elif isinstance(param_value, str):
                # Escape single quotes in strings
                escaped_value = param_value.replace("'", "''")
                param_list.append(f"@{param_name} = '{escaped_value}'")
            else:
                # For other types, convert to string and escape
                escaped_value = str(param_value).replace("'", "''")
                param_list.append(f"@{param_name} = '{escaped_value}'")

        param_string = ", ".join(param_list) if param_list else ""
        
        # Build EXEC statement
        if param_string:
            sql = f"EXEC {procedure_name} {param_string}"
        else:
            sql = f"EXEC {procedure_name}"

        logger.info(
            f"Executing stored procedure: {procedure_name}",
            extra={"procedure_name": procedure_name, "parameters": params}
        )
        logger.debug(f"SQL: {sql}")

        # Execute the stored procedure
        result = await session.execute(text(sql))
        
        # Fetch results if requested (BEFORE commit)
        fetched_results = None
        if fetch_results:
            if fetch_multiple:
                # Fetch all result sets using raw connection
                all_results = []
                
                # Get the underlying cursor from the result
                cursor = result.cursor
                
                # Helper function to fetch data from cursor synchronously
                def fetch_result_set(cursor):
                    rows = cursor.fetchall()
                    if rows and cursor.description:
                        columns = [desc[0] for desc in cursor.description]
                        return [dict(zip(columns, row)) for row in rows]
                    return []
                
                # Fetch first result set
                result_data = await asyncio.to_thread(fetch_result_set, cursor)
                all_results.append(result_data)
                
                # Try to fetch additional result sets
                def has_more_results(cursor):
                    try:
                        return cursor.nextset()
                    except Exception:
                        return False
                
                while await asyncio.to_thread(has_more_results, cursor):
                    try:
                        result_data = await asyncio.to_thread(fetch_result_set, cursor)
                        all_results.append(result_data)
                    except Exception as e:
                        logger.debug(f"No more result sets or error: {e}")
                        break
                
                fetched_results = all_results
                logger.info(
                    f"Stored procedure {procedure_name} returned {len(all_results)} result set(s)"
                )
            else:
                # Fetch only first result set
                rows = result.fetchall()
                if rows:
                    columns = result.keys()
                    fetched_results = [dict(zip(columns, row)) for row in rows]
                    logger.info(
                        f"Stored procedure {procedure_name} returned {len(fetched_results)} rows"
                    )
                else:
                    logger.info(f"Stored procedure {procedure_name} returned no results")
                    fetched_results = []
        
        # Commit the transaction AFTER fetching all results
        await session.commit()
        
        if fetch_results:
            logger.info(f"Stored procedure {procedure_name} executed successfully with results")
            return fetched_results
        
        logger.info(f"Stored procedure {procedure_name} executed successfully without results")
        return None

    except Exception as e:
        await session.rollback()
        logger.error(
            f"Error executing stored procedure {procedure_name}: {e}",
            exc_info=True,
            extra={"procedure_name": procedure_name, "parameters": params}
        )
        raise


async def execute_stored_procedure_with_output(
    session: AsyncSession,
    procedure_name: str,
    parameters: Optional[Dict[str, Any]] = None,
    output_params: Optional[Dict[str, str]] = None,
    fetch_multiple: bool = False,
) -> Tuple[Union[List[Dict[str, Any]], List[List[Dict[str, Any]]], None], Dict[str, Any]]:
    """
    Execute a stored procedure with output parameters.

    Args:
        session: Database session
        procedure_name: Name of the stored procedure
        parameters: Dictionary of input parameter names and values
        output_params: Dictionary of output parameter names and their SQL types
                      (e.g., {"TransactionId": "INT", "Message": "NVARCHAR(500)"})
        fetch_multiple: If True, returns all result sets; if False, returns only the first result set

    Returns:
        Tuple of (result rows, output parameters dictionary)
        - If fetch_multiple=False: (List[Dict] or None, Dict)
        - If fetch_multiple=True: (List[List[Dict]] or None, Dict)

    Example:
        ```python
        # Single result set
        results, outputs = await execute_stored_procedure_with_output(
            session=session,
            procedure_name="CreateTransaction",
            parameters={"Amount": 100.00},
            output_params={"TransactionId": "INT", "Message": "NVARCHAR(500)"}
        )
        print(f"Transaction ID: {outputs['TransactionId']}")
        print(f"Message: {outputs['Message']}")
        
        # Multiple result sets
        results, outputs = await execute_stored_procedure_with_output(
            session=session,
            procedure_name="CreateTransactionWithDetails",
            parameters={"Amount": 100.00},
            output_params={"TransactionId": "INT"},
            fetch_multiple=True
        )
        # results[0] = transaction data
        # results[1] = related details
        ```
    """
    try:
        params = parameters or {}
        out_params = output_params or {}

        # Build parameter declarations for output parameters
        declare_statements = []
        for param_name, param_type in out_params.items():
            declare_statements.append(f"DECLARE @{param_name} {param_type}")

        # Build input parameter list
        param_list = []
        for param_name, param_value in params.items():
            if param_value is None:
                param_list.append(f"@{param_name} = NULL")
            elif isinstance(param_value, bool):
                param_list.append(f"@{param_name} = {1 if param_value else 0}")
            elif isinstance(param_value, (int, float)):
                param_list.append(f"@{param_name} = {param_value}")
            elif isinstance(param_value, str):
                escaped_value = param_value.replace("'", "''")
                param_list.append(f"@{param_name} = '{escaped_value}'")
            else:
                escaped_value = str(param_value).replace("'", "''")
                param_list.append(f"@{param_name} = '{escaped_value}'")

        # Add output parameters to the parameter list
        for param_name in out_params.keys():
            param_list.append(f"@{param_name} = @{param_name} OUTPUT")

        param_string = ", ".join(param_list) if param_list else ""

        # Build select statement for output parameters
        select_outputs = ", ".join([f"@{name} AS {name}" for name in out_params.keys()])

        # Build complete SQL
        sql_parts = declare_statements + [
            f"EXEC {procedure_name} {param_string}",
            f"SELECT {select_outputs}"
        ]
        sql = "; ".join(sql_parts)

        logger.debug(
            f"Executing stored procedure with outputs: {procedure_name}",
            extra={"procedure_name": procedure_name, "parameters": params, "output_params": out_params}
        )
        logger.debug(f"SQL: {sql}")

        # Execute the stored procedure
        result = await session.execute(text(sql))
        
        # Fetch result sets (BEFORE commit)
        result_rows = None
        output_values = {}
        cursor = result.cursor
        
        # Helper function to check if result set is output params
        def is_output_params(columns, out_params):
            return set(columns) == set(out_params.keys())
        
        # Helper function to fetch data from cursor
        def fetch_result_set(cursor):
            rows = cursor.fetchall()
            if rows and cursor.description:
                columns = [desc[0] for desc in cursor.description]
                return rows, columns
            return None, None
        
        if fetch_multiple:
            # Fetch all result sets except the last one (which should be output params)
            all_results = []
            
            # Fetch first result set
            rows, columns = await asyncio.to_thread(fetch_result_set, cursor)
            if rows and columns:
                # Check if this looks like the output parameters result
                if is_output_params(columns, out_params):
                    # This is the output parameters result
                    output_values = dict(zip(columns, rows[0]))
                else:
                    # This is a regular result set
                    all_results.append([dict(zip(columns, row)) for row in rows])
            
            # Try to fetch additional result sets
            def has_more_results(cursor):
                try:
                    return cursor.nextset()
                except Exception:
                    return False
            
            while await asyncio.to_thread(has_more_results, cursor):
                try:
                    rows, columns = await asyncio.to_thread(fetch_result_set, cursor)
                    if rows and columns:
                        # Check if this looks like the output parameters result
                        if is_output_params(columns, out_params):
                            # This is the output parameters result (last result set)
                            output_values = dict(zip(columns, rows[0]))
                            break
                        else:
                            # This is a regular result set
                            all_results.append([dict(zip(columns, row)) for row in rows])
                except Exception as e:
                    logger.debug(f"No more result sets: {e}")
                    break
            
            result_rows = all_results if all_results else None
            
        else:
            # Fetch only first result set and output parameters
            try:
                # Fetch first result set
                rows, columns = await asyncio.to_thread(fetch_result_set, cursor)
                if rows and columns:
                    # Check if this looks like the output parameters result
                    if is_output_params(columns, out_params):
                        # This is the output parameters result
                        output_values = dict(zip(columns, rows[0]))
                    else:
                        # This is regular result data
                        result_rows = [dict(zip(columns, row)) for row in rows]
                        
                        # Try to get the next result set for output params
                        def has_more_results(cursor):
                            try:
                                return cursor.nextset()
                            except Exception:
                                return False
                        
                        if await asyncio.to_thread(has_more_results, cursor):
                            try:
                                next_rows, next_columns = await asyncio.to_thread(fetch_result_set, cursor)
                                if next_rows and next_columns:
                                    if is_output_params(next_columns, out_params):
                                        output_values = dict(zip(next_columns, next_rows[0]))
                            except Exception as e:
                                logger.debug(f"Could not fetch output params: {e}")
            except Exception as e:
                logger.warning(f"Could not fetch all results: {e}")

        # Commit the transaction AFTER fetching all results
        await session.commit()
        
        logger.info(
            f"Stored procedure {procedure_name} executed successfully",
            extra={"output_values": output_values}
        )
        
        return result_rows, output_values

    except Exception as e:
        await session.rollback()
        logger.error(
            f"Error executing stored procedure with outputs {procedure_name}: {e}",
            exc_info=True,
            extra={"procedure_name": procedure_name, "parameters": params}
        )
        raise



