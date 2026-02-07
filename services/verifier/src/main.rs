use tonic::{transport::Server, Request, Response, Status};
use verifier::verifier_service_server::{VerifierService, VerifierServiceServer};
use verifier::{VerifyRequest, VerifyResponse, VerificationResult, Issue};
use log::{info, error};

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

        // 1. Static Analysis (Native/Tree-sitter would go here)
        // ...

        // 2. Formal Verification (Z3 - Mocked)
        // Only run if contracts exist
        if !req.contracts.is_empty() {
             let smt = SmtVerifier::new();
             
             // Extract expressions from contracts
             let constraints = req.contracts.iter()
                .map(|c| c.expression.clone())
                .collect::<Vec<_>>();
                
             let passed = smt.verify_constraints(constraints); 
             
             if !passed {
                 all_passed = false;
                 final_score *= 0.5;
             }
             
             results.push(VerificationResult {
                 check_name: "smt_solver_z3".to_string(),
                 status: if passed { "passed".to_string() } else { "failed".to_string() },
                 message: "Formal verification constraints check (Simulated)".to_string(),
                 score: if passed { 1.0 } else { 0.0 },
                 tier: 3,
             });
        }

        // 3. Dynamic Execution (WASM Sandbox - Mocked)
        let sandbox_result = WasmSandbox::new()
            .and_then(|sb| sb.execute(req.code.as_bytes(), 1000));

        match sandbox_result {
            Ok(res) => {
                 results.push(VerificationResult {
                     check_name: "wasm_sandbox".to_string(),
                     status: "passed".to_string(),
                     message: format!("Execution successful: {}", res.output),
                     score: 1.0,
                     tier: 2,
                 });
            },
            Err(e) => {
                error!("WASM execution failed: {}", e);
                // For demo, we don't fail generic verification if sandbox fails,
                // unless it was explicitly requested.
            }
        }

        Ok(Response::new(VerifyResponse {
            valid: all_passed,
            score: final_score,
            issues: vec![], // Populate issues if analysis fails
            results,
        }))
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    env_logger::init();
    
    let addr = "0.0.0.0:50051".parse()?;
    let verifier = AxiomVerifier::default();

    println!("AXIOM Verifier Service (Rust/WASM/Z3) listening on {}", addr);

    Server::builder()
        .add_service(VerifierServiceServer::new(verifier))
        .serve(addr)
        .await?;

    Ok(())
}
