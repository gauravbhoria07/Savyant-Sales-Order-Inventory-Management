import csv
import io
from decimal import Decimal, InvalidOperation
from django.db import transaction
from .models import Product
from inventory.models import StockMovement


def import_products_csv(csv_file, user):
    """
    Imports products from an uploaded CSV file with all-or-nothing validation:
    Expected CSV columns:
    product_code,product_name,category,price,stock_quantity,status

    Validation rules:
    - Validate header row contains all required columns.
    - Validate each row for non-empty values.
    - Reject duplicate product codes within the CSV file itself.
    - Reject product codes already present in the database.
    - Reject negative prices or invalid numbers.
    - Reject negative stock quantities or non-integer values.
    - Reject statuses other than 'Active' or 'Inactive'.
    - If ANY error is found, reject the ENTIRE import and return detailed row errors.
    - If completely valid, create products and record 'OPENING' stock movements.
    """
    errors = []
    required_columns = {'product_code', 'product_name', 'category', 'price', 'stock_quantity', 'status'}

    try:
        content = csv_file.read().decode('utf-8-sig')
    except UnicodeDecodeError:
        try:
            csv_file.seek(0)
            content = csv_file.read().decode('latin-1')
        except Exception:
            return False, ["Unable to read CSV file. Please ensure it is UTF-8 encoded."], 0

    reader = csv.DictReader(io.StringIO(content))

    # Strip spaces from fieldnames
    if not reader.fieldnames:
        return False, ["The CSV file is empty or missing headers."], 0

    fieldnames = [col.strip().lower() for col in reader.fieldnames if col]
    missing_columns = required_columns - set(fieldnames)
    if missing_columns:
        return False, [f"Missing required CSV column(s): {', '.join(sorted(missing_columns))}"], 0

    rows_to_import = []
    seen_in_file = set()

    for row_idx, raw_row in enumerate(reader, start=2):  # start=2 considering header is line 1
        # Normalize keys and values
        row = {k.strip().lower(): (v.strip() if v else "") for k, v in raw_row.items() if k}

        code = row.get('product_code', '')
        name = row.get('product_name', '')
        category = row.get('category', '')
        price_str = row.get('price', '')
        qty_str = row.get('stock_quantity', '')
        status_raw = row.get('status', '').upper()

        # Check required values
        if not code:
            errors.append(f"Row {row_idx}: 'product_code' cannot be empty.")
        if not name:
            errors.append(f"Row {row_idx}: 'product_name' cannot be empty.")
        if not category:
            errors.append(f"Row {row_idx}: 'category' cannot be empty.")

        # Check duplicate code within file
        if code:
            if code in seen_in_file:
                errors.append(f"Row {row_idx}: Duplicate product code '{code}' within the CSV file.")
            else:
                seen_in_file.add(code)

            # Check if code already exists in DB
            if Product.objects.filter(code=code).exists():
                errors.append(f"Row {row_idx}: Product code '{code}' already exists in the database.")

        # Validate price
        try:
            price_val = Decimal(price_str)
            if price_val < Decimal('0.00'):
                errors.append(f"Row {row_idx}: Price cannot be negative (found: {price_str}).")
        except (InvalidOperation, TypeError):
            errors.append(f"Row {row_idx}: Invalid price value '{price_str}'. Must be a valid non-negative number.")
            price_val = Decimal('0.00')

        # Validate stock quantity
        try:
            qty_val = int(qty_str)
            if qty_val < 0:
                errors.append(f"Row {row_idx}: Stock quantity cannot be negative (found: {qty_str}).")
        except (ValueError, TypeError):
            errors.append(f"Row {row_idx}: Invalid stock quantity '{qty_str}'. Must be a non-negative whole number.")
            qty_val = 0

        # Validate status
        if status_raw in ('ACTIVE', 'ACTIVE.'):
            status_val = Product.Status.ACTIVE
        elif status_raw in ('INACTIVE', 'INACTIVE.'):
            status_val = Product.Status.INACTIVE
        else:
            errors.append(f"Row {row_idx}: Invalid status '{row.get('status')}'. Must be 'Active' or 'Inactive'.")
            status_val = Product.Status.ACTIVE

        rows_to_import.append({
            'code': code,
            'name': name,
            'category': category,
            'price': price_val,
            'stock_quantity': qty_val,
            'status': status_val,
        })

    if not rows_to_import and not errors:
        return False, ["The CSV file contains headers but no product data rows."], 0

    # All-or-nothing: if any errors occurred, stop and import NOTHING
    if errors:
        return False, errors, 0

    # Save all products and opening movements atomically
    with transaction.atomic():
        created_count = 0
        for item in rows_to_import:
            product = Product.objects.create(
                code=item['code'],
                name=item['name'],
                category=item['category'],
                price=item['price'],
                stock_quantity=item['stock_quantity'],
                status=item['status'],
            )
            created_count += 1

            if item['stock_quantity'] > 0:
                StockMovement.objects.create(
                    product=product,
                    movement_type=StockMovement.MovementType.OPENING,
                    quantity_change=item['stock_quantity'],
                    reason="Opening stock via CSV import",
                    created_by=user,
                )

    return True, [], created_count
