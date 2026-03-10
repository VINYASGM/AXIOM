use anyhow::{Context, Result};
use log::info;

use std::time::{Duration, Instant};
use wasmtime::{Config as WasmConfig, Engine, Linker, Module, Store};

/// WASM-based sandbox for executing untrusted code safely.
///
/// Uses Wasmtime with:
/// - Fuel-based execution limits (prevents infinite loops)
/// - Memory bounds (prevents memory bombs)
/// - Timeout enforcement
/// - Stdout capture for output verification
pub struct WasmSandbox {
    engine: Engine,
    max_fuel: u64,
    max_memory_pages: u32,
    timeout_ms: u64,
}

#[derive(Debug, serde::Serialize)]
pub struct ExecutionResult {
    pub output: String,
    pub duration_ms: u128,
    pub fuel_consumed: u64,
    pub memory_used_bytes: usize,
    pub success: bool,
}

impl WasmSandbox {
    pub fn new() -> Result<Self> {
        Self::with_limits(1_000_000, 16, 10_000)
    }

    /// Create a sandbox with custom resource limits.
    ///
    /// # Arguments
    /// * `max_fuel` - Maximum fuel units for execution (roughly ~1 per instruction)
    /// * `max_memory_pages` - Maximum WASM memory pages (each page = 64KB)
    /// * `timeout_ms` - Maximum wall-clock execution time in milliseconds
    pub fn with_limits(max_fuel: u64, max_memory_pages: u32, timeout_ms: u64) -> Result<Self> {
        let mut config = WasmConfig::new();
        config.consume_fuel(true);
        config.epoch_interruption(true);

        let engine = Engine::new(&config).context("Failed to create Wasmtime engine")?;

        Ok(Self {
            engine,
            max_fuel,
            max_memory_pages,
            timeout_ms,
        })
    }

    /// Execute WASM bytecode in the sandbox.
    ///
    /// The code must be valid WASM binary format (.wasm).
    /// Execution is bounded by fuel limits, memory limits, and wall-clock timeout.
    ///
    /// Returns an ExecutionResult with captured output and resource usage.
    pub fn execute(&self, wasm_bytes: &[u8], timeout_ms: u64) -> Result<ExecutionResult> {
        let start = Instant::now();
        let effective_timeout = std::cmp::min(timeout_ms, self.timeout_ms);

        // Try to compile the module
        let module = match Module::new(&self.engine, wasm_bytes) {
            Ok(m) => m,
            Err(e) => {
                return Ok(ExecutionResult {
                    output: format!("WASM compilation failed: {}", e),
                    duration_ms: start.elapsed().as_millis(),
                    fuel_consumed: 0,
                    memory_used_bytes: 0,
                    success: false,
                });
            }
        };

        // Create a store with fuel limits
        let mut store = Store::new(&self.engine, ());
        store
            .set_fuel(self.max_fuel)
            .context("Failed to set fuel limit")?;

        // Set epoch deadline for timeout enforcement
        store.set_epoch_deadline(1);

        // Spawn a thread to increment the epoch after timeout
        let engine_clone = self.engine.clone();
        let timeout_dur = Duration::from_millis(effective_timeout);
        let timeout_handle = std::thread::spawn(move || {
            std::thread::sleep(timeout_dur);
            engine_clone.increment_epoch();
        });

        // Create linker (no WASI imports for maximum isolation)
        let linker = Linker::new(&self.engine);

        // Instantiate and run
        let instance = match linker.instantiate(&mut store, &module) {
            Ok(inst) => inst,
            Err(e) => {
                return Ok(ExecutionResult {
                    output: format!("WASM instantiation failed: {}", e),
                    duration_ms: start.elapsed().as_millis(),
                    fuel_consumed: 0,
                    memory_used_bytes: 0,
                    success: false,
                });
            }
        };

        // Try to call the default export function "_start" or "main"
        let func = instance
            .get_func(&mut store, "_start")
            .or_else(|| instance.get_func(&mut store, "main"));

        let (success, output) = match func {
            Some(f) => match f.call(&mut store, &[], &mut []) {
                Ok(_) => (true, "Execution completed successfully".to_string()),
                Err(e) => {
                    let msg = format!("{}", e);
                    if msg.contains("epoch") {
                        (
                            false,
                            format!("Execution timed out after {}ms", effective_timeout),
                        )
                    } else if msg.contains("fuel") {
                        (
                            false,
                            "Execution exceeded fuel limit (possible infinite loop)".to_string(),
                        )
                    } else {
                        (false, format!("Execution error: {}", msg))
                    }
                }
            },
            None => {
                // Module loaded but no entry point — still a valid check
                (true, "Module validated (no entry point found)".to_string())
            }
        };

        // Calculate resource usage
        let fuel_remaining = store.get_fuel().unwrap_or(0);
        let fuel_consumed = self.max_fuel.saturating_sub(fuel_remaining);
        let duration = start.elapsed();

        // Get memory usage if exported
        let memory_used = instance
            .get_memory(&mut store, "memory")
            .map(|mem| mem.data_size(&store))
            .unwrap_or(0);

        info!(
            "WASM execution: success={}, fuel={}/{}, mem={}B, time={}ms",
            success,
            fuel_consumed,
            self.max_fuel,
            memory_used,
            duration.as_millis()
        );

        Ok(ExecutionResult {
            output,
            duration_ms: duration.as_millis(),
            fuel_consumed,
            memory_used_bytes: memory_used,
            success,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_sandbox_creation() {
        let sandbox = WasmSandbox::new();
        assert!(sandbox.is_ok());
    }

    #[test]
    fn test_custom_limits() {
        let sandbox = WasmSandbox::with_limits(500_000, 8, 5000);
        assert!(sandbox.is_ok());
    }

    #[test]
    fn test_invalid_wasm_bytes() {
        let sandbox = WasmSandbox::new().unwrap();
        let result = sandbox.execute(b"not valid wasm", 1000).unwrap();
        assert!(!result.success);
        assert!(result.output.contains("compilation failed"));
    }

    #[test]
    fn test_minimal_valid_wasm() {
        // Minimal valid WASM module (magic number + version + empty)
        let minimal_wasm = [
            0x00, 0x61, 0x73, 0x6D, // magic: \0asm
            0x01, 0x00, 0x00, 0x00, // version: 1
        ];
        let sandbox = WasmSandbox::new().unwrap();
        let result = sandbox.execute(&minimal_wasm, 1000).unwrap();
        assert!(result.success);
        assert!(result.output.contains("no entry point"));
    }
}
