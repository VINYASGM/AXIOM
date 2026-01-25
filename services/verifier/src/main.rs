use tonic::{transport::Server, Request, Response, Status};
use verifier::verifier_service_server::{VerifierService, VerifierServiceServer};
use verifier::{VerifyRequest, VerifyResponse, Issue};
use rustpython_parser::{parse, Mode};
use rustpython_parser::ast;
use rustpython_parser::ast::{Mod, Stmt};

struct DocstringChecker {
    total_definitions: usize,
    documented: usize,
    missing_docs: Vec<String>,
}

impl DocstringChecker {
    fn new() -> Self {
        Self { total_definitions: 0, documented: 0, missing_docs: Vec::new() }
    }

    fn check(&mut self, ast: &Vec<Stmt>) {
        for stmt in ast {
            self.visit_stmt(stmt);
        }
    }

    fn visit_stmt(&mut self, stmt: &Stmt) {
        match stmt {
            Stmt::FunctionDef(f) => self.check_def(&f.body, &f.name.as_str()),
            Stmt::AsyncFunctionDef(f) => self.check_def(&f.body, &f.name.as_str()),
            Stmt::ClassDef(c) => self.check_def(&c.body, &c.name.as_str()),
            _ => {}
        }
    }

    fn check_def(&mut self, body: &Vec<Stmt>, name: &str) {
        self.total_definitions += 1;
        if let Some(doc_stmt) = body.first() {
            if let Stmt::Expr(expr_stmt) = doc_stmt {
                 if let ast::Expr::Constant(const_expr) = &*expr_stmt.value {
                     if let ast::Constant::Str(_) = const_expr.value {
                         self.documented += 1;
                         return;
                     }
                 }
            }
        }
        self.missing_docs.push(name.to_string());
    }
}


pub mod verifier {
    tonic::include_proto!("verifier");
}

#[derive(Debug, Default)]
pub struct MyVerifier {}

#[tonic::async_trait]
impl VerifierService for MyVerifier {
    async fn verify(
        &self,
        request: Request<VerifyRequest>,
    ) -> Result<Response<VerifyResponse>, Status> {
        let req = request.into_inner();
        let code = req.code;
        let mut issues = Vec::new();
        let mut valid = true;
        
        // 1. Syntax Check (Python)
        // Only run if language is python or unspecified
        if req.language.to_lowercase() == "python" || req.language.is_empty() {
            match parse(&code, Mode::Module, "<embedded>") {
                Ok(_) => {
                    // Syntax OK
                },
                Err(e) => {
                    valid = false;
                    issues.push(Issue {
                        code: "SYNTAX_ERROR".to_string(),
                        message: format!("{}", e.error),
                        severity: "error".to_string(),
                        line: 0,
                        column: u32::from(e.offset) as i32,
                    });
                }
            }
        }
        
        
        // 2. Docstring Check
        if req.checks.contains(&"docstrings".to_string()) && (req.language.to_lowercase() == "python" || req.language.is_empty()) {
            match parse(&code, Mode::Module, "<embedded>") {
                Ok(module_ast) => { // Rename ast to module_ast logic
                    if let Mod::Module(m) = module_ast {
                        let mut checker = DocstringChecker::new();
                        checker.check(&m.body);
                        
                        if checker.total_definitions > 0 {
                            let ratio = checker.documented as f32 / checker.total_definitions as f32;
                            if ratio < 0.5 {
                               valid = false;
                               issues.push(Issue {
                                    code: "DOCSTRING_MISSING".to_string(),
                                    message: format!("Low docstring coverage: {}/{} ({:.0}%)", checker.documented, checker.total_definitions, ratio * 100.0),
                                    severity: "warning".to_string(),
                                    line: 0,
                                    column: 0,
                                });
                            }
                             for missing in checker.missing_docs.iter().take(5) { 
                                 issues.push(Issue {
                                    code: "DOCSTRING_MISSING".to_string(),
                                    message: format!("'{}' lacks a docstring", missing),
                                    severity: "warning".to_string(),
                                    line: 0,
                                    column: 0,
                                });
                            }
                        }
                    }
                },
                Err(_) => {
                    // Syntax error already handled by syntax check
                }
            }
        }

        // 3. Execution Check
        if req.checks.contains(&"execution".to_string()) && (req.language.to_lowercase() == "python" || req.language.is_empty()) {
             // Create a temp file with the sandbox wrapper
             use std::io::Write;
             use std::process::Command;
             
             let wrapper_code = format!(r#"
import sys
from io import StringIO
old_stdout = sys.stdout
sys.stdout = StringIO()
try:
    exec_globals = {{"__builtins__": __builtins__}}
    exec("""{}""", exec_globals)
    print("__EXECUTION_SUCCESS__")
except Exception as e:
    print(f"__EXECUTION_ERROR__: {{type(e).__name__}}: {{str(e)}}")
output = sys.stdout.getvalue()
sys.stdout = old_stdout
print(output)
"#, code.replace("\"", "\\\"").replace("\\", "\\\\")); // Basic escaping, might be fragile

             let mut temp_dir = std::env::temp_dir();
             temp_dir.push(format!("axiom_exec_{}.py", uuid::Uuid::new_v4()));
             
             if let Ok(mut file) = std::fs::File::create(&temp_dir) {
                 if let Ok(_) = file.write_all(wrapper_code.as_bytes()) {
                     // Run python (using py launcher for Windows compatibility)
                     // Try "py" first, then "python"
                     let output = Command::new("py").arg(&temp_dir).output()
                        .or_else(|_| Command::new("python").arg(&temp_dir).output());

                     if let Ok(output) = output {
                         let stdout = String::from_utf8_lossy(&output.stdout);
                         let stderr = String::from_utf8_lossy(&output.stderr);
                         
                         if stdout.contains("__EXECUTION_SUCCESS__") {
                             // Passed
                         } else if stdout.contains("__EXECUTION_ERROR__") {
                             valid = false;
                             let error_msg = stdout.lines().find(|l| l.contains("__EXECUTION_ERROR__")).unwrap_or("Unknown execution error");
                             issues.push(Issue {
                                code: "EXECUTION_ERROR".to_string(),
                                message: error_msg.to_string(),
                                severity: "error".to_string(),
                                line: 0,
                                column: 0,
                            });
                         } else {
                              valid = false;
                              issues.push(Issue {
                                code: "EXECUTION_FAIL".to_string(),
                                message: format!("Execution failed or no output. Stderr: {}", stderr),
                                severity: "error".to_string(),
                                line: 0,
                                column: 0,
                            });
                         }
                     } else {
                          valid = false;
                          issues.push(Issue {
                                code: "EXECUTION_SPAWN_FAIL".to_string(),
                                message: "Failed to spawn python interpreter".to_string(),
                                severity: "error".to_string(),
                                line: 0,
                                column: 0,
                            });
                     }
                 }
                 let _ = std::fs::remove_file(&temp_dir);
             }
        }

        Ok(Response::new(VerifyResponse {
            valid,
            score: if valid { 1.0 } else { 0.0 },
            issues,
        }))
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let addr = "[::1]:50051".parse()?;
    let verifier = MyVerifier::default();

    println!("VerifierService listening on {}", addr);

    Server::builder()
        .add_service(VerifierServiceServer::new(verifier))
        .serve(addr)
        .await?;

    Ok(())
}
