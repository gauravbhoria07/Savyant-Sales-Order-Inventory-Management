/**
 * order_form.js - Vanilla JavaScript for dynamic sales order creation
 * 
 * Features:
 * 1. Add / Remove dynamic product rows
 * 2. Fetch and display selected product rate & available stock
 * 3. Live calculations: Item amount, Subtotal, Discount amount, Grand total
 * 4. Client-side input validation with beginner-friendly error messages
 * 5. Duplicate product detection across rows
 * 6. Duplicate submission prevention (disables submit button during processing)
 */

document.addEventListener('DOMContentLoaded', function () {
    const tableBody = document.getElementById('orderItemsTableBody');
    const addRowBtn = document.getElementById('addRowBtn');
    const orderForm = document.getElementById('orderForm');
    const submitBtn = document.getElementById('submitOrderBtn');
    const discountInput = document.getElementById('discountPercentage');
    const subtotalDisplay = document.getElementById('subtotalDisplay');
    const discountAmountDisplay = document.getElementById('discountAmountDisplay');
    const grandTotalDisplay = document.getElementById('grandTotalDisplay');
    const validationAlert = document.getElementById('validationAlert');
    const validationMessage = document.getElementById('validationMessage');

    // Products catalog parsed from the backend JSON context
    let catalog = {};
    if (window.PRODUCTS_CATALOG) {
        window.PRODUCTS_CATALOG.forEach(p => {
            catalog[p.id] = p;
        });
    }

    // Helper: Format number to Indian Rupee 2 decimal places
    function formatCurrency(val) {
        return Number(val || 0).toFixed(2);
    }

    // Show alert message
    function showAlert(msg) {
        if (validationAlert && validationMessage) {
            validationMessage.innerText = msg;
            validationAlert.classList.remove('d-none');
            validationAlert.scrollIntoView({ behavior: 'smooth', block: 'center' });
        } else {
            alert(msg);
        }
    }

    // Hide alert message
    function hideAlert() {
        if (validationAlert) {
            validationAlert.classList.add('d-none');
        }
    }

    // Build product dropdown options HTML
    function buildProductOptions(selectedId = '') {
        let options = '<option value="">-- Choose Product --</option>';
        if (window.PRODUCTS_CATALOG) {
            window.PRODUCTS_CATALOG.forEach(p => {
                const isSelected = String(p.id) === String(selectedId) ? 'selected' : '';
                options += `<option value="${p.id}" ${isSelected} data-price="${p.price}" data-stock="${p.stock}">${p.code} - ${p.name} (₹${formatCurrency(p.price)})</option>`;
            });
        }
        return options;
    }

    // Add a new dynamic row
    function addNewRow(productId = '', quantity = 1) {
        hideAlert();
        const row = document.createElement('tr');
        row.className = 'item-row';
        row.innerHTML = `
            <td style="min-width: 250px;">
                <select name="product_id[]" class="form-select product-select" required>
                    ${buildProductOptions(productId)}
                </select>
            </td>
            <td class="text-center" style="width: 130px;">
                <span class="badge bg-light text-dark border stock-badge">--</span>
            </td>
            <td class="text-end" style="width: 140px;">
                <div class="input-group input-group-sm">
                    <span class="input-group-text">₹</span>
                    <input type="text" class="form-control text-end rate-input" value="0.00" readonly>
                </div>
            </td>
            <td style="width: 120px;">
                <input type="number" name="quantity[]" class="form-control form-control-sm text-center qty-input" value="${quantity}" min="1" step="1" required>
            </td>
            <td class="text-end fw-semibold" style="width: 150px;">
                ₹<span class="item-amount">0.00</span>
            </td>
            <td class="text-center" style="width: 70px;">
                <button type="button" class="btn btn-outline-danger btn-sm remove-row-btn" title="Remove row">
                    <i class="bi bi-trash"></i>
                </button>
            </td>
        `;

        tableBody.appendChild(row);
        bindRowEvents(row);

        // If productId is preselected, update immediately
        if (productId) {
            updateRow(row);
        }
        recalculateTotals();
    }

    // Update row price, stock and amount based on selected product
    function updateRow(row) {
        const select = row.querySelector('.product-select');
        const stockBadge = row.querySelector('.stock-badge');
        const rateInput = row.querySelector('.rate-input');
        const qtyInput = row.querySelector('.qty-input');
        const amountSpan = row.querySelector('.item-amount');

        const productId = select.value;
        if (productId && catalog[productId]) {
            const product = catalog[productId];
            rateInput.value = formatCurrency(product.price);
            stockBadge.textContent = product.stock;
            if (product.stock <= 5) {
                stockBadge.className = 'badge bg-danger-subtle text-danger border border-danger stock-badge';
            } else {
                stockBadge.className = 'badge bg-success-subtle text-success stock-badge';
            }

            const qty = parseInt(qtyInput.value) || 0;
            const amt = qty * Number(product.price);
            amountSpan.textContent = formatCurrency(amt);
        } else {
            rateInput.value = '0.00';
            stockBadge.textContent = '--';
            stockBadge.className = 'badge bg-light text-dark border stock-badge';
            amountSpan.textContent = '0.00';
        }
        recalculateTotals();
    }

    // Bind event listeners to a row
    function bindRowEvents(row) {
        const select = row.querySelector('.product-select');
        const qtyInput = row.querySelector('.qty-input');
        const removeBtn = row.querySelector('.remove-row-btn');

        select.addEventListener('change', function () {
            hideAlert();
            updateRow(row);
        });

        qtyInput.addEventListener('input', function () {
            hideAlert();
            updateRow(row);
        });

        removeBtn.addEventListener('click', function () {
            hideAlert();
            const allRows = tableBody.querySelectorAll('.item-row');
            if (allRows.length <= 1) {
                showAlert("An order must contain at least one item row.");
                return;
            }
            row.remove();
            recalculateTotals();
        });
    }

    // Recalculate Subtotal, Discount Amount, and Grand Total
    function recalculateTotals() {
        let subtotal = 0;
        const rows = tableBody.querySelectorAll('.item-row');

        rows.forEach(r => {
            const amt = parseFloat(r.querySelector('.item-amount').textContent) || 0;
            subtotal += amt;
        });

        const discPercent = parseFloat(discountInput.value) || 0;
        const discountAmount = (subtotal * discPercent) / 100.0;
        const grandTotal = Math.max(0, subtotal - discountAmount);

        subtotalDisplay.textContent = formatCurrency(subtotal);
        discountAmountDisplay.textContent = formatCurrency(discountAmount);
        grandTotalDisplay.textContent = formatCurrency(grandTotal);
    }

    // Recalculate on discount change
    if (discountInput) {
        discountInput.addEventListener('input', function () {
            const val = parseFloat(this.value);
            if (val < 0) this.value = 0;
            if (val > 20) this.value = 20;
            recalculateTotals();
        });
    }

    // Add row button click
    if (addRowBtn) {
        addRowBtn.addEventListener('click', function () {
            addNewRow();
        });
    }

    // Form submission validation & duplicate prevention
    if (orderForm) {
        orderForm.addEventListener('submit', function (e) {
            hideAlert();
            const customerSelect = document.getElementById('customer_id');
            if (!customerSelect.value) {
                e.preventDefault();
                showAlert("Please select a customer.");
                customerSelect.focus();
                return;
            }

            const rows = tableBody.querySelectorAll('.item-row');
            if (rows.length === 0) {
                e.preventDefault();
                showAlert("Please add at least one product to the order.");
                return;
            }

            const seenProducts = new Set();
            for (let i = 0; i < rows.length; i++) {
                const row = rows[i];
                const select = row.querySelector('.product-select');
                const qtyInput = row.querySelector('.qty-input');
                const pId = select.value;
                const qty = parseInt(qtyInput.value);

                if (!pId) {
                    e.preventDefault();
                    showAlert(`Row ${i + 1}: Please select a product.`);
                    select.focus();
                    return;
                }

                if (seenProducts.has(pId)) {
                    e.preventDefault();
                    const prodName = catalog[pId] ? catalog[pId].name : 'Item';
                    showAlert(`Row ${i + 1}: Duplicate product '${prodName}'. Each product can only be added once.`);
                    select.focus();
                    return;
                }
                seenProducts.add(pId);

                if (isNaN(qty) || qty <= 0) {
                    e.preventDefault();
                    showAlert(`Row ${i + 1}: Quantity must be a positive whole number (at least 1).`);
                    qtyInput.focus();
                    return;
                }
            }

            const disc = parseFloat(discountInput.value) || 0;
            if (disc < 0 || disc > 20) {
                e.preventDefault();
                showAlert("Discount percentage must be between 0% and 20%.");
                discountInput.focus();
                return;
            }

            // Prevent duplicate form submission
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status"></span> Creating Order...';
        });
    }

    // Add first row by default if empty
    if (tableBody && tableBody.children.length === 0) {
        addNewRow();
    }
});
