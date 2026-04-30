/**
 * Lendmark UI Helpers
 * formatCurrency — shared currency formatter used across all pages.
 * Note: Loan prediction is handled server-side via the Random Forest model (/api/predict).
 */
function formatCurrency(value) {
  if (value >= 10000000) return `₹${(value / 10000000).toFixed(1)}Cr`;
  if (value >= 100000)   return `₹${(value / 100000).toFixed(1)}L`;
  return `₹${Number(value).toLocaleString("en-IN")}`;
}

window.loanPredictor = { formatCurrency };
