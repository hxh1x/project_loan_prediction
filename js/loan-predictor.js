const FEATURE_WEIGHTS = {
  cibil_score: 0.35,
  income_to_loan_ratio: 0.22,
  total_assets_to_loan: 0.15,
  loan_term: 0.04,
  education: 0.07,
  self_employed: 0.02,
  dependents: 0.03,
  bank_asset_value: 0.07,
  commercial_assets: 0.05,
};

function sigmoid(x) {
  return 1 / (1 + Math.exp(-x));
}

function normalize(value, min, max) {
  return Math.max(0, Math.min(1, (value - min) / (max - min)));
}

function predictLoan(input) {
  // Feature engineering
  const cibilNorm = normalize(input.cibil_score, 300, 900);

  // Income-to-loan ratio: higher is better (can afford the loan)
  const incomeToLoanRatio = input.income_annum / Math.max(input.loan_amount, 1);
  const incomeRatioNorm = normalize(incomeToLoanRatio, 0, 1.5);

  // Total assets relative to loan amount
  const totalAssets = Number(input.residential_assets_value) + Number(input.commercial_assets_value) + Number(input.luxury_assets_value) + Number(input.bank_asset_value);
  const assetsToLoanRatio = totalAssets / Math.max(input.loan_amount, 1);
  const assetsRatioNorm = normalize(assetsToLoanRatio, 0, 3);

  // Loan term: shorter terms are slightly better (less risk)
  const loanTermMonths = Math.max(input.loan_term, 1);
  const loanTermNorm = normalize(360 - loanTermMonths, 0, 360); // inverse: shorter = higher score

  const educationScore = input.education === "Graduate" ? 0.65 : 0.35;
  const selfEmployedScore = input.self_employed === "No" ? 0.55 : 0.45;
  const dependentsNorm = normalize(5 - input.no_of_dependents, 0, 5);
  const bankAssetNorm = normalize(input.bank_asset_value, 0, 20000000);
  const commercialNorm = normalize(input.commercial_assets_value, 0, 20000000);

  // Weighted score
  let score =
    cibilNorm * FEATURE_WEIGHTS.cibil_score +
    incomeRatioNorm * FEATURE_WEIGHTS.income_to_loan_ratio +
    assetsRatioNorm * FEATURE_WEIGHTS.total_assets_to_loan +
    loanTermNorm * FEATURE_WEIGHTS.loan_term +
    educationScore * FEATURE_WEIGHTS.education +
    selfEmployedScore * FEATURE_WEIGHTS.self_employed +
    dependentsNorm * FEATURE_WEIGHTS.dependents +
    bankAssetNorm * FEATURE_WEIGHTS.bank_asset_value +
    commercialNorm * FEATURE_WEIGHTS.commercial_assets;

  // Non-linear decision boundaries
  if (input.cibil_score >= 700) score += 0.12;
  else if (input.cibil_score >= 650) score += 0.06;
  else if (input.cibil_score < 500) score -= 0.15;
  else if (input.cibil_score < 400) score -= 0.25;

  if (incomeToLoanRatio > 0.5) score += 0.05;
  if (incomeToLoanRatio < 0.1) score -= 0.1;

  if (assetsToLoanRatio > 1.5) score += 0.04;

  const confidence = sigmoid((score - 0.38) * 7);
  const approved = confidence >= 0.5;

  const features = [
    { feature: "CIBIL Score", importance: FEATURE_WEIGHTS.cibil_score, direction: cibilNorm > 0.55 ? "positive" : "negative" },
    { feature: "Income-to-Loan Ratio", importance: FEATURE_WEIGHTS.income_to_loan_ratio, direction: incomeRatioNorm > 0.3 ? "positive" : "negative" },
    { feature: "Assets-to-Loan Ratio", importance: FEATURE_WEIGHTS.total_assets_to_loan, direction: assetsRatioNorm > 0.3 ? "positive" : "negative" },
    { feature: "Education", importance: FEATURE_WEIGHTS.education, direction: input.education === "Graduate" ? "positive" : "negative" },
    { feature: "Bank Assets", importance: FEATURE_WEIGHTS.bank_asset_value, direction: bankAssetNorm > 0.3 ? "positive" : "negative" },
    { feature: "Loan Term", importance: FEATURE_WEIGHTS.loan_term, direction: loanTermMonths <= 180 ? "positive" : "negative" },
  ].sort((a, b) => b.importance - a.importance);

  return {
    status: approved ? "Approved" : "Rejected",
    confidence: Math.round(confidence * 1000) / 10,
    probability_of_default: Math.round((1 - confidence) * 1000) / 10,
    feature_importance: features,
    risk_score: Math.round((1 - score) * 100),
  };
}

function formatCurrency(value) {
  if (value >= 10000000) return `₹${(value / 10000000).toFixed(1)}Cr`;
  if (value >= 100000) return `₹${(value / 100000).toFixed(1)}L`;
  return `₹${Number(value).toLocaleString("en-IN")}`;
}

window.loanPredictor = { predictLoan, formatCurrency };
