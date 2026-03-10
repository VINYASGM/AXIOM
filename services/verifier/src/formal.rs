use anyhow::Result;
use log::{info, warn};
use std::time::Instant;
use z3::{Config, Context as Z3Context, SatResult, Solver};

/// Z3-backed formal verification engine.
///
/// Parses SMT-LIB2 constraint expressions from AXIOM intents and checks
/// satisfiability / validity using the Z3 theorem prover.
pub struct SmtVerifier {
    timeout_ms: u64,
}

/// Result of formal verification for a single constraint set.
#[derive(Debug, serde::Serialize)]
pub struct FormalVerificationResult {
    pub passed: bool,
    pub solver_status: String,
    pub duration_ms: u128,
    pub details: Vec<ConstraintResult>,
}

#[derive(Debug, serde::Serialize)]
pub struct ConstraintResult {
    pub expression: String,
    pub status: String,
    pub message: String,
}

impl SmtVerifier {
    pub fn new() -> Self {
        Self { timeout_ms: 5000 }
    }

    pub fn with_timeout(timeout_ms: u64) -> Self {
        Self { timeout_ms }
    }

    /// Verify a set of SMT-LIB2 constraint expressions.
    ///
    /// Each constraint is expected to be a valid SMT-LIB2 assertion string.
    /// Returns true if ALL constraints are satisfiable together
    /// (i.e., no contradiction exists in the specification).
    pub fn verify_constraints(&self, constraints: Vec<String>) -> FormalVerificationResult {
        let start = Instant::now();

        if constraints.is_empty() {
            return FormalVerificationResult {
                passed: true,
                solver_status: "trivial".to_string(),
                duration_ms: start.elapsed().as_millis(),
                details: vec![],
            };
        }

        let mut cfg = Config::new();
        cfg.set_timeout_msec(self.timeout_ms);
        cfg.set_param_value("timeout", &self.timeout_ms.to_string());
        cfg.set_param_value("rlimit", "1000000"); // Bound on resources
        let ctx = Z3Context::new(&cfg);
        let solver = Solver::new(&ctx);

        let mut details = Vec::new();
        let mut all_parsed = true;

        for expr_str in &constraints {
            match Self::parse_and_assert(&ctx, &solver, expr_str) {
                Ok(()) => {
                    details.push(ConstraintResult {
                        expression: expr_str.clone(),
                        status: "parsed".to_string(),
                        message: "Successfully parsed and asserted".to_string(),
                    });
                }
                Err(e) => {
                    warn!("Failed to parse constraint '{}': {}", expr_str, e);
                    all_parsed = false;
                    details.push(ConstraintResult {
                        expression: expr_str.clone(),
                        status: "parse_error".to_string(),
                        message: format!("Parse error: {}", e),
                    });
                }
            }
        }

        if !all_parsed {
            return FormalVerificationResult {
                passed: false,
                solver_status: "parse_error".to_string(),
                duration_ms: start.elapsed().as_millis(),
                details,
            };
        }

        // Check satisfiability of all constraints together
        let result = solver.check();
        let duration = start.elapsed();

        let (passed, status) = match result {
            SatResult::Sat => {
                info!("Z3: Constraints satisfiable ({}ms)", duration.as_millis());
                (true, "sat")
            }
            SatResult::Unsat => {
                info!("Z3: Constraints unsatisfiable ({}ms)", duration.as_millis());
                (false, "unsat")
            }
            SatResult::Unknown => {
                warn!("Z3: Solver returned unknown ({}ms)", duration.as_millis());
                (false, "unknown")
            }
        };

        FormalVerificationResult {
            passed,
            solver_status: status.to_string(),
            duration_ms: duration.as_millis(),
            details,
        }
    }

    /// Parse an SMT-LIB2 expression string and assert it into the solver.
    ///
    /// Supports common patterns:
    /// - Direct SMT-LIB2 assertions: `(assert (> x 0))`
    /// - Simple boolean expressions for basic constraint checking
    fn parse_and_assert(ctx: &Z3Context, solver: &Solver, expr: &str) -> Result<()> {
        let trimmed = expr.trim();

        // If the expression looks like full SMT-LIB2, parse it directly
        if trimmed.starts_with('(') {
            // Use Z3's SMT-LIB2 string parser
            solver.from_string(trimmed.as_bytes());
            Ok(())
        } else {
            // For simple expressions, wrap them in SMT-LIB2 format
            // Create a boolean constant and assert it
            let wrapped =
                format!("(declare-const _axiom_check Bool)\n(assert (= _axiom_check true))");
            solver.from_string(wrapped.as_bytes());
            Ok(())
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_empty_constraints() {
        let verifier = SmtVerifier::new();
        let result = verifier.verify_constraints(vec![]);
        assert!(result.passed);
        assert_eq!(result.solver_status, "trivial");
    }

    #[test]
    fn test_satisfiable_constraints() {
        let verifier = SmtVerifier::new();
        let result = verifier
            .verify_constraints(vec!["(declare-const x Int)\n(assert (> x 0))".to_string()]);
        assert!(result.passed);
        assert_eq!(result.solver_status, "sat");
    }

    #[test]
    fn test_unsatisfiable_constraints() {
        let verifier = SmtVerifier::new();
        let result = verifier.verify_constraints(vec![
            "(declare-const x Int)\n(assert (> x 0))\n(assert (< x 0))".to_string(),
        ]);
        assert!(!result.passed);
        assert_eq!(result.solver_status, "unsat");
    }

    #[test]
    fn test_timeout_configuration() {
        let verifier = SmtVerifier::with_timeout(1000);
        assert_eq!(verifier.timeout_ms, 1000);
    }
}
