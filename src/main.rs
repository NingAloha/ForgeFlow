#![allow(dead_code)]
#![allow(unused_imports)]

mod llm;
mod runtime;
mod sieves;
use serde_json::{Value, json};

fn main() {
    use std::fs;
    use std::io::{self, Read};
    use std::path::Path;

    let mut user_input = String::new();
    if let Err(err) = io::stdin().read_to_string(&mut user_input) {
        eprintln!("failed to read stdin: {err}");
        std::process::exit(1);
    }

    let user_input = user_input.trim_end();
    if user_input.trim().is_empty() {
        eprintln!("stdin input must not be empty");
        std::process::exit(1);
    }

    let domain_capture = match sieves::requirements::boundary::capture_domain(user_input) {
        Ok(v) => v,
        Err(err) => {
            eprintln!("{err}");
            std::process::exit(1);
        }
    };

    let problem_capture =
        match sieves::requirements::boundary::capture_problem_from_context(&domain_capture) {
            Ok(v) => v,
            Err(err) => {
                eprintln!("{err}");
                std::process::exit(1);
            }
        };

    let merged_candidate = match sieves::requirements::boundary::merge_domain_and_problem_candidate(
        &domain_capture,
        &problem_capture,
    ) {
        Ok(v) => v,
        Err(err) => {
            eprintln!("{err}");
            std::process::exit(1);
        }
    };
    let capability_capture =
        match sieves::requirements::boundary::capture_capability_from_context(&merged_candidate) {
            Ok(v) => v,
            Err(err) => {
                eprintln!("{err}");
                std::process::exit(1);
            }
        };

    let problem = match merged_candidate
        .get("boundary")
        .and_then(|v| v.get("problem"))
        .and_then(Value::as_str)
    {
        Some(v) => v.to_string(),
        None => {
            eprintln!("problem capture response missing boundary.problem");
            std::process::exit(1);
        }
    };
    let capability = match capability_capture
        .get("boundary")
        .and_then(|v| v.get("capability"))
        .and_then(Value::as_str)
    {
        Some(v) => v.to_string(),
        None => {
            eprintln!("capability capture response missing boundary.capability");
            std::process::exit(1);
        }
    };

    let domain = merged_candidate
        .get("boundary")
        .and_then(|v| v.get("domain"))
        .and_then(Value::as_str)
        .unwrap_or("");

    let preview =
        sieves::requirements::boundary::build_boundary_preview(domain, &problem, &capability);
    if !sieves::requirements::boundary::is_candidate_complete(domain, &problem, &capability) {
        println!("{preview}");
        return;
    }

    if let Err(err) = sieves::requirements::io::write_requirements_capture_output(&domain_capture) {
        eprintln!("{err}");
        std::process::exit(1);
    }

    let runtime_path = Path::new(runtime::paths::REQUIREMENTS_RUNTIME_PATH);
    let mut runtime: Value = match fs::read_to_string(runtime_path) {
        Ok(content) => match serde_json::from_str(&content) {
            Ok(v) => v,
            Err(err) => {
                eprintln!("failed to parse runtime JSON: {err}");
                std::process::exit(1);
            }
        },
        Err(err) => {
            eprintln!("failed to read runtime JSON: {err}");
            std::process::exit(1);
        }
    };

    let runtime_obj = match runtime.as_object_mut() {
        Some(v) => v,
        None => {
            eprintln!("runtime JSON must be an object");
            std::process::exit(1);
        }
    };
    let boundary_obj = runtime_obj
        .entry("boundary")
        .or_insert_with(|| json!({}))
        .as_object_mut();
    let boundary_obj = match boundary_obj {
        Some(v) => v,
        None => {
            eprintln!("runtime boundary must be an object");
            std::process::exit(1);
        }
    };
    boundary_obj.insert("problem".to_string(), Value::String(problem));

    let runtime_text = match serde_json::to_string_pretty(&runtime) {
        Ok(text) => format!("{text}\n"),
        Err(err) => {
            eprintln!("failed to serialize runtime JSON: {err}");
            std::process::exit(1);
        }
    };
    if let Err(err) = fs::write(runtime_path, runtime_text) {
        eprintln!("failed to write runtime JSON: {err}");
        std::process::exit(1);
    }

    let slice = match sieves::requirements::io::read_requirements_context_slice(&[
        "boundary.domain",
        "boundary.problem",
    ]) {
        Ok(v) => v,
        Err(err) => {
            eprintln!("{err}");
            std::process::exit(1);
        }
    };

    let domain = slice
        .get("boundary")
        .and_then(|v| v.get("domain"))
        .and_then(Value::as_str)
        .unwrap_or("");
    let problem = slice
        .get("boundary")
        .and_then(|v| v.get("problem"))
        .and_then(Value::as_str)
        .unwrap_or("");

    println!(
        "{}",
        sieves::requirements::boundary::build_boundary_preview(domain, problem, &capability)
    );
}
