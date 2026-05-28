#![allow(dead_code)]
#![allow(unused_imports)]

use anyhow::{bail, Result};
use std::io::{self, Write};

mod llm;
mod mutation;
mod runtime;
mod sieves;

fn main() -> Result<()> {
    let args: Vec<String> = std::env::args().collect();

    match args.as_slice() {
        [_, domain, action] if domain == "requirements" && action == "intent" => {
            print!("Requirement> ");
            io::stdout().flush()?;

            let mut user_input = String::new();
            io::stdin().read_line(&mut user_input)?;

            let artifact = sieves::requirements::intent::capture::capture_intent(
                user_input.trim(),
            )?;
            sieves::requirements::io::save_requirements(&artifact)?;
            println!("{}", serde_json::to_string_pretty(&artifact)?);
            Ok(())
        }
        [_, domain, action]
            if domain == "requirements" && action == "target-users" =>
        {
            sieves::requirements::scope::target_users::run_target_users_scope()
        }
        [_, domain, action]
            if domain == "requirements" && action == "application-boundary" =>
        {
            sieves::requirements::scope::application_boundary::run_application_boundary_scope()
        }
        [_, domain, action]
            if domain == "requirements" && action == "capability-categories" =>
        {
            sieves::requirements::scope::capability_categories::run_capability_categories_scope()
        }
        [_, domain, action]
            if domain == "requirements" && action == "explicit-constraints" =>
        {
            sieves::requirements::scope::explicit_constraints::run_explicit_constraints_scope()
        }
        [_, domain, action] if domain == "requirements" && action == "non-goals" => {
            sieves::requirements::scope::non_goals::run_non_goals_scope()
        }
        _ => {
            eprintln!("Usage:");
            eprintln!("  cargo run -- requirements intent");
            eprintln!("  cargo run -- requirements target-users");
            eprintln!("  cargo run -- requirements application-boundary");
            eprintln!("  cargo run -- requirements capability-categories");
            eprintln!("  cargo run -- requirements explicit-constraints");
            eprintln!("  cargo run -- requirements non-goals");
            bail!("unknown command")
        }
    }
}
