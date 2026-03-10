use tonic::{transport::Server, Request, Response, Status};
use verifier::verifier_service_server::{VerifierService, VerifierServiceServer};
use verifier::{VerifyRequest, VerifyResponse, VerificationResult, Issue};
use log::{info, error, warn};

pub mod verifier {
    tonic::include_proto!("verifier");
}

mod sandbox;
mod formal;

use sandbox::WasmSandbox;
use formal::SmtVerifier;

#[derive(Debug, Default)]
pub struct AxiomVerifier {}

#[tonic::async_trait]
impl VerifierService for AxiomVerifier {
    async fn verify(
        &self,
        request: Request<VerifyRequest>,
    ) -> Result<Response<VerifyResponse>, Status> {
        let req = request.into_inner();
        info!("Processing verification request for code (len: {})", req.code.len());

        let mut results = vec![];
        let mut all_passed = true;
        let mut final_score = 1.0;

        // 1. Static Analysis (Tree-sitter)
        let mut syntax_passed = true;
        if req.language.to_lowercase() == "python" {
            let mut parser = tree_sitter::Parser::new();
            parser.set_language(tree_sitter_python::language()).unwrap();
            if let Some(tree) = parser.parse(&req.code, None) {
                if tree.root_node().has_error() {
                    syntax_passed = false;
                    all_passed = false;
                    final_score *= 0.1;
                    results.push(VerificationResult {
                        check_name: "tree_sitter_syntax".to_string(),
                        status: "failed".to_string(),
                        message: "Syntax error detected by Tree-sitter".to_string(),
                        score: 0.0,
                        tier: 1,
                    });
                } else {
                    results.push(VerificationResult {
                        check_name: "tree_sitter_syntax".to_string(),
                        status: "passed".to_string(),
                        message: "Syntax is correct".to_string(),
                        score: 1.0,
                        tier: 1,
                    });
                }
            }
        }

        // 2. Formal Verification (Z3 — Real)
        if syntax_passed && !req.contracts.is_empty() {
             let smt = SmtVerifier::new();
             
             let constraints = req.contracts.iter()
                .map(|c| c.expression.clone())
                .collect::<Vec<_>>();
                
             let formal_result = smt.verify_constraints(constraints);

             if !formal_result.passed {
                 all_passed = false;
                 final_score *= 0.3;
             }
             
             results.push(VerificationResult {
                 check_name: "smt_solver_z3".to_string(),
                 status: if formal_result.passed { "passed".to_string() } else { "failed".to_string() },
                 message: format!(
                     "Z3 formal verification: {} ({}ms)",
                     formal_result.solver_status,
                     formal_result.duration_ms
                 ),
                 score: if formal_result.passed { 1.0 } else { 0.0 },
                 tier: 3,
             });

             // Log per-constraint details
             for detail in &formal_result.details {
                 if detail.status != "parsed" {
                     warn!("Constraint issue: {} — {}", detail.expression, detail.message);
                 }
             }
        }

        // 3. Dynamic Execution (WASM Sandbox — Real)
        if syntax_passed {
            let sandbox_result = WasmSandbox::new()
                .and_then(|sb| sb.execute(req.code.as_bytes(), 5000));

        match sandbox_result {
            Ok(res) => {
                 if !res.success {
                     all_passed = false;
                     final_score *= 0.5;
                 }

                 results.push(VerificationResult {
                     check_name: "wasm_sandbox".to_string(),
                     status: if res.success { "passed".to_string() } else { "failed".to_string() },
                     message: format!(
                         "{} (fuel: {}, mem: {}B, {}ms)",
                         res.output, res.fuel_consumed, res.memory_used_bytes, res.duration_ms
                     ),
                     score: if res.success { 1.0 } else { 0.0 },
                     tier: 2,
                 });
            },
            Err(e) => {
                error!("WASM sandbox error: {}", e);
                all_passed = false;

                results.push(VerificationResult {
                    check_name: "wasm_sandbox".to_string(),
                    status: "infrastructure_error".to_string(),
                    message: format!("Sandbox Infrastructure Error: initialization failed: {}", e),
                    score: 0.0,
                    tier: 2,
                });
            }
        }
        }

        // Build issues list from failed results
        let issues: Vec<Issue> = results.iter()
            .filter(|r| r.status != "passed")
            .map(|r| Issue {
                severity: if r.tier >= 3 { "critical".to_string() } else { "warning".to_string() },
                message: r.message.clone(),
                line: 0,
                column: 0,
                code: r.check_name.clone(),
            })
            .collect();

        Ok(Response::new(VerifyResponse {
            valid: all_passed,
            score: final_score,
            issues,
            results,
        }))
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    env_logger::init();
    
    let addr = std::env::var("VERIFIER_PORT")
        .unwrap_or_else(|_| "0.0.0.0:50051".to_string())
        .parse()?;
    let verifier = AxiomVerifier::default();

    println!("AXIOM Verifier Service (Rust/Z3/WASM) listening on {}", addr);

    Server::builder()
        .add_service(VerifierServiceServer::new(verifier))
        .serve(addr)
        .await?;

    Ok(())
}
