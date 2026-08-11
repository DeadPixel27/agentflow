"""Bank Statement Parser — transaction extraction from bank statements."""

from app.models.domain.template import PipelineTemplate

BANK_STATEMENT_TEMPLATE = PipelineTemplate(
    template_id="bank_statement",
    name="Bank Statement Parser",
    description="Extract account details and all transactions from bank statements",
    icon="landmark",
    category="finance",
    task_description="Extract account information, balances, and every transaction from bank or financial statements",
    fields=[
        "account_holder",
        "account_number",
        "bank_name",
        "statement_period",
        "currency",
        "opening_balance",
        "closing_balance",
        "transactions",
    ],
    extraction_instructions="""Extract account details and ALL transactions from the bank statement.

FIELD LOCATIONS AND GUIDANCE:
- account_holder: Name on the account. Usually near top, labeled "Account Holder", "Name", "Customer". Return full name.
- account_number: Account number as printed. Often partially masked (e.g. "****1234", "XXXX-5678"). Extract exactly as shown.
- bank_name: Name of the financial institution. Usually in header/logo area.
- statement_period: The date range this statement covers. Look for "Statement Period", "From/To", "Period". Return as a string: "YYYY-MM-DD to YYYY-MM-DD".
- currency: ISO 4217 code. Infer from symbol, bank locale, or explicit mention.
- opening_balance: Balance at start of period. Look for "Opening Balance", "Beginning Balance", "Previous Balance", "Balance Brought Forward". Plain number.
- closing_balance: Balance at end of period. Look for "Closing Balance", "Ending Balance", "Balance Carried Forward". Plain number.
- transactions: Array of ALL transaction rows. Each object: {"date": "YYYY-MM-DD", "description": string, "amount": number, "type": "debit" or "credit"}.
  - date: Transaction date. Return as YYYY-MM-DD.
  - description: Transaction description or payee. Extract as-is but trim excess whitespace.
  - amount: Transaction amount as a POSITIVE number (always positive).
  - type: "debit" if it reduces the balance (withdrawals, payments, fees), "credit" if it increases it (deposits, transfers in, interest).
Look for the transaction table - it may span multiple pages. Extract EVERY row, do not truncate.

IMPORTANT:
- Bank statements can be multi-page. Transaction tables may continue across pages - extract ALL rows.
- Debit/credit may be indicated by: separate columns (Debit | Credit), +/- signs, "DR"/"CR" labels, or parentheses for debits.
- Running balance column (if present) is NOT a transaction - do not extract it as a transaction.
- Header rows, subtotals, and page footers should NOT be extracted as transactions.

EXAMPLE EXTRACTION:
Input: "FIRST NATIONAL BANK\\nAccount: John Smith | ****4567\\nPeriod: Mar 1-31, 2024\\nOpening: $5,230.00\\n03/01 PAYROLL DEPOSIT  +2,500.00\\n03/05 AMAZON.COM -89.99\\n03/10 RENT PAYMENT  -1,500.00\\nClosing: $6,140.01"
Output: {"account_holder": "John Smith", "account_number": "****4567", "bank_name": "First National Bank", "statement_period": "2024-03-01 to 2024-03-31", "currency": "USD", "opening_balance": 5230.00, "closing_balance": 6140.01, "transactions": [{"date": "2024-03-01", "description": "Payroll Deposit", "amount": 2500.00, "type": "credit"}, {"date": "2024-03-05", "description": "Amazon.com", "amount": 89.99, "type": "debit"}, {"date": "2024-03-10", "description": "Rent Payment", "amount": 1500.00, "type": "debit"}]}""",
    rules=[
        {
            "field": "transactions",
            "operator": "gt",
            "value": 5000,
            "flag_name": "large_transaction",
        },
    ],
    output_format="csv",
    suggested_steps=[
        "processor.ocr",
        "transform.field_extractor",
        "transform.rules",
        "output.formatter",
    ],
    sort_order=8,
)
