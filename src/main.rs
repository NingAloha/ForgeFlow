mod llm;
mod mutation;
mod runtime;
mod sieves;

use anyhow::Result;
use std::io::{self, Write};

fn main() -> Result<()> {
    print!("Requirement> ");
    io::stdout().flush()?;

    let mut user_input = String::new();
    io::stdin().read_line(&mut user_input)?;

    let artifact = sieves::requirements::intent::capture::capture_intent(user_input.trim())?;

    sieves::requirements::io::save_requirements(&artifact)?;

    println!("\nSaved requirements artifact:");
    println!("{}", serde_json::to_string_pretty(&artifact)?);

    Ok(())
}