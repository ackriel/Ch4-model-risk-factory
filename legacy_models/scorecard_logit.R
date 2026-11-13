# =============================================================================
# MODEL_ID:     CR-PD-001
# MODEL_NAME:   Retail Unsecured Loan Application Scorecard (PD)
# OWNER:        Retail Credit Risk Analytics
# PURPOSE:      Estimate probability of default (PD) for new personal-loan applications
# USE:          Credit approval decisions and risk-based pricing
# LANGUAGE:     R (base stats only)
# LAST_REVIEW:  2019-03 (documentation out of date)
# =============================================================================
# Legacy logistic regression scorecard. Fitted with glm() and the binomial family.
# Run from the project root:   Rscript legacy_models/scorecard_logit.R
# Writes coefficients, train/test scores and the model specification to
# legacy_models/artifacts/ so that the Redevelop agent can prove parity.

args <- commandArgs(trailingOnly = TRUE)
out_dir <- if (length(args) >= 1) args[1] else "legacy_models/artifacts"
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)

train <- read.csv("data/train.csv", stringsAsFactors = FALSE, check.names = FALSE)
test  <- read.csv("data/test.csv",  stringsAsFactors = FALSE, check.names = FALSE)

target <- "default_flag"
numeric_vars <- c("duration", "amount", "age")

# Explicit factor levels: the FIRST level of each list is the reference category.
factor_levels <- list(
  status = c("no checking account",
             "... < 0 DM",
             "0<= ... < 200 DM",
             "... >= 200 DM / salary for at least 1 year"),
  credit_history = c("no credits taken/all credits paid back duly",
                     "all credits at this bank paid back duly",
                     "existing credits paid back duly till now",
                     "delay in paying off in the past",
                     "critical account/other credits elsewhere"),
  savings = c("unknown/no savings account",
              "... <  100 DM",
              "100 <= ... <  500 DM",
              "500 <= ... < 1000 DM",
              "... >= 1000 DM")
)

prep <- function(df) {
  for (v in names(factor_levels)) {
    df[[v]] <- factor(df[[v]], levels = factor_levels[[v]])
  }
  df
}
train <- prep(train)
test  <- prep(test)

model_formula <- as.formula(paste(
  target, "~", paste(c(numeric_vars, names(factor_levels)), collapse = " + ")))

fit <- glm(model_formula, data = train, family = binomial(link = "logit"),
           control = glm.control(epsilon = 1e-14, maxit = 100))

# ---- Outputs ------------------------------------------------------------------
coefs <- summary(fit)$coefficients
write.csv(data.frame(term = rownames(coefs),
                     estimate = coefs[, "Estimate"],
                     std_error = coefs[, "Std. Error"],
                     p_value = coefs[, "Pr(>|z|)"]),
          file.path(out_dir, "CR-PD-001_r_coefficients.csv"), row.names = FALSE)

write.csv(data.frame(customer_id = train$customer_id,
                     pd = predict(fit, newdata = train, type = "response")),
          file.path(out_dir, "CR-PD-001_r_train_scores.csv"), row.names = FALSE)
write.csv(data.frame(customer_id = test$customer_id,
                     pd = predict(fit, newdata = test, type = "response")),
          file.path(out_dir, "CR-PD-001_r_test_scores.csv"), row.names = FALSE)

# Model specification in a machine-readable form (variable, type, level, order).
spec_rows <- data.frame(variable = numeric_vars, type = "numeric", level = "", level_order = 0)
for (v in names(factor_levels)) {
  lv <- factor_levels[[v]]
  spec_rows <- rbind(spec_rows, data.frame(variable = v, type = "factor",
                                           level = lv, level_order = seq_along(lv) - 1))
}
write.csv(spec_rows, file.path(out_dir, "CR-PD-001_r_spec.csv"), row.names = FALSE)

writeLines(c(paste0("r_version=", R.version.string),
             paste0("run_utc=", format(Sys.time(), "%Y-%m-%dT%H:%M:%SZ", tz = "UTC")),
             paste0("converged=", fit$converged),
             paste0("iterations=", fit$iter),
             paste0("aic=", sprintf("%.6f", AIC(fit)))),
           file.path(out_dir, "CR-PD-001_r_run_info.txt"))

cat("CR-PD-001 fitted. AIC:", AIC(fit), " converged:", fit$converged, "\n")
